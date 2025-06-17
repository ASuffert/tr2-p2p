import hashlib
import os
import shutil
import sqlite3
import random
import subprocess
import sys

from peer.chunk_manager import split_file, hash_file


DB_FILE = "tracker/tracker.db"
BASE_DIR = os.path.expanduser("~/p2p-tr2")
TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "test_files")


PEERS = ["test1", "test2", "test3", "test4", "test5"]


def reset_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("[*] Limpando banco de dados...")

    tables = ["users", "sessions", "files", "file_peers", "active_peers"]

    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table}")
        except Exception:
            pass

    conn.commit()
    conn.close()


def reset_files():
    print(f"[*] Removendo diretório {BASE_DIR}...")
    if os.path.exists(BASE_DIR):
        shutil.rmtree(BASE_DIR)
    os.makedirs(BASE_DIR, exist_ok=True)


def init_test_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("[*] Populando usuários e sessões de teste...")

    users = [(peer, hashlib.sha256("test".encode()).hexdigest()) for peer in PEERS]
    cursor.executemany("INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)", users)

    conn.commit()
    conn.close()


def load_test_files():
    print("[*] Carregando arquivos da pasta test_files...")

    if not os.path.exists(TEST_FILES_DIR):
        raise Exception(f"Pasta {TEST_FILES_DIR} não encontrada!")

    filepaths = []

    for fname in os.listdir(TEST_FILES_DIR):
        src = os.path.join(TEST_FILES_DIR, fname)
        dst = os.path.join(BASE_DIR, fname)

        shutil.copyfile(src, dst)
        filepaths.append(dst)

    return filepaths


def register_files_and_chunks(filepaths):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    report = {}

    print("[*] Registrando arquivos e chunks...")

    for filepath in filepaths:
        file_hash = hash_file(filepath)
        file_size = os.path.getsize(filepath)
        filename = os.path.basename(filepath)

        report[file_hash] = {
            "filename": filename,
            "size": file_size,
            "peers": {}
        }

        # Diretório de chunks completo para 'test1'
        chunk_dir_test1 = os.path.join(BASE_DIR, "test1", file_hash)
        metadata = split_file(filepath, chunk_dir_test1)

        chunk_list = sorted([c for c in os.listdir(chunk_dir_test1) if "_" in c])

        # test1 → possui tudo (completo)
        cursor.execute("""
            INSERT OR IGNORE INTO file_peers (file_hash, username)
            VALUES (?, ?)
        """, (file_hash, "test1"))
        report[file_hash]["peers"]["test1"] = len(chunk_list)

        # test2 → metade dos chunks
        chunk_dir_test2 = os.path.join(BASE_DIR, "test2", file_hash)
        os.makedirs(chunk_dir_test2, exist_ok=True)
        for i, chunk in enumerate(chunk_list):
            if i % 2 == 0:
                src = os.path.join(chunk_dir_test1, chunk)
                dst = os.path.join(chunk_dir_test2, chunk)
                shutil.copyfile(src, dst)
        half_count = len([c for i, c in enumerate(chunk_list) if i % 2 == 0])
        cursor.execute("""
            INSERT OR IGNORE INTO file_peers (file_hash, username)
            VALUES (?, ?)
        """, (file_hash, "test2"))
        report[file_hash]["peers"]["test2"] = half_count

        # test3 → alguns chunks aleatórios (~30%)
        chunk_dir_test3 = os.path.join(BASE_DIR, "test3", file_hash)
        os.makedirs(chunk_dir_test3, exist_ok=True)
        selected = random.sample(chunk_list, max(1, len(chunk_list) // 3))
        for chunk in selected:
            src = os.path.join(chunk_dir_test1, chunk)
            dst = os.path.join(chunk_dir_test3, chunk)
            shutil.copyfile(src, dst)
        cursor.execute("""
            INSERT OR IGNORE INTO file_peers (file_hash, username)
            VALUES (?, ?)
        """, (file_hash, "test3"))
        report[file_hash]["peers"]["test3"] = len(selected)

        # test4 → não tem chunks, mas aparece no tracker
        cursor.execute("""
            INSERT OR IGNORE INTO file_peers (file_hash, username)
            VALUES (?, ?)
        """, (file_hash, "test4"))
        report[file_hash]["peers"]["test4"] = 0

        # test5 → não aparece no tracker (sem registro)
        report[file_hash]["peers"]["test5"] = 0

        # Registra o arquivo na tabela 'files'
        cursor.execute("""
            INSERT OR IGNORE INTO files (hash, filename, size)
            VALUES (?, ?, ?)
        """, (file_hash, filename, file_size))

        print(f"[✓] Arquivo {filename} registrado com hash {file_hash}")

    conn.commit()
    conn.close()

    return report


def launch_gui_for_peer(peer):
    print(f"[*] Iniciando interface para {peer}...")
    subprocess.Popen(["gnome-terminal", "--title", f"Peer {peer}", "--", sys.executable, "peer/gui.py", peer])


def print_report(report):
    print("\n========== RELATÓRIO DOS DADOS DE TESTE ==========\n")
    for file_hash, info in report.items():
        print(f"Arquivo: {info['filename']}")
        print(f"Hash: {file_hash}")
        print(f"Tamanho: {info['size']} bytes")
        print("Peers:")
        for peer, chunk_count in info["peers"].items():
            status = ""
            if chunk_count == 0 and peer in ["test4"]:
                status = "(no tracker, sem chunks)"
            elif chunk_count == 0 and peer == "test5":
                status = "(não registrado)"
            elif chunk_count == len([c for c in os.listdir(os.path.join(BASE_DIR, 'test1', file_hash)) if '_' in c]):
                status = "(completo)"
            elif chunk_count >= 1:
                status = "(incompleto)"

            print(f"  - {peer}: {chunk_count} chunks {status}")
        print("\n---------------------------------------------------\n")
    print("====================================================\n")


if __name__ == "__main__":
    print("[*] Resetando banco e arquivos de teste...")
    reset_db()
    reset_files()

    init_test_db()
    files = load_test_files()
    report = register_files_and_chunks(files)

    print_report(report)

    for peer in PEERS:
        launch_gui_for_peer(peer)

    print("[✓] Dados de teste populados com sucesso.")
