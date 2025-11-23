import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
import time

class ChatClient:
    def __init__(self):
        self.sock = None
        self.username = None
        self.connected = False
        self.show_connect_window()

    def show_connect_window(self):
        self.conn_root = tk.Tk()
        self.conn_root.title("Connect to server")

        tk.Label(self.conn_root, text="Server IP or domain").pack(pady=5)
        self.host_entry = tk.Entry(self.conn_root)
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.pack(pady=5)

        tk.Label(self.conn_root, text="Port").pack(pady=5)
        self.port_entry = tk.Entry(self.conn_root)
        self.port_entry.insert(0, "5000")
        self.port_entry.pack(pady=5)

        tk.Button(self.conn_root, text="Connect", command=self.connect_server).pack(pady=10)
        self.conn_root.mainloop()

    def connect_server(self):
        host = self.host_entry.get().strip()
        port = int(self.port_entry.get().strip())
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.connected = True
            messagebox.showinfo("Info", f"Connected to {host}:{port}")
            self.conn_root.destroy()
            self.show_auth_window()
            threading.Thread(target=self.ping_server, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {e}")

    def ping_server(self):
        while self.connected:
            try:
                self.sock.send(b"PING")
            except:
                self.connected = False
                self.handle_disconnect()
                break
            time.sleep(2)

    def show_auth_window(self):
        self.auth_root = tk.Tk()
        self.auth_root.title("Login or Register")

        tk.Label(self.auth_root, text="Username").pack(pady=5)
        self.username_entry = tk.Entry(self.auth_root)
        self.username_entry.pack(pady=5)

        tk.Label(self.auth_root, text="Password").pack(pady=5)
        self.password_entry = tk.Entry(self.auth_root, show="*")
        self.password_entry.pack(pady=5)

        btn_frame = tk.Frame(self.auth_root)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Login", width=12, command=self.login).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Register", width=12, command=self.register).grid(row=0, column=1, padx=5)
