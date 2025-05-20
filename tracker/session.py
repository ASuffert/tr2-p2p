import sqlite3
import uuid
import time
from database import DB_FILE

SESSION_TIMEOUT = 3600

def create_session(username):
    token = str(uuid.uuid4())
    now = int(time.time())
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            INSERT INTO sessions (token, username, last_seen)
            VALUES (?, ?, ?)
        ''', (token, username, now))
    return token

def validate_session(token):
    now = int(time.time())
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.execute('''
            SELECT username, last_seen FROM sessions
            WHERE token = ?
        ''', (token,))
        row = cur.fetchone()
        if not row:
            return None
        username, last_seen = row
        if now - last_seen > SESSION_TIMEOUT:
            conn.execute('DELETE FROM sessions WHERE token = ?', (token,))
            return None
        conn.execute('UPDATE sessions SET last_seen = ? WHERE token = ?', (now, token))
        return username

def invalidate_session(token):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('DELETE FROM sessions WHERE token = ?', (token,))
