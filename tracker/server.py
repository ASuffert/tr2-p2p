import socket
import threading
import json

from authentication import register_user, login_user
from files import register_file, list_files
from peers import receive_heartbeat, list_active_peers

HOST = "0.0.0.0"
PORT = 5000


def handle_client(conn, addr):
    try:
        with conn:
            data = conn.recv(8192).decode()
            request = json.loads(data)

            if request["type"] == "register":
                success, msg = register_user(request["username"], request["password"])

            elif request["type"] == "login":
                success, msg = login_user(request["username"], request["password"])

            elif request["type"] == "register_file":
                register_file(
                    request["hash"],
                    request["filename"],
                    request["size"],
                    request["peer_address"],
                )
                success, msg = True, "Arquivo registrado com sucesso."

            elif request["type"] == "list_files":
                files = list_files()
                conn.sendall(json.dumps({"status": "success", "files": files}).encode())
                return

            elif request["type"] == "heartbeat":
                username = request.get("username")
                peer_address = request.get("peer_address") or f"{addr[0]}:{addr[1]}"
                if username:
                    receive_heartbeat(username, peer_address)
                    conn.sendall(
                        json.dumps(
                            {"status": "success", "message": "heartbeat recebido"}
                        ).encode()
                    )
                else:
                    conn.sendall(
                        json.dumps(
                            {"status": "error", "message": "username ausente"}
                        ).encode()
                    )
                return

            elif request["type"] == "list_active_peers":
                peers = list_active_peers()
                conn.sendall(json.dumps({"status": "success", "peers": peers}).encode())
                return

            else:
                success, msg = False, "Requisição inválida."

            conn.sendall(
                json.dumps(
                    {"status": "success" if success else "error", "message": msg}
                ).encode()
            )

    except Exception as e:
        conn.sendall(json.dumps({"status": "error", "message": str(e)}).encode())


def start_server():
    from database import init_db

    init_db()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"[*] Tracker ativo em {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            threading.Thread(
                target=handle_client, args=(conn, addr), daemon=True
            ).start()


if __name__ == "__main__":
    start_server()
