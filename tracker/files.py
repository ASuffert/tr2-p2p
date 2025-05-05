import sqlite3
from database import DB_FILE, init_db


def register_file(file_hash, filename, size, peer_address):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Inserir se não existir
    cursor.execute(
        "INSERT OR IGNORE INTO files (hash, filename, size) VALUES (?, ?, ?)",
        (file_hash, filename, size),
    )

    # Associar peer ao arquivo
    cursor.execute(
        "INSERT INTO file_peers (file_hash, peer_address) VALUES (?, ?)",
        (file_hash, peer_address),
    )

    conn.commit()
    conn.close()


def list_files():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
                   SELECT f.filename, f.size, f.hash, group_concat(fp.peer_address)
                   FROM files f
                            LEFT JOIN file_peers fp ON f.hash = fp.file_hash
                   GROUP BY f.hash
                   """
    )

    results = cursor.fetchall()
    conn.close()

    files = []
    for filename, size, hash_, peers in results:
        files.append(
            {
                "filename": filename,
                "size": size,
                "hash": hash_,
                "peers": peers.split(",") if peers else [],
            }
        )
    return files
