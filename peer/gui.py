import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext, Listbox, filedialog
from tkinter import ttk
import socket
import json
import hashlib
import threading
import time
import queue
import datetime
import os
import random
from p2p_server import start_p2p_server, message_queues
from chunk_manager import split_file, reassemble_file, CHUNK_SIZE
from p2p_client import download_file

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

def hash_file(filepath):
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(4096):
            sha.update(chunk)
    return sha.hexdigest()

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()


class FileManagerWindow(tk.Toplevel):
    def __init__(self, parent, token, username):
        super().__init__(parent)
        self.title("Gerenciador de Arquivos")
        self.geometry("700x500")
        self.token = token
        self.username = username
        self.files_data = []

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

        payload = { "type": "register_file", "token": self.token, "filename": os.path.basename(filepath), "size": os.path.getsize(filepath), "hash": file_hash }
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
        
        res = send_request({"type": "list_active_peers", "token": self.token})
        if res["status"] != "success":
            messagebox.showerror("Erro", res["message"])
            return

        peers = res.get("peers", [])

        if not peers:
            messagebox.showerror("Erro", "Nenhum peer ativo no momento.")
            return

        start_time = time.time()
        success = download_file(self.username, filename, file_hash, total_size, [peer["address"] for peer in peers if peer["username"] != self.username])
        print("Download took %.3f seconds." % (time.time() - start_time))
        if success:
            messagebox.showinfo("Download", f"Arquivo {filename} baixado com sucesso.")
        else:
            messagebox.showerror("Erro", f"Falha ao baixar o arquivo {filename}.")

