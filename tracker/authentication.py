import sqlite3
import hashlib
import os

from database import init_db, DB_FILE


def hash_password(password: str, salt: str = None):
    salt = salt or os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(stored_hash, input_password):
    try:
        salt, hash_val = stored_hash.split("$")
        return hash_password(input_password, salt) == stored_hash
    except Exception:
        return False


def register_user(username: str, password: str):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        # Verifica se já existe
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, "Usuário já existe."

        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        conn.commit()
        return True, "Usuário registrado com sucesso."
    except Exception as e:
        return False, f"Erro ao registrar: {e}"
    finally:
        conn.close()


def login_user(username: str, password: str):
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

        if verify_password(row[0], password):
            return True, "Login bem-sucedido."
        else:
            return False, "Senha incorreta."
    except Exception as e:
        return False, f"Erro ao fazer login: {e}"
    finally:
        conn.close()
