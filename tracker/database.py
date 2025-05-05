import sqlite3

DB_FILE = 'tracker.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    ''')

    # Tabela de arquivos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            hash TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            size INTEGER NOT NULL
        )
    ''')

    # Associação arquivos ↔ peers
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_peers (
            file_hash TEXT,
            peer_address TEXT,
            FOREIGN KEY (file_hash) REFERENCES files(hash)
        )
    ''')

    conn.commit()
    conn.close()
