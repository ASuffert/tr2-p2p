import os
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import hashlib
import json
import socket

from chunk_manager import split_file
from p2p_client import download_file
from p2p_server import start_p2p_server

TRACKER_HOST = "localhost"
TRACKER_PORT = 5000

HEARTBEAT_INTERVAL = 60


def send_request(payload):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((TRACKER_HOST, TRACKER_PORT))
        s.sendall(json.dumps(payload).encode())
        return json.loads(s.recv(8192).decode())

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class P2PApp(tk.Tk):
    def __init__(self, auto_login_username: str = None, auto_login_password: str = None):
        super().__init__()
        self.title("Cliente P2P")
        self.geometry("400x300")
        self.resizable(False, False)
        self.username = None
        self.token = None
        self.peer_port = None
        self.auto_login_username = auto_login_username
        self.auto_login_password = auto_login_password
        self.show_login()

    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()
    
    def heartbeat_loop(self):
        while True:
            try:
                send_request({
                    "type": "heartbeat",
                    "token": self.token,
                    "port": self.peer_port,
                })
            except Exception as e:
                print(f"[!] Erro ao enviar heartbeat: {e}")
            time.sleep(60)

    def show_login(self):
        self.clear_window()

        tk.Label(self, text="Usuário").pack(pady=5)
        entry_user = tk.Entry(self)
        entry_user.pack()

        tk.Label(self, text="Senha").pack(pady=5)
        entry_pwd = tk.Entry(self, show="*")
        entry_pwd.pack()

        def try_login():
            user = entry_user.get()
            pwd = hash_password(entry_pwd.get())
            res = send_request({"type": "login", "username": user, "password": pwd})
            if res["status"] == "success":
                self.username = user
                self.token = res["token"]
                self.peer_port = start_p2p_server(self.username)
                threading.Thread(target=self.heartbeat_loop, daemon=True).start()
                self.show_main_menu()
            else:
                messagebox.showerror("Erro", res["message"])

        def try_register():
            user = entry_user.get()
            pwd = hash_password(entry_pwd.get())
            res = send_request({"type": "register", "username": user, "password": pwd})
            messagebox.showinfo("Registro", res["message"])

        entry_pwd.bind('<Return>', lambda event: try_login())

        tk.Button(self, text="Login", command=try_login).pack(pady=10)
        tk.Button(self, text="Registrar", command=try_register).pack()

        if self.auto_login_username and self.auto_login_password:
            entry_user.insert(0, self.auto_login_username)
            entry_pwd.insert(0, self.auto_login_password)
            try_login()

    def show_main_menu(self):
        self.clear_window()
        tk.Label(self, text=f"Usuário: {self.username}", font=("Arial", 12, "bold")).pack(pady=10)

        tk.Button(self, text="Anunciar Arquivo", width=30, command=self.anunciar_arquivo).pack(pady=5)
        tk.Button(self, text="Buscar Arquivos", width=30, command=self.buscar_arquivos).pack(pady=5)
        tk.Button(self, text="Baixar Arquivo", width=30, command=self.baixar_arquivo).pack(pady=5)
        tk.Button(self, text="Listar Peers Ativos", width=30, command=self.listar_peers).pack(pady=5)
        tk.Button(self, text="Sair", width=30, command=self.quit).pack(pady=20)
    
    def hash_file(self, filepath):
        sha = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(4096):
                sha.update(chunk)
        return sha.hexdigest()

    def anunciar_arquivo(self):
        filepath = filedialog.askopenfilename(title="Selecione o arquivo para anunciar")
        if not filepath:
            return
        size = os.path.getsize(filepath)
        name = os.path.basename(filepath)
        file_hash = self.hash_file(filepath)

        split_file(filepath, f"~/p2p-tr2/{self.username}/{file_hash}")

        res = send_request({
            "type": "register_file",
            "filename": name,
            "size": size,
            "hash": file_hash,
            "token": self.token
        })

        if res["status"] == "success":
            messagebox.showinfo("Anúncio", "Arquivo anunciado com sucesso.")
        else:
            messagebox.showerror("Erro", res["message"])

    def buscar_arquivos(self):
        res = send_request({"type": "list_files", "token": self.token})
        if res["status"] != "success":
            messagebox.showerror("Erro", res["message"])
            return
        arquivos = res.get("files", [])
        texto = ""
        for arq in arquivos:
            texto += f"{arq['filename']} ({arq['size']} bytes)\nPeers: {', '.join(arq['peers'])}\n\n"
        if not texto:
            texto = "Nenhum arquivo disponível no momento."
        messagebox.showinfo("Arquivos Disponíveis", texto)

    def listar_peers(self):
        res = send_request({"type": "list_active_peers", "token": self.token})
        if res["status"] != "success":
            messagebox.showerror("Erro", res["message"])
            return
        peers = res.get("peers", [])
        texto = "\n".join(f"{p['username']} @ {p['address']}" for p in peers)
        if not texto:
            texto = "Nenhum peer ativo no momento."
        messagebox.showinfo("Peers Ativos", texto)

    def baixar_arquivo(self):
        res = send_request({"type": "get_user_tier", "token": self.token})
        if res["status"] != "success":
            messagebox.showerror("Erro", res["message"])
            return
        max_connections = res["max_connections"]
        tier = res["tier"]

        res = send_request({"type": "list_files", "token": self.token})
        if res["status"] != "success":
            messagebox.showerror("Erro", res["message"])
            return

        arquivos = res.get("files", [])
        if not arquivos:
            messagebox.showinfo("Info", "Nenhum arquivo disponível no momento.")
            return

        lista = "\n".join([f"{i}. {arq['filename']} ({arq['size']} bytes)" for i, arq in enumerate(arquivos)])
        choice = simpledialog.askinteger("Escolha o Arquivo", f"Selecione o arquivo:\n\n{lista}\n\nDigite o número:")

        if choice is None or choice < 0 or choice >= len(arquivos):
            messagebox.showinfo("Cancelado", "Operação cancelada.")
            return

        arq = arquivos[choice]
        filename = arq['filename']
        file_hash = arq['hash']
        size = arq['size']

        res = send_request({"type": "list_active_peers", "token": self.token})
        if res["status"] != "success":
            messagebox.showerror("Erro", res["message"])
            return

        peers = res.get("peers", [])

        if not peers:
            messagebox.showerror("Erro", "Nenhum peer ativo no momento.")
            return

        def run_download():
            start_time = time.time()
            success = download_file(self.username, filename, file_hash, size, [peer["address"] for peer in peers if peer["username"] != self.username], max_connections)
            print("Download took %.3f seconds." % (time.time() - start_time))
            if success:
                messagebox.showinfo("Download", f"Arquivo {filename} baixado com sucesso.")
            else:
                messagebox.showerror("Erro", f"Falha ao baixar o arquivo {filename}.")

        # Executa em thread para não travar a GUI
        threading.Thread(target=run_download, daemon=True).start()
if __name__ == "__main__":
    if len(sys.argv) >= 2:
        peer = sys.argv[1]
        username = peer
        app = P2PApp(auto_login_username=username, auto_login_password="test")
    else:
        app = P2PApp()

    app.mainloop()
