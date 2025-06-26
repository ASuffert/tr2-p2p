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

    # Tabela de salas de chat
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_name TEXT NOT NULL,
            owner_username TEXT NOT NULL,
            is_private INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(owner_username) REFERENCES users(username)
        )
    """)

    # Tabela de associação de membros da sala de chat
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_members (
            room_id INTEGER,
            username TEXT,
            FOREIGN KEY(room_id) REFERENCES chat_rooms(id),
            FOREIGN KEY(username) REFERENCES users(username),
            PRIMARY KEY (room_id, username)
        )
    """)

    conn.commit()
    conn.close()