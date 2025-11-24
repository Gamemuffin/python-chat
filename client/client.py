import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog
import json
import time
import os


class ChatClient:
    def __init__(self):
        self.sock = None
        self.connected = False
        self.buffer = ""
        self.username = None

        self.root = tk.Tk()
        self.root.title("Chat Client")
        self.connect_frame = None
        self.auth_frame = None
        self.chat_frame = None

        self.host_entry = None
        self.port_entry = None
        self.username_entry = None
        self.password_entry = None
        self.text_area = None
        self.entry = None

        self.reader_thread = None
        self.ping_thread = None
        self.stop_threads = threading.Event()

        self.build_connect_view()
        self.root.protocol("WM_DELETE_WINDOW", self.close_all)
        self.root.mainloop()

    def clear_root(self):
        for child in self.root.winfo_children():
            child.destroy()

    # ============================
    # CONNECT VIEW
    # ============================
    def build_connect_view(self):
        self.clear_root()
        self.connect_frame = tk.Frame(self.root)
        self.connect_frame.pack(padx=12, pady=12, fill="x")

        tk.Label(self.connect_frame, text="Server IP or domain").pack(pady=4)
        self.host_entry = tk.Entry(self.connect_frame)
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.pack(pady=4, fill="x")

        tk.Label(self.connect_frame, text="Port").pack(pady=4)
        self.port_entry = tk.Entry(self.connect_frame)
        self.port_entry.insert(0, "5000")
        self.port_entry.pack(pady=4, fill="x")

        tk.Button(self.connect_frame, text="Connect", command=self.connect_server).pack(pady=8)

    # ============================
    # AUTH VIEW
    # ============================
    def build_auth_view(self):
        self.clear_root()
        self.auth_frame = tk.Frame(self.root)
        self.auth_frame.pack(padx=12, pady=12, fill="x")

        tk.Label(self.auth_frame, text="Username").pack(pady=4)
        self.username_entry = tk.Entry(self.auth_frame)
        self.username_entry.pack(pady=4, fill="x")

        tk.Label(self.auth_frame, text="Password").pack(pady=4)
        self.password_entry = tk.Entry(self.auth_frame, show="*")
        self.password_entry.pack(pady=4, fill="x")

        row = tk.Frame(self.auth_frame)
        row.pack(pady=8, fill="x")
        tk.Button(row, text="Login", width=12, command=self.login).grid(row=0, column=0, padx=4)
        tk.Button(row, text="Register", width=12, command=self.register).grid(row=0, column=1, padx=4)
        tk.Button(row, text="Forgot password", width=16, command=self.reset_password).grid(row=0, column=2, padx=4)
        tk.Button(row, text="Delete account", width=16, command=self.delete_account).grid(row=0, column=3, padx=4)

    # ============================
    # CHAT VIEW
    # ============================
    def build_chat_view(self):
        self.clear_root()
        self.chat_frame = tk.Frame(self.root)
        self.chat_frame.pack(padx=10, pady=10, fill="both", expand=True)

        top = tk.Frame(self.chat_frame)
        top.pack(fill="both", expand=True)
        self.text_area = tk.Text(top, state="disabled", width=80, height=24)
        self.text_area.pack(fill="both", expand=True)

        ctrl = tk.Frame(self.chat_frame)
        ctrl.pack(fill="x", pady=4)
        tk.Button(ctrl, text="Contacts", width=12, command=self.open_contacts_window).pack(side="left", padx=4)
        tk.Button(ctrl, text="Get my code", width=12, command=self.request_my_code).pack(side="left", padx=4)
        tk.Button(ctrl, text="Refresh contacts", width=15, command=self.request_list_contacts).pack(side="left", padx=4)

        bottom = tk.Frame(self.chat_frame)
        bottom.pack(fill="x", pady=6)
        self.entry = tk.Entry(bottom)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.send_message)
        tk.Button(bottom, text="Send", width=10, command=self.send_message).pack(side="right", padx=4)

        os.makedirs("chat_history", exist_ok=True)
        if self.username:
            self.load_local_history()

    # ============================
    # NETWORK
    # ============================
    def connect_server(self):
        host = self.host_entry.get().strip()
        port_str = self.port_entry.get().strip()
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Error", "Port must be a number.")
            return

        self.disconnect_socket()
        self.stop_threads.clear()

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.sock.settimeout(None)
            self.connected = True
            messagebox.showinfo("Info", f"Connected to {host}:{port}")
        except Exception as e:
            self.connected = False
            self.sock = None
            messagebox.showerror("Error", f"Connection failed: {e}")
            return

        self.build_auth_view()
        self.reader_thread = threading.Thread(target=self.read_loop, daemon=True)
        self.reader_thread.start()
        self.ping_thread = threading.Thread(target=self.ping_loop, daemon=True)
        self.ping_thread.start()

    def send_json(self, obj: dict):
        if not self.connected or not self.sock:
            return
        try:
            data = (json.dumps(obj) + "\n").encode("utf-8")
            self.sock.sendall(data)
        except Exception:
            self.root.after(0, self.on_disconnect)

    def read_loop(self):
        try:
            while self.connected and not self.stop_threads.is_set():
                data = self.sock.recv(4096)
                if not data:
                    break
                self.buffer += data.decode("utf-8", errors="ignore")
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    if not line.strip():
                        continue
                    self.root.after(0, self.handle_server_message, line)
        except Exception:
            pass
        self.root.after(0, self.on_disconnect)

    def ping_loop(self):
        while self.connected and not self.stop_threads.is_set():
            self.send_json({"type": "ping"})
            for _ in range(20):
                if self.stop_threads.is_set():
                    return
                time.sleep(0.1)

    def disconnect_socket(self):
        try:
            if self.sock:
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                self.sock.close()
        except:
            pass
        self.sock = None
        self.connected = False

    # ============================
    # SERVER MESSAGE HANDLER
    # ============================
    def handle_server_message(self, line: str):
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            return

        mtype = msg.get("type")

        if mtype == "pong":
            return

        if mtype == "register_ok":
            self.show_codes_window(msg.get("recovery_codes", []))
            return

        if mtype == "login_ok":
            self.username = self.username_entry.get().strip()
            self.build_chat_view()
            self.append_text("[System] Login successful.")
            return

        if mtype in ("reset_ok", "delete_ok"):
            messagebox.showinfo("Info", msg.get("message", "OK"))
            return

        # --- BROADCAST CHAT MESSAGE ---
        if mtype == "chat":
            from_user = msg.get("from", "Unknown")
            text = msg.get("message", "")

            # ★ 修复了重复显示，并显示 (you)
            if from_user == self.username:
                line = f"{from_user} (you): {text}"
            else:
                line = f"{from_user}: {text}"

            self.append_text(line)
            self.save_local_history(line)
            return

        # --- CONTACT CODE ---
        if mtype == "your_code":
            code = msg.get("code")
            ttl = msg.get("ttl", 60)
            messagebox.showinfo("Your code", f"Your current code: {code}\nValid for {ttl} seconds.")
            return

        # --- CONTACTS ---
        if mtype == "add_contact_ok":
            messagebox.showinfo("Contacts", msg.get("message"))
            return

        if mtype == "remove_contact_ok":
            messagebox.showinfo("Contacts", msg.get("message"))
            return

        if mtype == "list_contacts_ok":
            self.show_contacts_list(msg.get("contacts", []))
            return

        if mtype == "online_status":
            user = msg.get("user")
            online = msg.get("online", False)
            messagebox.showinfo("Online status", f"{user} is {'online' if online else 'offline'}.")
            return

        if mtype == "error":
            messagebox.showerror("Error", msg.get("message", "Unknown error"))
            return

    # ============================
    # AUTH COMMANDS
    # ============================
    def login(self):
        u = self.username_entry.get().strip()
        p = self.password_entry.get()
        if not u or not p:
            messagebox.showerror("Error", "Username and password required.")
            return
        self.send_json({"type": "login", "username": u, "password": p})

    def register(self):
        u = self.username_entry.get().strip()
        p = self.password_entry.get()
        if not u or not p:
            messagebox.showerror("Error", "Username and password required.")
            return
        self.send_json({"type": "register", "username": u, "password": p})

    def reset_password(self):
        win = tk.Toplevel(self.root)
        win.title("Reset Password")
        win.grab_set()

        tk.Label(win, text="Username").pack()
        u_entry = tk.Entry(win); u_entry.pack()

        tk.Label(win, text="Recovery code").pack()
        c_entry = tk.Entry(win); c_entry.pack()

        tk.Label(win, text="New password").pack()
        p_entry = tk.Entry(win, show="*"); p_entry.pack()

        def do():
            u = u_entry.get().strip()
            c = c_entry.get().strip()
            p = p_entry.get()
            if not u or not c or not p:
                messagebox.showerror("Error", "All fields required.")
                return
            self.send_json({"type": "reset_password", "username": u,
                            "recovery_code": c, "new_password": p})
            win.destroy()

        tk.Button(win, text="Confirm", command=do).pack()

    def delete_account(self):
        win = tk.Toplevel(self.root)
        win.title("Delete Account")
        win.grab_set()

        tk.Label(win, text="Username").pack()
        u_entry = tk.Entry(win); u_entry.pack()

        tk.Label(win, text="Recovery code").pack()
        c_entry = tk.Entry(win); c_entry.pack()

        def do():
            u = u_entry.get().strip()
            c = c_entry.get().strip()
            if not u or not c:
                messagebox.showerror("Error", "Required fields empty.")
                return
            self.send_json({"type": "delete_account", "username": u,
                            "recovery_code": c})
            win.destroy()

        tk.Button(win, text="Confirm", command=do).pack()

    # ============================
    # SEND CHAT MESSAGE
    # ============================
    def send_message(self, event=None):
        text = self.entry.get().strip()
        self.entry.delete(0, tk.END)
        if not text:
            return

        # ★ 不要本地 echo，由服务器广播回来统一显示
        self.send_json({"type": "chat", "message": text})

    # ============================
    # UI HELPERS
    # ============================
    def append_text(self, line: str):
        self.text_area.config(state="normal")
        self.text_area.insert("end", line + "\n")
        self.text_area.config(state="disabled")
        self.text_area.see("end")

    # ============================
    # CONTACTS WINDOW
    # ============================
    def open_contacts_window(self):
        win = tk.Toplevel(self.root)
        win.title("Contacts")
        win.geometry("400x300")
        win.grab_set()

        listbox = tk.Listbox(win)
        listbox.pack(fill="both", expand=True, padx=6, pady=6)

        def add_contact():
            code = simpledialog.askstring("Add contact", "Enter 6-digit code:", parent=win)
            if code:
                self.send_json({"type": "add_contact", "code": code})

        def remove_contact():
            sel = listbox.curselection()
            if not sel:
                return
            target = listbox.get(sel[0]).split(" ")[0]
            self.send_json({"type": "remove_contact", "target": target})

        def query_online():
            sel = listbox.curselection()
            if not sel:
                return
            target = listbox.get(sel[0]).split(" ")[0]
            self.send_json({"type": "query_online", "user": target})

        def refresh():
            self.request_list_contacts()

        btn_frame = tk.Frame(win)
        btn_frame.pack(fill="x")

        tk.Button(btn_frame, text="Add", command=add_contact).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Remove", command=remove_contact).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Is online?", command=query_online).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Refresh", command=refresh).pack(side="right", padx=4)

        self._contacts_listbox = listbox
        self.request_list_contacts()

    def show_contacts_list(self, contacts):
        if not hasattr(self, "_contacts_listbox"):
            return
        lb = self._contacts_listbox
        lb.delete(0, "end")
        for item in contacts:
            uname = item.get("username")
            online = item.get("online", False)
            lb.insert("end", f"{uname} {'(online)' if online else '(offline)'}")

    # ============================
    # CONTACT COMMANDS
    # ============================
    def request_my_code(self):
        self.send_json({"type": "get_code"})

    def request_list_contacts(self):
        self.send_json({"type": "list_contacts"})

    # ============================
    # LOCAL CHAT HISTORY
    # ============================
    def save_local_history(self, line: str):
        if not self.username:
            return
        path = os.path.join("chat_history", f"{self.username}.txt")
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"{int(time.time())} {line}\n")
        except:
            pass

    def load_local_history(self):
        path = os.path.join("chat_history", f"{self.username}.txt")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(" ", 1)
                    if len(parts) == 2:
                        _, content = parts
                        self.append_text(content)
        except:
            pass

    # ============================
    # CLEANUP
    # ============================
    def on_disconnect(self):
        if not self.connected:
            return
        self.connected = False
        self.stop_threads.set()
        self.disconnect_socket()
        self.show_reconnect_dialog()

    def show_reconnect_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Disconnected")
        dlg.grab_set()
        tk.Label(dlg, text="Lost connection.\nReconnect?").pack(pady=12)
        btns = tk.Frame(dlg)
        btns.pack()

        tk.Button(btns, text="Reconnect", command=lambda: (dlg.destroy(), self.build_connect_view())).pack(side="left")
        tk.Button(btns, text="Close", command=lambda: (dlg.destroy(), self.close_all())).pack(side="left")

    def close_all(self):
        self.stop_threads.set()
        self.disconnect_socket()
        try:
            self.root.destroy()
        except:
            pass


if __name__ == "__main__":
    ChatClient()
