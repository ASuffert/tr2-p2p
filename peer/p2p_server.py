import socket
import threading
import json
import os

from peer.chunk_manager import hash_file


def get_chunks_available(chunk_dir: str, file_hash: str) -> list[int]:
    file_chunk_dir = os.path.join(chunk_dir, file_hash)
    if not os.path.isdir(file_chunk_dir):
        return []

    chunks = []
    for fname in os.listdir(file_chunk_dir):
        if "_" not in fname:
            continue
        try:
            index_str, _ = fname.split("_", 1)
            idx = int(index_str)
            chunks.append(idx)
        except ValueError:
            continue
    return sorted(chunks)


def handle_client(username, conn, addr):
    chunk_dir = os.path.expanduser(f"~/p2p-tr2/{username}")
    try:
        with conn:
            header = conn.recv(1024).decode().strip()
            request = json.loads(header)
            print(f"Received request: {request}")

            req_type = request.get("type")
            file_hash = request.get("file_hash")

            if req_type == "chunk_map":
                chunks = get_chunks_available(chunk_dir, file_hash)
                if chunks:
                    response = {
                        "status": "success",
                        "chunks": chunks
                    }
                else:
                    response = {
                        "status": "error",
                        "message": "Arquivo não encontrado"
                    }
                conn.sendall(json.dumps(response).encode())

            elif req_type == "get_chunk":
                chunk_index = request.get("chunk")

                file_chunk_dir = os.path.join(chunk_dir, file_hash)

                chunk_file = None
                for fname in os.listdir(file_chunk_dir):
                    if fname.startswith(f"{chunk_index}_"):
                        chunk_file = fname

                if not chunk_file:
                    conn.sendall(b'{"status": "error", "message": "Chunk nao encontrado"}')
                    return

                chunk_path = os.path.join(file_chunk_dir, chunk_file)
                chunk_size = os.path.getsize(chunk_path)

                response = {
                    "status": "success",
                    "hash": hash_file(chunk_path),
                    "size": chunk_size
                }
                conn.sendall(json.dumps(response).encode() + b'\n')

                with open(chunk_path, 'rb') as f:
                    while data := f.read(4096):
                        conn.sendall(data)

                print(f"[✓] Chunk {chunk_index} de {file_hash} enviado para {addr}")

            else:
                conn.sendall(b'{"status": "error", "message": "Requisicao invalida"}')

    except Exception as e:
        print(f"[!] Erro ao lidar com cliente {addr}: {e}")

def start_p2p_server(username: str, host="0.0.0.0", port=0) -> int:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    real_port = server_socket.getsockname()[1]
    server_socket.listen()

    print(f"[📡] Servidor P2P ouvindo em {host}:{real_port}")

    def accept_loop():
        while True:
            conn, addr = server_socket.accept()
            threading.Thread(target=handle_client, args=(username, conn, addr), daemon=True).start()

    threading.Thread(target=accept_loop, daemon=True).start()

    return real_port

if __name__ == "__main__":
    start_p2p_server("Test")
