import socket
import threading
import tkinter as tk
from tkinter import messagebox

class ChatClient:
    def __init__(self):
        # 连接窗口
        self.conn_root = tk.Tk()
        self.conn_root.title("Connect to server")

        tk.Label(self.conn_root, text="Server IP address").pack(pady=5)
        self.host_entry = tk.Entry(self.conn_root)
        self.host_entry.insert(0, "127.0.0.1")  # 默认值
        self.host_entry.pack(pady=5)

        tk.Label(self.conn_root, text="Port").pack(pady=5)
        self.port_entry = tk.Entry(self.conn_root)
        self.port_entry.insert(0, "5000")  # 默认值
        self.port_entry.pack(pady=5)

        tk.Button(self.conn_root, text="Connect", command=self.connect_server).pack(pady=10)

        self.conn_root.mainloop()

    def connect_server(self):
        host = self.host_entry.get()
        port = int(self.port_entry.get())
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            messagebox.showinfo("tip", f"Connect successful {host}:{port}")
            self.conn_root.destroy()
            self.show_login_window()
        except Exception as e:
            messagebox.showerror("Error", f"Connect failed: {e}")

    def show_login_window(self):
        # 登录/注册窗口
        self.login_root = tk.Tk()
        self.login_root.title("Sign up or Sign in")

        tk.Label(self.login_root, text="Username").pack(pady=5)
        self.username_entry = tk.Entry(self.login_root)
        self.username_entry.pack(pady=5)

        tk.Label(self.login_root, text="Password").pack(pady=5)
        self.password_entry = tk.Entry(self.login_root, show="*")
        self.password_entry.pack(pady=5)

        tk.Button(self.login_root, text="Sign in", command=self.login).pack(pady=5)
        tk.Button(self.login_root, text="Sign up", command=self.register).pack(pady=5)

        self.login_root.mainloop()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        self.sock.send(f"LOGIN {username} {password}".encode("utf-8"))
        result = self.sock.recv(4096).decode("utf-8")
        if "Successful" in result:
            messagebox.showinfo("Tip", result)
            self.login_root.destroy()
            self.start_chat(username)
        else:
            messagebox.showerror("Error", result)

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        self.sock.send(f"REGISTER {username} {password}".encode("utf-8"))
        result = self.sock.recv(4096).decode("utf-8")
        if "Recovery Code" in result:
            messagebox.showinfo("Sign up successful", result)
        else:
            messagebox.showerror("Sign up failed", result)

    def start_chat(self, username):
        self.root = tk.Tk()
        self.root.title(f"Chat Client - {username}")

        self.text_area = tk.Text(self.root, state="disabled", width=60, height=20)
        self.text_area.pack(padx=10, pady=10)

        self.entry = tk.Entry(self.root, width=60)
        self.entry.pack(padx=10, pady=5, fill="x")
        self.entry.bind("<Return>", self.send_message)

        threading.Thread(target=self.receive_messages, daemon=True).start()
        self.root.mainloop()

    def send_message(self, event=None):
        msg = self.entry.get()
        if msg.strip():
            try:
                self.sock.send(msg.encode("utf-8"))
            except:
                pass
        self.entry.delete(0, tk.END)

    def receive_messages(self):
        while True:
            try:
                msg = self.sock.recv(1024).decode("utf-8")
                if not msg:
                    break
                self.text_area.config(state="normal")
                self.text_area.insert(tk.END, msg + "\n")
                self.text_area.config(state="disabled")
                self.text_area.see(tk.END)
            except:
                break

if __name__ == "__main__":
    ChatClient()