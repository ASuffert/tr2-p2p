import socket
import json
import os
import hashlib

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


def login():
    user = input("Usuário: ")
    pwd = input("Senha: ")
    res = send_request({"type": "login", "username": user, "password": pwd})
    print(res["message"])


def announce_file():
    path = input("Caminho do arquivo: ")
    if not os.path.isfile(path):
        print("Arquivo não encontrado.")
        return

    size = os.path.getsize(path)
    hash_ = hash_file(path)
    name = os.path.basename(path)
    peer_address = input("Endereço do peer (ex: 192.168.0.100:6000): ")

    res = send_request(
        {
            "type": "register_file",
            "filename": name,
            "size": size,
            "hash": hash_,
            "peer_address": peer_address,
        }
    )

    print(res["message"])


def list_files():
    res = send_request({"type": "list_files"})
    for f in res.get("files", []):
        print(f"{f['filename']} ({f['size']} bytes) [{len(f['peers'])} peers]")


def main():
    while True:
        print("\n1. Registrar")
        print("2. Login")
        print("3. Anunciar Arquivo")
        print("4. Listar Arquivos")
        print("0. Sair")
        op = input("> ")

        if op == "1":
            register()
        elif op == "2":
            login()
        elif op == "3":
            announce_file()
        elif op == "4":
            list_files()
        elif op == "0":
            break


if __name__ == "__main__":
    main()
