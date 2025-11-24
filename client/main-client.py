import tkinter as tk
from tkinter import messagebox
import threading, json, os

from ui_helpers import make_entry, append_text, show_codes_window
from network import connect_server, send_json, disconnect_socket
from auth import login, register, reset_password, delete_account
from contacts import open_contacts_window, show_contacts_list, request_my_code, request_list_contacts
from history import load_local_history, save_local_history

class ChatClient:
    def __init__(self):
        self.sock, self.connected, self.buffer, self.username = None, False, "", None
        self.stop_threads = threading.Event()
        self.root = tk.Tk(); self.root.title("Chat Client")
        self.build_connect_view()
        self.root.protocol("WM_DELETE_WINDOW", self.close_all)
        self.root.mainloop()

    def clear_root(self): [c.destroy() for c in self.root.winfo_children()]

    def build_connect_view(self):
        self.clear_root()
        f = tk.Frame(self.root); f.pack(padx=12, pady=12, fill="x")
        self.host_entry = make_entry(f, "Server IP or domain"); self.host_entry.insert(0, "127.0.0.1")
        self.port_entry = make_entry(f, "Port"); self.port_entry.insert(0, "5000")
        tk.Button(f, text="Connect", command=lambda: connect_server(self)).pack(pady=8)

    def build_auth_view(self):
        self.clear_root()
        f = tk.Frame(self.root); f.pack(padx=12, pady=12, fill="x")
        self.username_entry = make_entry(f, "Username")
        self.password_entry = make_entry(f, "Password", show="*")
        row = tk.Frame(f); row.pack(pady=8, fill="x")
        tk.Button(row, text="Login", width=12, command=lambda: login(self)).grid(row=0, column=0, padx=4)
        tk.Button(row, text="Register", width=12, command=lambda: register(self)).grid(row=0, column=1, padx=4)
        tk.Button(row, text="Forgot password", width=16, command=lambda: reset_password(self)).grid(row=0, column=2, padx=4)
        tk.Button(row, text="Delete account", width=16, command=lambda: delete_account(self)).grid(row=0, column=3, padx=4)

    def build_chat_view(self):
        self.clear_root()
        f = tk.Frame(self.root); f.pack(padx=10, pady=10, fill="both", expand=True)
        self.text_area = tk.Text(f, state="disabled", width=80, height=24)
        self.text_area.pack(fill="both", expand=True)
        ctrl = tk.Frame(f); ctrl.pack(fill="x", pady=4)
        tk.Button(ctrl, text="Contacts", command=lambda: open_contacts_window(self)).pack(side="left", padx=4)
        tk.Button(ctrl, text="Get my code", command=lambda: request_my_code(self)).pack(side="left", padx=4)
        tk.Button(ctrl, text="Refresh contacts", command=lambda: request_list_contacts(self)).pack(side="left", padx=4)
        bottom = tk.Frame(f); bottom.pack(fill="x", pady=6)
        self.entry = tk.Entry(bottom); self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.send_message)
        tk.Button(bottom, text="Send", command=self.send_message).pack(side="right", padx=4)
        os.makedirs("chat_history", exist_ok=True)
        if self.username: load_local_history(self)

    def handle_server_message(self, line):
        try: msg = json.loads(line)
        except: return
        mtype = msg.get("type")
        handlers = {
            "pong": lambda m: None,
            "register_ok": lambda m: show_codes_window(self.root, m.get("recovery_codes", [])),
            "login_ok": lambda m: (setattr(self, "username", self.username_entry.get().strip()),
                                   self.build_chat_view(),
                                   append_text(self.text_area, "[System] Login successful.")),
            "reset_ok": lambda m: messagebox.showinfo("Info", m.get("message", "OK")),
            "delete_ok": lambda m: messagebox.showinfo("Info", m.get("message", "OK")),
            "chat": lambda m: self._handle_chat(m),
            "private_chat": lambda m: self._handle_private_chat(m),
            "your_code": lambda m: messagebox.showinfo("Your code", f"{m.get('code')} valid {m.get('ttl',60)}s"),
            "add_contact_ok": lambda m: messagebox.showinfo("Contacts", m.get("message")),
            "remove_contact_ok": lambda m: messagebox.showinfo("Contacts", m.get("message")),
            "list_contacts_ok": lambda m: show_contacts_list(self, m.get("contacts", [])),
            "online_status": lambda m: messagebox.showinfo("Online status", f"{m.get('user')} is {'online' if m.get('online') else 'offline'}."),
            "error": lambda m: messagebox.showerror("Error", m.get("message", "Unknown error"))
        }
        if mtype in handlers: handlers[mtype](msg)

    def _handle_chat(self, m):
        u, text = m.get("from", "Unknown"), m.get("message", "")
        line = f"{u} (you): {text}" if u == self.username else f"{u}: {text}"
        append_text(self.text_area, line)
        save_local_history(self, line)

    def _handle_private_chat(self, m):
        if "from" in m:
            line = f"[Private] {m['from']} -> you: {m['message']}"
        else:
            line = f"[Private] you -> {m['to']}: {m['message']}"
        append_text(self.text_area, line)
        save_local_history(self, line)

    def send_message(self, event=None):
        text = self.entry.get().strip(); self.entry.delete(0, tk.END)
        if text: send_json(self, {"type": "chat", "message": text})

    def on_disconnect(self):
        disconnect_socket(self); self.stop_threads.set()
        messagebox.showwarning("Disconnected", "Lost connection to server.")
        self.build_connect_view()

    def close_all(self):
        self.stop_threads.set(); disconnect_socket(self); self.root.destroy()

if __name__ == "__main__":
    ChatClient()
