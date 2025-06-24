import datetime
import json
import queue
import socket
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
import threading
import time

from peer.chat import store_message
from peer.gui.utils import send_request


class ChatRoomWindow:
    def __init__(self, parent, token, username, chat_data, message_queues):
        self.parent = parent
        self.token = token
        self.username = username
        self.chat_data = chat_data
        self.room_id = chat_data['id']
        self.owner = chat_data['owner']
        self.members = []

        self.message_queues = message_queues
        self.msg_queue = queue.Queue()
        self.message_queues[self.room_id] = self.msg_queue

        self.window = tk.Toplevel(parent)
        self.window.title(f"Sala: {self.chat_data['name']} (Moderador: {self.owner})")
        self.window.geometry("500x600")
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.setup_menu()

        login_status_label = tk.Label(self.window, text=f"Você está logado como: {self.username}",
                                      font=("Arial", 9, "italic"), relief=tk.SUNKEN, anchor='w')
        login_status_label.pack(side=tk.TOP, fill='x', padx=10, pady=(0, 5))

        self.chat_box = scrolledtext.ScrolledText(self.window, state='disabled', wrap=tk.WORD, font=("Arial", 10))
        self.chat_box.pack(padx=10, pady=5, fill="both", expand=True)

        msg_frame = tk.Frame(self.window)
        msg_frame.pack(padx=10, pady=(5, 0), fill="x")

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
        window = tk.Toplevel(self.window)
        window.title("Adicionar Membro")
        window.geometry("300x400")

        tk.Label(window, text="Selecione um usuário ativo:", font=("Arial", 10)).pack(pady=5)

        user_listbox = tk.Listbox(window)
        user_listbox.pack(padx=10, pady=5, fill='both', expand=True)

        def refresh_users():
            res = send_request({"type": "list_active_peers", "token": self.token})
            active_peers = res.get("peers", [])

            current_members = [m['username'] for m in self.members]
            candidates = [u for u in active_peers if
                          u['username'] != self.username and u['username'] not in current_members]

            user_listbox.delete(0, tk.END)
            user_listbox.users_data = candidates

            for user in candidates:
                user_listbox.insert(tk.END, f"{user['username']} ({user.get('address', 'Offline')})")

        def confirm_add():
            selected = user_listbox.curselection()
            if not selected:
                return
            user = user_listbox.users_data[selected[0]]
            target_username = user['username']

            payload = {
                "type": "add_chat_member",
                "token": self.token,
                "room_id": self.room_id,
                "user_to_add": target_username
            }
            res = send_request(payload)

            if res.get('status') == 'success':
                messagebox.showinfo("Adicionar Membro", res.get("message"), parent=window)
                self.fetch_history_and_members()
                window.destroy()
            else:
                messagebox.showerror("Erro", res.get("message", "Erro ao adicionar membro."), parent=window)

        tk.Button(window, text="Atualizar", command=refresh_users).pack(pady=5)
        tk.Button(window, text="Adicionar", command=confirm_add).pack(pady=5)

        refresh_users()

    def remove_member(self):
        user_to_remove = simpledialog.askstring("Remover Membro", "Digite o nome do usuário a ser removido:",
                                                parent=self.window)
        if user_to_remove:
            if user_to_remove == self.username:
                messagebox.showwarning("Aviso", "Você não pode remover a si mesmo.", parent=self.window)
                return
            payload = {"type": "remove_chat_member", "token": self.token, "room_id": self.room_id,
                       "user_to_remove": user_to_remove}
            threading.Thread(target=self.send_remove_member_request, args=(payload,), daemon=True).start()

    def delete_room(self):
        if not messagebox.askyesno("Confirmar Remoção", "Tem certeza que deseja remover esta sala permanentemente?",
                                   parent=self.window):
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
        if res.get('status') != 'success': self.display_message(
            {"sender": "SISTEMA", "content": "Erro ao buscar lista de membros.", "timestamp": time.time()}); return
        self.members = res.get('members', [])
        moderator_info = next((m for m in self.members if m['username'] == self.owner), None)
        if not moderator_info or not moderator_info['address']: self.display_message(
            {"sender": "SISTEMA", "content": "Moderador está offline. Histórico indisponível.",
             "timestamp": time.time()}); return
        try:
            mod_host, mod_port = moderator_info['address'].split(':')
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((mod_host, int(mod_port)))
                payload = {"type": "get_chat_history", "room_id": self.room_id}
                s.sendall(json.dumps(payload).encode('utf-8'))
                res = json.loads(s.recv(8192).decode('utf-8'))
                if res['status'] == 'success':
                    for msg in res['history']: self.display_message(msg)
                self.display_message({"sender": "SISTEMA", "content": "Você entrou na sala.", "timestamp": time.time()})
        except Exception as e:
            self.display_message(
                {"sender": "SISTEMA", "content": f"Não foi possível obter o histórico: {e}", "timestamp": time.time()})

    def send_message_thread(self, event=None):
        threading.Thread(target=self.send_message, daemon=True).start()

    def send_message(self):
        message_text = self.msg_entry.get()
        if not message_text:
            return
        active_members = [m for m in self.members if m['address'] and m['username'] != self.username]
        if not active_members:
            self.display_message(
                {"sender": "SISTEMA", "content": f"Nenhum membro online", "timestamp": time.time()}
            )
        self.msg_entry.delete(0, tk.END)
        message_payload = {"sender": self.username, "content": message_text, "timestamp": time.time()}
        self.display_message(message_payload)
        store_message(self.username, self.room_id, message_payload)
        for member in active_members:
            threading.Thread(target=self._send_to_peer, args=(member, message_payload), daemon=True).start()

    def _send_to_peer(self, member, message_payload):
        try:
            host, port = member['address'].split(':')
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((host, int(port)))
                payload = {"type": "broadcast_message", "room_id": self.room_id, "message": message_payload}
                s.sendall(json.dumps(payload).encode('utf-8'))
        except Exception as e:
            print(f"Não foi possível enviar mensagem para {member['username']}: {e}")

    def display_message(self, msg_data):
        self.chat_box.config(state='normal')
        ts = datetime.datetime.fromtimestamp(msg_data['timestamp']).strftime('%H:%M:%S')
        sender = msg_data.get('sender', '???')
        content = msg_data.get('content', '')
        self.chat_box.insert(tk.END, f"[{ts}] {sender}: {content}\n")
        self.chat_box.config(state='disabled')
        self.chat_box.see(tk.END)

    def check_queue(self):
        try:
            while not self.msg_queue.empty(): self.display_message(self.msg_queue.get_nowait())
        finally:
            self.window.after(100, self.check_queue)

    def on_closing(self):
        if self.room_id in self.message_queues:
            del self.message_queues[self.room_id]
        self.window.destroy()