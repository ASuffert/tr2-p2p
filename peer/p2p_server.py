import socket
import threading
import json
import os
import time

from peer.chat import store_message
from .chunk_manager import hash_file, get_chunks_available

message_queues = {}

def handle_client(username: str, conn: socket.socket, addr: tuple, queues: dict):
    base_dir = os.path.expanduser(f"~/p2p-tr2/{username}")
    
    try:
        with conn:
            data = conn.recv(2048).decode('utf-8').strip()
            if not data:
                return
            request = json.loads(data)
            print(f"[P2P Server] Recebido de {addr}: {request['type']}")

            req_type = request.get("type")
            file_hash = request.get("file_hash")

            if req_type == "chunk_map":
                chunks = get_chunks_available(base_dir, file_hash)
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

                file_chunk_dir = os.path.join(base_dir, file_hash)

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

            elif req_type == "get_chat_history":
                room_id = request.get("room_id")
                history_path = os.path.join(base_dir, "chats", f"{room_id}.json")
                history = []
                if os.path.exists(history_path):
                    with open(history_path, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                response = {"status": "success", "history": history}
                conn.sendall(json.dumps(response).encode('utf-8'))

            elif req_type == "broadcast_message":
                room_id = request.get("room_id")
                message_data = request.get("message")
                
                if room_id in queues:
                    queues[room_id].put(message_data)
                store_message(username, room_id, message_data)
                
                conn.sendall(json.dumps({"status": "success"}).encode('utf-8'))
            
            else:
                conn.sendall(json.dumps({"status": "error", "message": "Requisicao invalida"}).encode('utf-8'))

    except Exception as e:
        print(f"[!] Erro ao lidar com cliente P2P {addr}: {e}")

def start_p2p_server(username: str, queues: dict, host="0.0.0.0", port=0) -> int:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    real_port = server_socket.getsockname()[1]
    server_socket.listen()

    print(f"[📡] Servidor P2P ouvindo em {host}:{real_port}")

    def accept_loop():
        while True:
            try:
                conn, addr = server_socket.accept()
                handler_thread = threading.Thread(target=handle_client, args=(username, conn, addr, queues), daemon=True)
                handler_thread.start()
            except Exception as e:
                print(f"Erro no loop de aceitação do P2P Server: {e}")
                break

    threading.Thread(target=accept_loop, daemon=True).start()
    return real_port

if __name__ == "__main__":
    test_queues = {}
    start_p2p_server("TestUser", test_queues)
    while True:
        time.sleep(1)