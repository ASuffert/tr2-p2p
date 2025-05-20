import sqlite3

DB_FILE = "tracker.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Tabela de usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    """)

    # Tabela de arquivos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            hash TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            size INTEGER NOT NULL
        )
    """)

    # Associação arquivos ↔ peers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_peers (
            file_hash TEXT,
            username TEXT NOT NULL,
            FOREIGN KEY (file_hash) REFERENCES files(hash),
            FOREIGN KEY(username) REFERENCES users(username),
            PRIMARY KEY (file_hash, username)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    """)

    conn.commit()
    conn.close()
