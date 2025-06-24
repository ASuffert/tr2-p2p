import sys
import tkinter as tk
from tkinter import simpledialog, messagebox, Listbox
import threading
import time

from peer.gui.chats import ChatRoomWindow
from peer.gui.files import FileManagerWindow
from peer.gui.utils import hash_password, send_request
from peer.p2p_server import start_p2p_server


class P2PClientApp:
    def __init__(self, root, auto_login_username = None, auto_login_password = None):
        self.root = root
        self.root.title("Cliente P2P - Login")
        self.root.geometry("300x160")
        self.token = None
        self.username = None
        self.p2p_port = None
        self.opened_windows = {}
        self.messages_queues = {}

        self.chat_listbox = None

        self.auto_login_username = auto_login_username
        self.auto_login_password = auto_login_password

        self.setup_login_frame()

    def setup_login_frame(self):
        self.clear_frame()
        self.root.geometry("300x160")
        self.root.title("Cliente P2P - Login")

        frame = tk.Frame(self.root)
        frame.pack(padx=10, pady=10, fill='both', expand=True)

        tk.Label(frame, text="Usuário:").grid(row=0, column=0, sticky="w", pady=2)
        self.user_entry = tk.Entry(frame)
        self.user_entry.grid(row=0, column=1, pady=2, sticky="ew")

        tk.Label(frame, text="Senha:").grid(row=1, column=0, sticky="w", pady=2)
        self.pass_entry = tk.Entry(frame, show="*")
        self.pass_entry.grid(row=1, column=1, pady=2, sticky="ew")

        frame.grid_columnconfigure(1, weight=1)

        button_frame = tk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        login_btn = tk.Button(button_frame, text="Login", command=self.attempt_login)
        login_btn.pack(side='left', expand=True, padx=5)

        register_btn = tk.Button(button_frame, text="Registrar", command=self.attempt_register)
        register_btn.pack(side='right', expand=True, padx=5)

        self.root.bind('<Return>', lambda event: self.attempt_login())

        if self.auto_login_username and self.auto_login_password:
            self.user_entry.insert(0, self.auto_login_username)
            self.pass_entry.insert(0, self.auto_login_password)
            self.root.after(100, self.attempt_login)

    def attempt_register(self):
        user = self.user_entry.get()
        pwd = self.pass_entry.get()
        if not user or not pwd:
            messagebox.showerror("Erro de Registro", "Usuário e senha são obrigatórios.")
            return

        payload = {"type": "register", "username": user, "password": hash_password(pwd)}
        res = send_request(payload)

        if res.get("status") == "success":
            messagebox.showinfo("Registro", res.get("message", "Usuário registrado com sucesso!"))
        else:
            messagebox.showerror("Erro de Registro", res.get("message", "Erro desconhecido."))

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
        self.p2p_port = start_p2p_server(self.username, self.messages_queues)
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

        login_status_label = tk.Label(chat_lobby, text=f"Você está logado como: {self.username}",
                                      font=("Arial", 9, "italic"), relief=tk.SUNKEN, anchor='w')
        login_status_label.pack(side=tk.TOP, fill='x', padx=10, pady=(5, 0))

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

        if room_id in self.opened_windows and self.opened_windows.get(room_id) and self.opened_windows[
            room_id].winfo_exists():
            self.opened_windows[room_id].lift()
        else:
            chat_window_obj = ChatRoomWindow(self.root, self.token, self.username, chat_data, self.messages_queues)
            self.opened_windows[room_id] = chat_window_obj.window

    def clear_frame(self):
        for widget in self.root.winfo_children():
            widget.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    if len(sys.argv) >= 2:
        peer = sys.argv[1]
        app = P2PClientApp(root, peer, "test")
    else:
        app = P2PClientApp(root)
    root.mainloop()