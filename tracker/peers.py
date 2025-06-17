import sqlite3
import time

from database import DB_FILE

peers_online = {}

HEARTBEAT_TIMEOUT = 300
CLEANUP_INTERVAL = 60


def receive_heartbeat(username, peer_address):
    peers_online[username] = {"peer_address": peer_address, "last_seen": time.time()}


def list_active_peers():
    now = time.time()
    return [
        {"username": u, "address": info["peer_address"]}
        for u, info in peers_online.items()
        if now - info["last_seen"] < HEARTBEAT_TIMEOUT
    ]

def cleanup_inactive_peers():
    now = time.time()
    to_remove = [u for u, data in peers_online.items()
                 if now - data["last_seen"] > HEARTBEAT_TIMEOUT]

    if not to_remove:
        return

    with sqlite3.connect(DB_FILE) as conn:
        for username in to_remove:
            print(f"[!] Peer inativo detectado: {username} — removendo seus arquivos")
            conn.execute("DELETE FROM file_peers WHERE username = ?", (username,))

            orphaned_files = conn.execute("""
                SELECT f.hash FROM files f
                LEFT JOIN file_peers fp ON f.hash = fp.file_hash
                WHERE fp.file_hash IS NULL
            """).fetchall()

            for (file_hash,) in orphaned_files:
                print(f"    ⤷ Removendo metadados de arquivo órfão: {file_hash}")
                conn.execute("DELETE FROM files WHERE hash = ?", (file_hash,))

            del peers_online[username]
        conn.commit()

def cleanup_loop():
    while True:
        cleanup_inactive_peers()
        time.sleep(CLEANUP_INTERVAL)
