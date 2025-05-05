import time

peers_online = {}

HEARTBEAT_TIMEOUT = 300


def receive_heartbeat(username, peer_address):
    peers_online[username] = {"peer_address": peer_address, "last_seen": time.time()}


def list_active_peers():
    now = time.time()
    return [
        {"username": u, "address": info["peer_address"]}
        for u, info in peers_online.items()
        if now - info["last_seen"] < HEARTBEAT_TIMEOUT
    ]
