import json
import os


def store_message(username: str, room_id: str, message_data: dict):
    base_dir = os.path.expanduser(f"~/p2p-tr2/{username}")
    chat_log_dir = os.path.join(base_dir, "chats")
    os.makedirs(chat_log_dir, exist_ok=True)
    history_path = os.path.join(chat_log_dir, f"{room_id}.json")

    current_history = []
    if os.path.exists(history_path):
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                current_history = json.load(f)
        except json.JSONDecodeError:
            pass

    current_history.append(message_data)
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(current_history, f, indent=2, ensure_ascii=False)
