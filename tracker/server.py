import socket
import threading
import json

from authentication import register_user, login_user
from files import register_file, list_files
from peers import receive_heartbeat, list_active_peers
from session import create_session, validate_session

HOST = "0.0.0.0"
PORT = 5000


def handle_client(conn, addr):
    try:
        with conn:
            data = conn.recv(8192).decode()
            request = json.loads(data)
            print(f"[{addr[0]}:{addr[1]}] Request: {request}")
            if request["type"] not in ["register", "login"]:
                token = request.get("token")
                username = validate_session(token)
                if not username:
                    conn.sendall(json.dumps({
                        "status": "error",
                        "message": "Token inválido ou expirado"
                    }).encode())
                    return

            request = json.loads(data)
            req_type = request.get("type")
            success, msg = False, ""
            extra_payload = {}

            match req_type:
                case "register":
                    success, msg = register_user(request["username"], request["password"])

                case "login":
                    success, msg = login_user(request["username"], request["password"])
                    if success:
                        token = create_session(request["username"])
                        extra_payload["token"] = token

                case "register_file":
                    token = request.get("token")
                    username = validate_session(token)
                    if not username:
                        success, msg = False, "Token inválido ou expirado"
                    else:
                        register_file(
                            request["hash"],
                            request["filename"],
                            request["size"],
                            username
                        )
                        success, msg = True, "Arquivo registrado com sucesso."

                case "list_files":
                    files = list_files()
                    success = True
                    extra_payload["files"] = files

                case "heartbeat":
                    token = request.get("token")
                    username = validate_session(token)
                    peer_address = f"{addr[0]}:{addr[1]}"
                    if username:
                        receive_heartbeat(username, peer_address)
                        success, msg = True, "heartbeat recebido"
                    else:
                        success, msg = False, "Token inválido ou ausente"
                    # resposta será enviada abaixo
                case "list_active_peers":
                    peers = list_active_peers()
                    success = True
                    extra_payload["peers"] = peers

                case _:
                    success, msg = False, "Requisição inválida."

            response = {
                "status": "success" if success else "error",
                "message": msg
            }
            response.update(extra_payload)
            print(f"[{addr[0]}:{addr[1]}] Response: {response}")
            conn.sendall(json.dumps(response).encode()) 

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