class ChatRoomWindow:
    def __init__(self, parent, token, username, chat_data):
        self.parent = parent
        self.token = token
        self.username = username
        self.chat_data = chat_data
        self.room_id = chat_data['id']
        self.owner = chat_data['owner']
        self.members = []

        self.msg_queue = queue.Queue()
        message_queues[self.room_id] = self.msg_queue

        self.window = tk.Toplevel(parent)
        self.window.title(f"Sala: {self.chat_data['name']} (Moderador: {self.owner})")
        self.window.geometry("500x600")
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.setup_menu()
        
        login_status_label = tk.Label(self.window, text=f"Você está logado como: {self.username}", font=("Arial", 9, "italic"), relief=tk.SUNKEN, anchor='w')
        login_status_label.pack(side=tk.TOP, fill='x', padx=10, pady=(0, 5))

        self.chat_box = scrolledtext.ScrolledText(self.window, state='disabled', wrap=tk.WORD, font=("Arial", 10))
        self.chat_box.pack(padx=10, pady=5, fill="both", expand=True)

        msg_frame = tk.Frame(self.window)
        msg_frame.pack(padx=10, pady=(5,0), fill="x")
        
        self.msg_entry = tk.Entry(msg_frame, font=("Arial", 10))
        self.msg_entry.pack(side=tk.LEFT, fill="x", expand=True, ipady=4)
        self.msg_entry.bind("<Return>", self.send_message_thread)

        send_btn = tk.Button(msg_frame, text="Enviar", command=self.send_message_thread)
        send_btn.pack(side=tk.RIGHT, padx=(5, 0))

        if self.username == self.owner:
            admin_frame = tk.Frame(self.window)
            admin_frame.pack(padx=10, pady=(2, 10), fill="x")

            add_member_btn = tk.Button(admin_frame, text="Adicionar Membro", command=self.add_member)
            add_member_btn.pack(side=tk.LEFT)

            remove_member_btn = tk.Button(admin_frame, text="Remover Membro", command=self.remove_member)
            remove_member_btn.pack(side=tk.LEFT, padx=5)
            
            delete_room_btn = tk.Button(admin_frame, text="Remover Sala", command=self.delete_room)
            delete_room_btn.pack(side=tk.LEFT)

        threading.Thread(target=self.fetch_history_and_members, daemon=True).start()
        self.check_queue()

    def setup_menu(self):
        menu_bar = tk.Menu(self.window)
        self.window.config(menu=menu_bar)
        room_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Opções da Sala", menu=room_menu)
        room_menu.add_command(label="Ver Membros", command=self.show_members)

    def add_member(self):
        user_to_add = simpledialog.askstring("Adicionar Membro", "Digite o nome do usuário a ser adicionado:", parent=self.window)
        if user_to_add:
            if user_to_add == self.username:
                messagebox.showwarning("Aviso", "Você não pode adicionar a si mesmo.", parent=self.window)
                return
            payload = {"type": "add_chat_member", "token": self.token, "room_id": self.room_id, "user_to_add": user_to_add}
            threading.Thread(target=self.send_add_member_request, args=(payload,), daemon=True).start()

    def remove_member(self):
        user_to_remove = simpledialog.askstring("Remover Membro", "Digite o nome do usuário a ser removido:", parent=self.window)
        if user_to_remove:
            if user_to_remove == self.username:
                messagebox.showwarning("Aviso", "Você não pode remover a si mesmo.", parent=self.window)
                return
            payload = {"type": "remove_chat_member", "token": self.token, "room_id": self.room_id, "user_to_remove": user_to_remove}
            threading.Thread(target=self.send_remove_member_request, args=(payload,), daemon=True).start()
    def delete_room(self):
        if not messagebox.askyesno("Confirmar Remoção", "Tem certeza que deseja remover esta sala permanentemente?", parent=self.window):
            return

        payload = {"type": "delete_chat_room", "token": self.token, "room_id": self.room_id}
        threading.Thread(target=self.send_delete_room_request, args=(payload,), daemon=True).start()

    def send_add_member_request(self, payload):
        res = send_request(payload)
        messagebox.showinfo("Adicionar Membro", res.get("message", "Nenhuma resposta do servidor."), parent=self.window)

    def send_remove_member_request(self, payload):
        res = send_request(payload)
        messagebox.showinfo("Remover Membro", res.get("message", "Nenhuma resposta do servidor."), parent=self.window)

    def send_delete_room_request(self, payload):
        res = send_request(payload)
        if res.get("status") == "success":
            messagebox.showinfo("Sala Removida", res.get("message"), parent=self.window)
            self.window.destroy()
        else:
            messagebox.showerror("Erro", res.get("message"), parent=self.window)
    
    def show_members(self):
        member_names = [f"- {m['username']} {'(Online)' if m['address'] else '(Offline)'}" for m in self.members]
        messagebox.showinfo("Membros da Sala", "\n".join(member_names), parent=self.window)

    def fetch_history_and_members(self):
        res = send_request({"type": "get_chat_members", "token": self.token, "room_id": self.room_id})
        if res.get('status') != 'success': self.display_message({"sender": "SISTEMA", "content": "Erro ao buscar lista de membros.", "timestamp": time.time()}); return
        self.members = res.get('members', [])
        moderator_info = next((m for m in self.members if m['username'] == self.owner), None)
        if not moderator_info or not moderator_info['address']: self.display_message({"sender": "SISTEMA", "content": "Moderador está offline. Histórico indisponível.", "timestamp": time.time()}); return
        try:
            mod_host, mod_port = moderator_info['address'].split(':')
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5); s.connect((mod_host, int(mod_port)))
                payload = {"type": "get_chat_history", "room_id": self.room_id}
                s.sendall(json.dumps(payload).encode('utf-8'))
                res = json.loads(s.recv(8192).decode('utf-8'))
                if res['status'] == 'success':
                    for msg in res['history']: self.display_message(msg)
                self.display_message({"sender": "SISTEMA", "content": "Você entrou na sala.", "timestamp": time.time()})
        except Exception as e: self.display_message({"sender": "SISTEMA", "content": f"Não foi possível obter o histórico: {e}", "timestamp": time.time()})

    def send_message_thread(self, event=None):
        threading.Thread(target=self.send_message, daemon=True).start()

    def send_message(self):
        message_text = self.msg_entry.get();
        if not message_text: return
        self.msg_entry.delete(0, tk.END)
        message_payload = {"sender": self.username, "content": message_text, "timestamp": time.time()}
        self.display_message(message_payload)
        active_members = [m for m in self.members if m['address'] and m['username'] != self.username]
        for member in active_members: threading.Thread(target=self._send_to_peer, args=(member, message_payload), daemon=True).start()

    def _send_to_peer(self, member, message_payload):
        try:
            host, port = member['address'].split(':')
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2); s.connect((host, int(port)))
                payload = {"type": "broadcast_message", "room_id": self.room_id, "message": message_payload}
                s.sendall(json.dumps(payload).encode('utf-8'))
        except Exception as e: print(f"Não foi possível enviar mensagem para {member['username']}: {e}")

    def display_message(self, msg_data):
        self.chat_box.config(state='normal')
        ts = datetime.datetime.fromtimestamp(msg_data['timestamp']).strftime('%H:%M:%S')
        sender = msg_data.get('sender', '???'); content = msg_data.get('content', '')
        self.chat_box.insert(tk.END, f"[{ts}] {sender}: {content}\n")
        self.chat_box.config(state='disabled'); self.chat_box.see(tk.END)

    def check_queue(self):
        try:
            while not self.msg_queue.empty(): self.display_message(self.msg_queue.get_nowait())
        finally: self.window.after(100, self.check_queue)
    
    def on_closing(self):
        if self.room_id in message_queues: del message_queues[self.room_id]
        self.window.destroy()

