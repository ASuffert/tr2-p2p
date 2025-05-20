import socket
import json
import os
import hashlib
import threading
import time

TRACKER_HOST = "localhost"
TRACKER_PORT = 5000


def send_request(payload):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((TRACKER_HOST, TRACKER_PORT))
        s.sendall(json.dumps(payload).encode())
        return json.loads(s.recv(8192).decode())


def hash_file(filepath):
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(4096):
            sha.update(chunk)
    return sha.hexdigest()


def register():
    user = input("Usuário: ")
    pwd = input("Senha: ")
    res = send_request({"type": "register", "username": user, "password": pwd})
    print(res["message"])


def login() -> tuple[str | None, str | None]:
    user = input("Usuário: ")
    pwd = input("Senha: ")
    res = send_request({"type": "login", "username": user, "password": pwd})
    print(res["message"])
    if res["status"] == "success":
        session_token = res["token"]
        return user, session_token
    return None, None


def announce_file(token: str):
    path = input("Caminho do arquivo: ")
    if not os.path.isfile(path):
        print("Arquivo não encontrado.")
        return

    size = os.path.getsize(path)
    hash_ = hash_file(path)
    name = os.path.basename(path)

    res = send_request(
        {
            "type": "register_file",
            "filename": name,
            "size": size,
            "hash": hash_,
            "token": token,
        }
    )

    print(res["message"])


def list_files(token: str):
    res = send_request({"type": "list_files", "token": token})
    for f in res.get("files", []):
        print(f"{f['filename']} ({f['size']} bytes) [{len(f['peers'])} peers]")


def list_peers(token: str):
    res = send_request({"type": "list_active_peers", "token": token})
    for peer in res.get("peers", []):
        print(f"{peer['username']} @ {peer['address']}")


def heartbeat_loop(token: str):
    while True:
        send_request(
            {"type": "heartbeat", "token": token}
        )
        time.sleep(60)


def main():
    username = None
    token = None

    while not username:
        print("\n--- Sistema P2P - Menu Inicial ---")
        print("1. Registrar")
        print("2. Login")
        print("0. Sair")
        op = input("> ")

        if op == "1":
            register()
        elif op == "2":
            username, token = login()
            if username:
                threading.Thread(
                    target=heartbeat_loop, args=(token,), daemon=True
                ).start()
        elif op == "0":
            return

    while True:
        print(f"\n--- Usuário: {username} ---")
        print("1. Anunciar Arquivo")
        print("2. Listar Arquivos")
        print("3. Listar Peers Ativos")
        print("0. Sair")
        op = input("> ")

        if op == "1":
            announce_file(token)
        elif op == "2":
            list_files(token)
        elif op == "3":
            list_peers(token)
        elif op == "0":
            print("Saindo...")
            break


if __name__ == "__main__":
    main()
