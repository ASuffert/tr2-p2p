import hashlib
import json
import socket

TRACKER_HOST = "localhost"
TRACKER_PORT = 5000


def send_request(payload):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((TRACKER_HOST, TRACKER_PORT))
            s.sendall(json.dumps(payload).encode('utf-8'))
            response_data = s.recv(16384).decode('utf-8')
            return json.loads(response_data)
    except Exception as e:
        print(f"\n[!] Erro na comunicação com o tracker: {e}")
        return {"status": "error", "message": "Não foi possível conectar ao tracker."}


def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()
