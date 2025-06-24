import tkinter as tk
from tkinter import messagebox, Listbox, filedialog
from tkinter import ttk
import threading
import time
import os

from peer.chunk_manager import split_file, hash_file
from peer.gui.utils import send_request
from peer.p2p_client import download_file


class FileManagerWindow(tk.Toplevel):
    def __init__(self, parent, token, username):
        super().__init__(parent)
        self.title(f"Gerenciador de Arquivos - {username}")
        self.geometry("700x500")
        self.token = token
        self.username = username
        self.files_data = []

        login_status_label = tk.Label(self, text=f"Você está logado como: {self.username}", font=("Arial", 9, "italic"),
                                      relief=tk.SUNKEN, anchor='w')
        login_status_label.pack(side=tk.TOP, fill='x', padx=10, pady=(5, 0))

        top_frame = tk.Frame(self)
        top_frame.pack(pady=5, padx=10, fill='x')
        tk.Button(top_frame, text="Anunciar Novo Arquivo", command=self._announce_file_thread).pack(side='left')
        tk.Button(top_frame, text="Atualizar Lista", command=self._list_files_thread).pack(side='left', padx=5)

        list_frame = tk.Frame(self)
        list_frame.pack(pady=5, padx=10, fill='both', expand=True)
        self.files_listbox = Listbox(list_frame, font=("Courier", 10))
        self.files_listbox.pack(side='left', fill='both', expand=True)
        scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=self.files_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.files_listbox.config(yscrollcommand=scrollbar.set)
        self.files_listbox.bind("<<ListboxSelect>>", self._on_file_select)

        bottom_frame = tk.Frame(self)
        bottom_frame.pack(pady=10, padx=10, fill='x')
        self.details_label = tk.Label(bottom_frame, text="Selecione um arquivo para ver os detalhes.", justify='left')
        self.details_label.pack(side='left')
        tk.Button(bottom_frame, text="Baixar Selecionado", command=self._download_file_thread).pack(side='right')

        self.progress_bar = ttk.Progressbar(self, orient='horizontal', length=100, mode='determinate')
        self.progress_bar.pack(pady=5, padx=10, fill='x')

        self._list_files_thread()

    def _on_file_select(self, event=None):
        selected_indices = self.files_listbox.curselection()
        if not selected_indices: return

        file_data = self.files_data[selected_indices[0]]
        online_peers = len([p for p in file_data['peers_info'] if p['address']])
        details_text = f"Nome: {file_data['filename']}\nTamanho: {file_data['size']:,} bytes\nPeers: {online_peers}/{len(file_data['peers_info'])} online"
        self.details_label.config(text=details_text)

    def _list_files_thread(self):
        threading.Thread(target=self._list_files, daemon=True).start()

    def _list_files(self):
        res = send_request({"type": "list_files", "token": self.token})
        self.files_data = res.get("files", [])

        self.files_listbox.delete(0, tk.END)
        print(self.files_data)
        for f in self.files_data:
            name = f['filename'].ljust(40)
            size = f"{f['size']:,}".rjust(15)
            peers = f"({len(f['peers_info'])} peers)".ljust(10)
            self.files_listbox.insert(tk.END, f"{name}{peers}{size} bytes")

    def _announce_file_thread(self):
        threading.Thread(target=self._announce_file, daemon=True).start()

    def _announce_file(self):
        filepath = filedialog.askopenfilename(title="Selecione o arquivo para anunciar")
        if not filepath: return

        base_dir = os.path.expanduser(f"~/p2p-tr2/{self.username}")
        os.makedirs(base_dir, exist_ok=True)
        messagebox.showinfo("Anunciando", f"Processando {os.path.basename(filepath)}...", parent=self)

        file_hash = hash_file(filepath)
        chunk_dir = os.path.join(base_dir, file_hash)
        split_file(filepath, chunk_dir)

        payload = {"type": "register_file", "token": self.token, "filename": os.path.basename(filepath),
                   "size": os.path.getsize(filepath), "hash": file_hash}
        res = send_request(payload)
        messagebox.showinfo("Anunciar Arquivo", res.get("message"), parent=self)
        self._list_files()

    def _download_file_thread(self):
        selected_indices = self.files_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Aviso", "Selecione um arquivo para baixar.", parent=self)
            return
        file_data = self.files_data[selected_indices[0]]
        threading.Thread(target=self._download_file, args=(file_data,), daemon=True).start()

    def _download_file(self, file_data):
        file_hash, filename, total_size = file_data['hash'], file_data['filename'], file_data['size']

        res = send_request({"type": "get_user_tier", "token": self.token})
        if res["status"] != "success":
            messagebox.showerror("Erro", res["message"])
            return
        max_connections = res["max_connections"]

        res = send_request({"type": "list_active_peers", "token": self.token})
        if res["status"] != "success":
            messagebox.showerror("Erro", res["message"])
            return

        peers = res.get("peers", [])

        if not peers:
            messagebox.showerror("Erro", "Nenhum peer ativo no momento.")
            return

        start_time = time.time()
        success = download_file(self.username, filename, file_hash, total_size,
                                [peer["address"] for peer in peers if peer["username"] != self.username], max_connections)
        print("Download took %.3f seconds." % (time.time() - start_time))
        if success:
            messagebox.showinfo("Download", f"Arquivo {filename} baixado com sucesso.")
        else:
            messagebox.showerror("Erro", f"Falha ao baixar o arquivo {filename}.")
