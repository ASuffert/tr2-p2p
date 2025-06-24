import os
import hashlib

CHUNK_SIZE = 64 * 1024  # 64KB por padrão

def hash_file(filepath):
    sha = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(4096):
            sha.update(chunk)
    return sha.hexdigest()


def split_file(filepath, chunk_dir, chunk_size=CHUNK_SIZE):
    chunk_dir = os.path.expanduser(chunk_dir)
    os.makedirs(chunk_dir, exist_ok=True)

    chunks = []
    with open(filepath, 'rb') as f:
        index = 0
        while data := f.read(chunk_size):
            sha = hashlib.sha256(data).hexdigest()
            chunk_name = f"{index}_{sha}"
            chunk_path = os.path.join(chunk_dir, chunk_name)

            with open(chunk_path, 'wb') as cf:
                cf.write(data)

            chunks.append({"index": index, "hash": sha})
            index += 1

    file_hash = hash_file(filepath)

    return {
        "filename": os.path.basename(filepath),
        "size": os.path.getsize(filepath),
        "file_hash": file_hash,
        "chunks": chunks
    }


def validate_chunk(chunk_path):
    filename = os.path.basename(chunk_path)
    try:
        index, expected_hash = filename.split("_", 1)
    except ValueError:
        print(f"[!] Nome inválido para chunk: {filename}")
        return False

    real_hash = hash_file(chunk_path)
    return real_hash == expected_hash


def reassemble_file(chunk_dir, output_path):
    chunks = []

    for fname in os.listdir(chunk_dir):
        if "_" not in fname:
            continue
        try:
            index, hash_part = fname.split("_", 1)
            chunks.append((int(index), fname))
        except ValueError:
            continue

    if not chunks:
        print("[!] Nenhum chunk encontrado.")
        return False

    chunks.sort(key=lambda x: x[0])

    with open(output_path, 'wb') as out:
        for index, fname in chunks:
            chunk_path = os.path.join(chunk_dir, fname)

            if not validate_chunk(chunk_path):
                print(f"[!] Chunk inválido detectado: {fname}")
                return False

            with open(chunk_path, 'rb') as cf:
                out.write(cf.read())
    return True


def get_chunks_available(chunk_dir: str, file_hash: str) -> list[int]:
    file_chunk_dir = os.path.join(chunk_dir, file_hash)
    if not os.path.isdir(file_chunk_dir):
        return []

    chunks = []
    for fname in os.listdir(file_chunk_dir):
        if "_" not in fname:
            continue
        try:
            index_str, _ = fname.split("_", 1)
            idx = int(index_str)
            chunks.append(idx)
        except ValueError:
            continue
    return sorted(chunks)
