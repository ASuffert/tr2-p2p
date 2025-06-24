import sqlite3
from database import DB_FILE
from peers import peers_online

def create_chat_room(room_name, owner_username):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chat_rooms (room_name, owner_username) VALUES (?, ?)", (room_name, owner_username))
            room_id = cursor.lastrowid
            cursor.execute("INSERT INTO chat_members (room_id, username) VALUES (?, ?)", (room_id, owner_username))
            conn.commit()
            return room_id, "Sala criada com sucesso."
    except Exception as e:
        return None, f"Erro ao criar sala: {e}"

def get_user_chats(username):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cr.id, cr.room_name, cr.owner_username
            FROM chat_rooms cr
            JOIN chat_members cm ON cr.id = cm.room_id
            WHERE cm.username = ?
        """, (username,))
        chats = [{"id": row[0], "name": row[1], "owner": row[2]} for row in cursor.fetchall()]
        return chats

def add_member_to_chat(room_id, user_to_add, requester_username):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT owner_username FROM chat_rooms WHERE id = ?", (room_id,))
            owner = cursor.fetchone()
            if not owner or owner[0] != requester_username:
                return False, "Apenas o moderador pode adicionar membros."
            
            cursor.execute("SELECT username FROM users WHERE username = ?", (user_to_add,))
            if not cursor.fetchone():
                return False, f"Usuário '{user_to_add}' não encontrado."

            cursor.execute("INSERT OR IGNORE INTO chat_members (room_id, username) VALUES (?, ?)", (room_id, user_to_add))
            conn.commit()
            return True, f"'{user_to_add}' adicionado à sala."
    except Exception as e:
        return False, f"Erro ao adicionar membro: {e}"
    
def remove_member_from_chat(room_id, user_to_remove, requester_username):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT owner_username FROM chat_rooms WHERE id = ?", (room_id,))
            owner = cursor.fetchone()
            if not owner or owner[0] != requester_username:
                return False, "Apenas o moderador pode remover membros."
            
            cursor.execute("DELETE FROM chat_members WHERE room_id = ? AND username = ?", (room_id, user_to_remove))
            if cursor.rowcount == 0:
                return False, f"Usuário '{user_to_remove}' não encontrado na sala."
            
            conn.commit()
            return True, f"'{user_to_remove}' removido da sala."
    except Exception as e:
        return False, f"Erro ao remover membro: {e}"

def get_chat_members_with_addresses(room_id):
    members = []
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM chat_members WHERE room_id = ?", (room_id,))
        rows = cursor.fetchall()
        for row in rows:
            username = row[0]
            peer_info = peers_online.get(username)
            address = peer_info['peer_address'] if peer_info else None
            members.append({"username": username, "address": address})
    return members

def delete_chat_room(room_id, requester_username):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Validação crucial: Apenas o dono pode remover a sala
            cursor.execute("SELECT owner_username FROM chat_rooms WHERE id = ?", (room_id,))
            owner = cursor.fetchone()
            if not owner or owner[0] != requester_username:
                return False, "Apenas o moderador pode remover a sala."

            # Remove todos os membros da sala primeiro
            cursor.execute("DELETE FROM chat_members WHERE room_id = ?", (room_id,))
            
            # Remove a sala em si
            cursor.execute("DELETE FROM chat_rooms WHERE id = ?", (room_id,))
            
            conn.commit()
            return True, "Sala removida com sucesso."
    except Exception as e:
        return False, f"Erro ao remover a sala: {e}"