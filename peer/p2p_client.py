import socket
import json
import threading
import os
from queue import Queue
from chunk_manager import reassemble_file, hash_file


CHUNK_SIZE = 64 * 1024  # 64KB padrão


def connect_and_send(peer, payload):
    host, port = peer.split(":")
    port = int(port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        s.connect((host, port))
        s.sendall(json.dumps(payload).encode())
        data = s.recv(8192).decode()
        return json.loads(data.strip())


def get_chunk_map(peer, file_hash):
    try:
        res = connect_and_send(peer, {
            "type": "chunk_map",
            "file_hash": file_hash
        })
        if res.get("status") == "success":
            return res.get("chunks", [])
    except Exception as e:
        print(f"[!] Falha ao consultar chunk_map de {peer}: {e}")
        return []
    return []


def download_chunk(peer, file_hash, chunk_index, chunk_dir):
    try:
        host, port = peer.split(":")
        port = int(port)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect((host, port))

            payload = {
                "type": "get_chunk",
                "file_hash": file_hash,
                "chunk": chunk_index
            }
            s.sendall(json.dumps(payload).encode())

            header = b""
            while not header.endswith(b'\n'):
                header += s.recv(1)
            res = json.loads(header.decode().strip())

            if res.get("status") != "success":
                print(f"[!] Erro recebendo chunk {chunk_index} de {peer}")
                return False

            size = res.get("size")
            expected_chunk_hash = res.get("hash")
            received = 0

            os.makedirs(chunk_dir, exist_ok=True)

            temp_chunk_path = os.path.join(chunk_dir, f"temp_{chunk_index}")
            with open(temp_chunk_path, 'wb') as f:
                while received < size:
                    data = s.recv(min(4096, size - received))
                    if not data:
                        break
                    f.write(data)
                    received += len(data)

            chunk_hash = hash_file(temp_chunk_path)
            chunk_name = f"{chunk_index}_{chunk_hash}"
            chunk_path = os.path.join(chunk_dir, chunk_name)

            os.rename(temp_chunk_path, chunk_path)

            if chunk_hash != expected_chunk_hash:
                print(f"[!] Chunk inválido (hash incorreto): {chunk_name}")
                os.remove(chunk_path)
                return False

            print(f"[✓] Chunk {chunk_index} baixado de {peer} como {chunk_name}")
            return True

    except Exception as e:
        print(f"[!] Falha no download do chunk {chunk_index} de {peer}: {e}")
        return False


def download_file(username, filename, file_hash, size, peers, max_connections):
    chunk_dir = os.path.expanduser(f"~/p2p-tr2/{username}/{file_hash}")
    output_dir = os.path.expanduser(f"~/p2p-tr2/{username}/arquivos_reconstruidos")
    os.makedirs(chunk_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    num_chunks = (size + CHUNK_SIZE - 1) // CHUNK_SIZE

    chunk_peer_map = {}
    chunk_rarity = {}

    print("[*] Consultando mapa de chunks dos peers...")

    for peer in peers:
        available = get_chunk_map(peer, file_hash)
        for c in available:
            chunk_peer_map.setdefault(c, []).append(peer)

    if not chunk_peer_map:
        print("[!] Nenhum peer possui o arquivo.")
        return False

    for chunk_index in chunk_peer_map:
        chunk_rarity[chunk_index] = len(chunk_peer_map[chunk_index])

    chunk_queue = Queue()
    for c in sorted(chunk_rarity, key=lambda x: chunk_rarity[x]):
        chunk_queue.put(c)

    def worker():
        while not chunk_queue.empty():
            chunk = chunk_queue.get()
            peers_with_chunk = chunk_peer_map.get(chunk, [])
            if not peers_with_chunk:
                chunk_queue.task_done()
                continue

            peer = peers_with_chunk[0]

            success = download_chunk(
                peer, file_hash, chunk, chunk_dir
            )

            if not success:
                chunk_queue.put(chunk)

            chunk_queue.task_done()

    num_threads = min(max_connections, len(peers))
    print("Threads used:", num_threads)
    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        threads.append(t)

    chunk_queue.join()

    downloaded_chunks = [
        fname for fname in os.listdir(chunk_dir) if "_" in fname
    ]
    if len(downloaded_chunks) != num_chunks:
        print("[!] Download incompleto. Nem todos os chunks foram baixados.")
        return False

    output_path = os.path.join(output_dir, filename)

    success = reassemble_file(chunk_dir, output_path)

    if not success:
        print("[!] Erro na reconstrução do arquivo.")
        return False

    final_hash = hash_file(output_path)
    if final_hash != file_hash:
        print("[!] Arquivo final inválido. Hash não confere.")
        os.remove(output_path)
        return False

    print(f"[✓] Arquivo {filename} reconstruído e validado em {output_path}")
    return True