class P2PClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cliente P2P - Login")
        self.root.geometry("300x150")
        self.token = None
        self.username = None
        self.p2p_port = None
        self.opened_windows = {}
        
        self.chat_listbox = None
        
        self.setup_login_frame()

    def setup_login_frame(self):
        self.clear_frame()
        frame = tk.Frame(self.root)
        frame.pack(padx=10, pady=10)
        
        tk.Label(frame, text="Usuário:").grid(row=0, column=0, sticky="w", pady=2)
        self.user_entry = tk.Entry(frame)
        self.user_entry.grid(row=0, column=1, pady=2)

        tk.Label(frame, text="Senha:").grid(row=1, column=0, sticky="w", pady=2)
        self.pass_entry = tk.Entry(frame, show="*")
        self.pass_entry.grid(row=1, column=1, pady=2)

        tk.Button(frame, text="Login", command=self.attempt_login).grid(row=2, column=0, columnspan=2, pady=10)
        self.root.bind('<Return>', lambda event: self.attempt_login())

    def attempt_login(self):
        user = self.user_entry.get()
        pwd = self.pass_entry.get()
        if not user or not pwd:
            messagebox.showerror("Erro", "Usuário e senha são obrigatórios.")
            return

        res = send_request({"type": "login", "username": user, "password": hash_password(pwd)})
        if res.get("status") == "success":
            self.username = user
            self.token = res["token"]
            self.start_background_services()
            self.setup_main_lobby()
        else:
            messagebox.showerror("Login Falhou", res.get("message", "Erro desconhecido."))

    def start_background_services(self):
        self.p2p_port = start_p2p_server(self.username, message_queues)
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()

    def heartbeat_loop(self):
        while True:
            if not self.token: break
            send_request({"type": "heartbeat", "token": self.token, "port": self.p2p_port})
            time.sleep(60)

    def setup_main_lobby(self):
        self.clear_frame()
        self.root.title(f"Cliente P2P - {self.username}")
        self.root.geometry("300x200")
        
        tk.Label(self.root, text=f"Bem-vindo, {self.username}!", font=("Arial", 12)).pack(pady=10)
        tk.Button(self.root, text="Gerenciador de Arquivos", command=self.show_file_manager).pack(pady=5, ipadx=10)
        tk.Button(self.root, text="Gerenciador de Chat", command=self.show_chat_lobby).pack(pady=5, ipadx=10)
        
    def show_chat_lobby(self):
        if 'chat_lobby' in self.opened_windows and self.opened_windows['chat_lobby'].winfo_exists():
            self.opened_windows['chat_lobby'].lift()
            return
            
        chat_lobby = tk.Toplevel(self.root)
        self.opened_windows['chat_lobby'] = chat_lobby
        chat_lobby.title("Lobby de Chat")
        chat_lobby.geometry("400x300")
        
        btn_frame = tk.Frame(chat_lobby)
        btn_frame.pack(pady=5, padx=10, fill='x')
        tk.Button(btn_frame, text="Criar Nova Sala", command=self.create_room).pack(side='left')
        tk.Button(btn_frame, text="Atualizar Lista", command=self.refresh_chat_list).pack(side='left', padx=5)

        list_frame = tk.Frame(chat_lobby)
        list_frame.pack(pady=5, padx=10, fill='both', expand=True)
        
        self.chat_listbox = Listbox(list_frame)
        self.chat_listbox.pack(side='left', fill='both', expand=True)
        
        tk.Button(chat_lobby, text="Entrar na Sala", command=self.enter_selected_room).pack(pady=10)
        self.refresh_chat_list()
        
    def show_file_manager(self):
        if 'file_manager' in self.opened_windows and self.opened_windows['file_manager'].winfo_exists():
            self.opened_windows['file_manager'].lift()
        else:
            fm_window = FileManagerWindow(self.root, self.token, self.username)
            self.opened_windows['file_manager'] = fm_window

    def refresh_chat_list(self):
        if not self.chat_listbox or not self.chat_listbox.winfo_exists():
             return

        res = send_request({"type": "list_my_chats", "token": self.token})
        chats = res.get("chats", [])
        
        self.chat_listbox.chats_data = chats
        self.chat_listbox.delete(0, tk.END)
        for chat in chats:
            self.chat_listbox.insert(tk.END, f"{chat['name']} (Moderador: {chat['owner']})")

    def create_room(self):
        parent = self.opened_windows.get('chat_lobby')
        if not parent: return

        room_name = simpledialog.askstring("Nova Sala", "Digite o nome da sala:", parent=parent)
        if room_name:
            res = send_request({"type": "create_chat_room", "token": self.token, "room_name": room_name})
            messagebox.showinfo("Criar Sala", res.get("message"), parent=parent)
            self.refresh_chat_list()
    
    def enter_selected_room(self):
        selected_indices = self.chat_listbox.curselection()
        if not selected_indices: return
        
        chat_data = self.chat_listbox.chats_data[selected_indices[0]]
        room_id = chat_data['id']

        if room_id in self.opened_windows and self.opened_windows.get(room_id) and self.opened_windows[room_id].winfo_exists():
            self.opened_windows[room_id].lift()
        else:
            chat_window_obj = ChatRoomWindow(self.root, self.token, self.username, chat_data)
            self.opened_windows[room_id] = chat_window_obj.window

    def clear_frame(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = P2PClientApp(root)
    root.mainloop()