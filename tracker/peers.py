import sqlite3
import time

from tracker.database import DB_FILE

peers_online = {}

HEARTBEAT_TIMEOUT = 300
CLEANUP_INTERVAL = 60


def receive_heartbeat(username, peer_address):
    if username not in peers_online:
        peers_online[username] = {"peer_address": peer_address, "last_seen": time.time(), "first_seen": time.time()}
    else:
        peers_online[username].update({"peer_address": peer_address, "last_seen": time.time()})


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


def calculate_tier(username) -> tuple[str, int]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT username, SUM(size) as total_bytes
        FROM files
        JOIN file_peers ON files.hash = file_peers.file_hash
        GROUP BY username
    """)
    bytes_por_peer = {row[0]: row[1] or 0 for row in cursor.fetchall()}

    max_bytes = max(bytes_por_peer.values()) if bytes_por_peer else 0
    bytes_do_peer = bytes_por_peer.get(username, 0)

    tempos = {}
    now = int(time.time())

    for user, info in peers_online.items():
        uptime = now - info["first_seen"]
        tempos[user] = uptime

    max_uptime = max(tempos.values()) if tempos else 0
    uptime_do_peer = tempos.get(username, 0)

    proporcao_arquivos = bytes_do_peer / max_bytes if max_bytes > 0 else 0
    proporcao_tempo = uptime_do_peer / max_uptime if max_uptime > 0 else 0

    score = (0.7 * proporcao_arquivos) + (0.3 * proporcao_tempo)

    if score >= 0.75:
        return "IV", 6
    elif score >= 0.5:
        return "III", 4
    elif score >= 0.25:
        return "II", 2
    else:
        return "I", 1

