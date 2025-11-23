import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
import json
import time

class ChatClient:
    def __init__(self):
        self.sock = None
        self.connected = False
        self.username = None
        self.buffer = ""

        # Single root and view frames
        self.root = tk.Tk()
        self.root.title("Chat Client")
        self.connect_frame = None
        self.auth_frame = None
        self.chat_frame = None

        # Widgets shared
        self.text_area = None
        self.entry = None

        # Build views
        self.build_connect_view()
        self.root.protocol("WM_DELETE_WINDOW", self.close_all)
        self.root.mainloop()

    # ---------- Views ----------
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

        bottom = tk.Frame(self.chat_frame)
        bottom.pack(fill="x", pady=6)
        self.entry = tk.Entry(bottom)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.send_message)
        tk.Button(bottom, text="Send", width=10, command=self.send_message).pack(side="right", padx=4)

    # ---------- Connection ----------
    def connect_server(self):
        host = self.host_entry.get().strip()
        port_text = self.port_entry.get().strip()
        try:
            port = int(port_text)
        except ValueError:
            messagebox.showerror("Error", "Port must be a number.")
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.connected = True
            messagebox.showinfo("Info", f"Connected to {host}:{port}")
            self.build_auth_view()
            threading.Thread(target=self.read_loop, daemon=True).start()
            threading.Thread(target=self.ping_loop, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {e}")

    # ---------- Networking ----------
    def send_json(self, obj: dict):
        try:
            data = (json.dumps(obj) + "\n").encode("utf-8")
            self.sock.sendall(data)
        except Exception:
            self.on_disconnect()

    def read_loop(self):
        try:
            while self.connected:
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
        while self.connected:
            try:
                self.send_json({"type": "ping"})
            except Exception:
                break
            time.sleep(2)

    # ---------- Handlers ----------
    def handle_server_message(self, line: str):
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            return
        mtype = msg.get("type")

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

        if mtype == "pong":
            return

        if mtype == "chat":
            from_user = msg.get("from", "Unknown")
            text = msg.get("message", "")
            self.append_text(f"{from_user}: {text}")
            return

        if mtype == "error":
            messagebox.showerror("Error", msg.get("message", "Unknown error"))
            return

    # ---------- Actions ----------
    def login(self):
        u = self.username_entry.get().strip()
        p = self.password_entry.get()
        if not u or not p:
            messagebox.showerror("Error", "Username and password are required.")
            return
        self.send_json({"type": "login", "username": u, "password": p})

    def register(self):
        u = self.username_entry.get().strip()
        p = self.password_entry.get()
        if not u or not p:
            messagebox.showerror("Error", "Username and password are required.")
            return
        self.send_json({"type": "register", "username": u, "password": p})

    def reset_password(self):
        win = tk.Toplevel(self.root)
        win.title("Reset password with recovery code")

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
        self.send_json({"type": "chat", "message": text})

    # ---------- UI helpers ----------
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
        tk.Label(win, text="Save these codes securely. Each code can be used once.").pack(pady=4)
        txt = scrolledtext.ScrolledText(win, width=60, height=15)
        txt.pack(padx=8, pady=8)
        if isinstance(codes, list):
            txt.insert("end", "\n".join(codes))
        else:
            txt.insert("end", str(codes))
        txt.config(state="disabled")
        tk.Button(win, text="Close", command=win.destroy).pack(pady=4)

    # ---------- Disconnect handling ----------
    def on_disconnect(self):
        if not self.connected:
            return
        self.connected = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.sock = None
        self.show_reconnect_dialog()

    def show_reconnect_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Connection lost")
        dlg.grab_set()  # modal
        tk.Label(dlg, text="The connection to the server was lost.\nDo you want to reconnect?").pack(padx=12, pady=12)
        btns = tk.Frame(dlg); btns.pack(pady=8)
        def do_reconnect():
            dlg.destroy()
            # back to connect view
            self.build_connect_view()
        def do_close():
            dlg.destroy()
            self.close_all()
        tk.Button(btns, text="Reconnect", command=do_reconnect, width=12).grid(row=0, column=0, padx=6)
        tk.Button(btns, text="Close", command=do_close, width=12).grid(row=0, column=1, padx=6)

    def close_all(self):
        self.connected = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.root.destroy()

if __name__ == "__main__":
    ChatClient()
