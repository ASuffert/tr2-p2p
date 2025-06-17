import sqlite3
import hashlib
import os

from database import init_db, DB_FILE


def register_user(username: str, password: str):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, "Usuário já existe."

        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password),
        )
        conn.commit()
        return True, "Usuário registrado com sucesso."
    except Exception as e:
        return False, f"Erro ao registrar: {e}"
    finally:
        conn.close()


def login_user(username: str, password_hash: str):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT password_hash FROM users WHERE username = ?", (username,)
        )
        row = cursor.fetchone()
        if not row:
            return False, "Usuário não encontrado."

        if row[0] == password_hash:
            return True, "Login bem-sucedido."
        else:
            return False, "Senha incorreta."
    except Exception as e:
        return False, f"Erro ao fazer login: {e}"
    finally:
        conn.close()
