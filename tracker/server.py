import socket
import threading
import json

from authentication import register_user, login_user
from files import register_file, list_files
from peers import cleanup_loop, receive_heartbeat, list_active_peers, calculate_tier
from session import create_session, validate_session
from database import init_db
from chat_manager import create_chat_room, delete_chat_room, get_user_chats, add_member_to_chat, get_chat_members_with_addresses, remove_member_from_chat

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
                    if not request.get("username") or not request.get("password"):
                        success, msg = False, "Usuário e senha são obrigatórios"
                    else:
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
                    peer_port = request.get("port")
                    username = validate_session(token)
                    peer_address = f"{addr[0]}:{peer_port}"
                    if username:
                        receive_heartbeat(username, peer_address)
                        success, msg = True, "heartbeat recebido"
                    else:
                        success, msg = False, "Token inválido ou ausente"
                case "list_active_peers":
                    peers = list_active_peers()
                    success = True
                    extra_payload["peers"] = peers
                case "get_user_tier":
                    token = request.get("token")
                    username = validate_session(token)
                    tier, max_connections = calculate_tier(username)
                    success = True
                    extra_payload["tier"] = tier
                    extra_payload["max_connections"] = max_connections

                case "create_chat_room":
                    room_name = request.get("room_name")
                    is_private = request.get("is_private", 0)
                    invited_user = request.get("invited_user")
                    if not room_name:
                        success, msg = False, "O nome da sala é obrigatório."
                    else:
                        room_id, msg = create_chat_room(room_name, username, is_private, invited_user)
                        if room_id:
                            success = True
                            extra_payload["room_id"] = room_id
                        else:
                            success = False
                
                case "list_my_chats":
                    chats = get_user_chats(username)
                    success = True
                    extra_payload["chats"] = chats

                case "add_chat_member":
                    room_id = request.get("room_id")
                    user_to_add = request.get("user_to_add")
                    success, msg = add_member_to_chat(room_id, user_to_add, username)

                case "remove_chat_member":
                    room_id = request.get("room_id")
                    user_to_remove = request.get("user_to_remove")
                    success, msg = remove_member_from_chat(room_id, user_to_remove, username)

                case "delete_chat_room":
                    room_id = request.get("room_id")
                    success, msg = delete_chat_room(room_id, username)
                    if success:
                        extra_payload["action"] = "close_window"

                case "get_chat_members":
                    room_id = request.get("room_id")
                    members = get_chat_members_with_addresses(room_id)
                    success = True
                    extra_payload["members"] = members

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
    init_db()

    threading.Thread(target=cleanup_loop, daemon=True).start()

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
