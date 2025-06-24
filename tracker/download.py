import sqlite3
import time

from peer.gui.utils import send_request, hash_password
from tracker.files import list_files
from tracker.peers import calculate_tier
from peer.p2p_client import download_file

DB_FILE = "tracker.db"

def obter_token(username, password="test"):
    res = send_request({
        "type": "login",
        "username": username,
        "password": hash_password(password)
    })

    if res.get("status") == "success":
        return res["token"]
    else:
        print(f"[X] Erro ao obter token de {username}: {res.get('message')}")
        return None


def testar_downloads_todos_usuarios():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT username FROM users")
    all_users = [row[0] for row in cursor.fetchall()]

    conn.close()

    arquivos = list_files()

    if not arquivos:
        print("Nenhum arquivo disponível para download.")
        return

    print(f"\n{'Username':<10} {'Tier':>4} {'Max Conn.':>10} {'Arquivo':<20} {'Status':<10} {'Tempo(s)':>10}")
    print("-" * 80)

    for user in all_users:
        tier, max_conn = calculate_tier(user)
        token = obter_token(user)

        res = send_request({"type": "list_active_peers", "token": token})
        active_peers = res.get("peers", [])

        for file in arquivos:
            start = time.time()
            success = download_file(
                username=user,
                filename=file['filename'],
                file_hash=file['hash'],
                size=file['size'],
                peers=[peer["address"] for peer in active_peers if peer["username"] != user],
                max_connections=max_conn,
                verbose=False
            )
            elapsed = time.time() - start

            status = "OK" if success else "FAIL"
            print(f"{user:<10} {tier:>4} {max_conn:>10} {file['filename']:<20} {status:<10} {elapsed:>10.2f}")

    print("-" * 80)


if __name__ == "__main__":
    testar_downloads_todos_usuarios()
