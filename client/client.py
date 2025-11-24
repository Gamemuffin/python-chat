# client.py
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

    def build_chat_view(self):
        self.clear_root()
        self.chat_frame = tk.Frame(self.root)
        self.chat_frame.pack(padx=10, pady=10, fill="both", expand=True)

        top = tk.Frame(self.chat_frame)
        top.pack(fill="both", expand=True)
        self.text_area = tk.Text(top, state="disabled", width=80, height=24)
        self.text_area.pack(fill="both", expand=True)

        # left control buttons: contacts / get my code / refresh contacts
        ctrl = tk.Frame(self.chat_frame)
        ctrl.pack(fill="x", pady=4)
        tk.Button(ctrl, text="Contacts", width=12, command=self.open_contacts_window).pack(side="left", padx=4)
        tk.Button(ctrl, text="Get my code", width=12, command=self.request_my_code).pack(side="left", padx=4)
        tk.Button(ctrl, text="Refresh contacts", width=14, command=self.request_list_contacts).pack(side="left", padx=4)

        bottom = tk.Frame(self.chat_frame)
        bottom.pack(fill="x", pady=6)
        self.entry = tk.Entry(bottom)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.send_message)
        tk.Button(bottom, text="Send", width=10, command=self.send_message).pack(side="right", padx=4)

        # ensure local chat history dir exists
        os.makedirs("chat_history", exist_ok=True)
        # load local history if exists
        if self.username:
            self.load_local_history()

    def connect_server(self):
        host = (self.host_entry.get() if self.host_entry else "").strip()
        port_str = (self.port_entry.get() if self.port_entry else "").strip()
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
                if not self.connected or self.stop_threads.is_set():
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
        except Exception:
            pass
        self.sock = None
        self.connected = False

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
            self.username = (self.username_entry.get() if self.username_entry else "").strip()
            self.build_chat_view()
            self.append_text("[System] Login successful.")
            return

        if mtype == "reset_ok" or mtype == "delete_ok":
            messagebox.showinfo("Info", msg.get("message", "OK"))
            return

        if mtype == "chat":
            from_user = msg.get("from", "Unknown")
            text = msg.get("message", "")
            line = f"{from_user}: {text}"
            self.append_text(line)
            # save to local history (for current user)
            self.save_local_history(line)
            return

        if mtype == "your_code":
            code = msg.get("code")
            ttl = msg.get("ttl", 60)
            messagebox.showinfo("Your code", f"Your current 6-digit code: {code}\nValid for {ttl} seconds.")
            return

        if mtype == "add_contact_ok":
            contact = msg.get("contact")
            messagebox.showinfo("Contacts", f"Added contact: {contact}")
            return

        if mtype == "remove_contact_ok":
            contact = msg.get("contact")
            messagebox.showinfo("Contacts", f"Removed contact: {contact}")
            return

        if mtype == "list_contacts_ok":
            contacts = msg.get("contacts", [])
            # show contacts window if open
            self.show_contacts_list(contacts)
            return

        if mtype == "online_status":
            user = msg.get("user")
            online = msg.get("online", False)
            messagebox.showinfo("Online status", f"{user} is {'online' if online else 'offline'}.")
            return

        if mtype == "error":
            messagebox.showerror("Error", msg.get("message", "Unknown error"))
            return

    def login(self):
        u = (self.username_entry.get() if self.username_entry else "").strip()
        p = (self.password_entry.get() if self.password_entry else "")
        if not u or not p:
            messagebox.showerror("Error", "Username and password are required.")
            return
        self.send_json({"type": "login", "username": u, "password": p})

    def register(self):
        u = (self.username_entry.get() if self.username_entry else "").strip()
        p = (self.password_entry.get() if self.password_entry else "")
        if not u or not p:
            messagebox.showerror("Error", "Username and password are required.")
            return
        self.send_json({"type": "register", "username": u, "password": p})

    def reset_password(self):
        win = tk.Toplevel(self.root)
        win.title("Reset password with recovery code")
        win.grab_set()

        tk.Label(win, text="Username").pack(pady=4)
        u_entry = tk.Entry(win); u_entry.pack(pady=4, fill="x")

        tk.Label(win, text="Recovery code").pack(pady=4)
        c_entry = tk.Entry(win); c_entry.pack(pady=4, fill="x")

        tk.Label(win, text="New password").pack(pady=4)
        p_entry = tk.Entry(win, show="*"); p_entry.pack(pady=4, fill="x")

        def do_reset():
            u = u_entry.get().strip()
            c = c_entry.get().strip()
            p = p_entry.get()
            if not u or not c or not p:
                messagebox.showerror("Error", "All fields are required.")
                return
            self.send_json({"type": "reset_password", "username": u, "recovery_code": c, "new_password": p})
            win.destroy()

        tk.Button(win, text="Confirm reset", command=do_reset).pack(pady=8)

    def delete_account(self):
        win = tk.Toplevel(self.root)
        win.title("Delete account with recovery code")
        win.grab_set()

        tk.Label(win, text="Username").pack(pady=4)
        u_entry = tk.Entry(win); u_entry.pack(pady=4, fill="x")

        tk.Label(win, text="Recovery code").pack(pady=4)
        c_entry = tk.Entry(win); c_entry.pack(pady=4, fill="x")

        def do_delete():
            u = u_entry.get().strip()
            c = c_entry.get().strip()
            if not u or not c:
                messagebox.showerror("Error", "Username and recovery code are required.")
                return
            self.send_json({"type": "delete_account", "username": u, "recovery_code": c})
            win.destroy()

        tk.Button(win, text="Confirm delete", command=do_delete).pack(pady=8)

    def send_message(self, event=None):
        if not self.entry:
            return
        text = self.entry.get()
        self.entry.delete(0, tk.END)
        if not text.strip():
            return
        self.append_text(f"You: {text}")
        self.save_local_history(f"You: {text}")
        self.send_json({"type": "chat", "message": text})

    def append_text(self, line: str):
        if not self.text_area:
            return
        self.text_area.config(state="normal")
        self.text_area.insert("end", line + "\n")
        self.text_area.config(state="disabled")
        self.text_area.see("end")

    def show_codes_window(self, codes):
        win = tk.Toplevel(self.root)
        win.title("Your recovery codes")
        win.grab_set()
        tk.Label(win, text="Save these codes securely. Each code can be used (reusable).").pack(pady=4)
        txt = scrolledtext.ScrolledText(win, width=60, height=15)
        txt.pack(padx=8, pady=8)
        if isinstance(codes, list):
            txt.insert("end", "\n".join(codes))
        else:
            txt.insert("end", str(codes))
        txt.config(state="disabled")
        tk.Button(win, text="Close", command=win.destroy).pack(pady=4)

    def on_disconnect(self):
        if not self.connected:
            return
        self.connected = False
        self.stop_threads.set()
        self.disconnect_socket()
        self.show_reconnect_dialog()

    def show_reconnect_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Connection lost")
        dlg.grab_set()
        tk.Label(dlg, text="The connection to the server was lost.\nDo you want to reconnect?").pack(padx=12, pady=12)
        btns = tk.Frame(dlg); btns.pack(pady=8)

        def do_reconnect():
            dlg.destroy()
            self.build_connect_view()

        def do_close():
            dlg.destroy()
            self.close_all()

        tk.Button(btns, text="Reconnect", command=do_reconnect, width=12).grid(row=0, column=0, padx=6)
        tk.Button(btns, text="Close", command=do_close, width=12).grid(row=0, column=1, padx=6)

    def close_all(self):
        self.stop_threads.set()
        self.disconnect_socket()
        try:
            self.root.destroy()
        except Exception:
            pass

    # -------------------------
    # Contacts UI & actions
    # -------------------------
    def open_contacts_window(self):
        win = tk.Toplevel(self.root)
        win.title("Contacts")
        win.grab_set()
        win.geometry("400x300")

        listbox = tk.Listbox(win)
        listbox.pack(fill="both", expand=True, padx=6, pady=6)

        def refresh():
            self.request_list_contacts()

        def on_add():
            code = simpledialog.askstring("Add contact", "Enter 6-digit contact code:", parent=win)
            if not code:
                return
            self.send_json({"type": "add_contact", "code": code})

        def on_remove():
            sel = listbox.curselection()
            if not sel:
                messagebox.showerror("Error", "Select a contact to remove.")
                return
            target = listbox.get(sel[0]).split(" ")[0]  # format "username (online)" maybe
            self.send_json({"type": "remove_contact", "target": target})

        def on_query():
            sel = listbox.curselection()
            if not sel:
                messagebox.showerror("Error", "Select a contact to query.")
                return
            target = listbox.get(sel[0]).split(" ")[0]
            self.send_json({"type": "query_online", "user": target})

        btns = tk.Frame(win)
        btns.pack(fill="x", pady=4)
        tk.Button(btns, text="Add by code", command=on_add).pack(side="left", padx=4)
        tk.Button(btns, text="Remove contact", command=on_remove).pack(side="left", padx=4)
        tk.Button(btns, text="Is online?", command=on_query).pack(side="left", padx=4)
        tk.Button(btns, text="Refresh", command=refresh).pack(side="right", padx=4)

        # store listbox for update
        self._contacts_listbox = listbox
        # trigger initial load
        self.request_list_contacts()

    def show_contacts_list(self, contacts):
        # contacts: list of {"username": u, "online": True/False}
        if hasattr(self, "_contacts_listbox") and self._contacts_listbox:
            lb = self._contacts_listbox
            lb.delete(0, "end")
            for c in contacts:
                uname = c.get("username")
                online = c.get("online", False)
                lb.insert("end", f"{uname} {'(online)' if online else '(offline)'}")

    def request_my_code(self):
        self.send_json({"type": "get_code"})

    def request_list_contacts(self):
        self.send_json({"type": "list_contacts"})

    # -------------------------
    # Local chat history
    # -------------------------
    def save_local_history(self, line: str):
        if not self.username:
            return
        path = os.path.join("chat_history", f"{self.username}.txt")
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"{int(time.time())} {line}\n")
        except Exception:
            pass

    def load_local_history(self):
        path = os.path.join("chat_history", f"{self.username}.txt")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    # skip leading timestamp
                    parts = line.strip().split(" ", 1)
                    if len(parts) == 2:
                        _, content = parts
                    else:
                        content = line.strip()
                    self.append_text(content)
        except Exception:
            pass

if __name__ == "__main__":
    ChatClient()
