import sqlite3
from database import DB_FILE, init_db
from peers import peers_online

def register_file(file_hash: str, filename: str, size: int, username: str):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO files (hash, filename, size) VALUES (?, ?, ?)", (file_hash, filename, size))
    cursor.execute("INSERT OR IGNORE INTO file_peers (file_hash, username) VALUES (?, ?)", (file_hash, username))
    conn.commit()
    conn.close()

def list_files():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
           SELECT f.filename, f.size, f.hash, group_concat(fp.username)
           FROM files f
                    LEFT JOIN file_peers fp ON f.hash = fp.file_hash
           GROUP BY f.hash
           """
    )
    results = cursor.fetchall()
    conn.close()

    files = []
    for filename, size, hash_, peers_str in results:
        peer_usernames = peers_str.split(',') if peers_str else []
        
        peers_info = []
        for name in peer_usernames:
            peer_details = peers_online.get(name)
            address = peer_details['peer_address'] if peer_details else None
            peers_info.append({
                "username": name,
                "address": address
            })

        files.append({
            "filename": filename,
            "size": size,
            "hash": hash_,
            "peers_info": peers_info,
        })
    return files