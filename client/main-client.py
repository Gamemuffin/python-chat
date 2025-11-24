# main-client.py
import tkinter as tk
from tkinter import messagebox
import threading, socket, json, time, os

from ui_helpers import make_entry, append_text, show_codes_window
from network import connect_server, send_json, read_loop, ping_loop, disconnect_socket
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
        f = tk.Frame(self.root); f.pack(padx=12,pady=12,fill="x")
        self.host_entry = make_entry(f,"Server IP or domain"); self.host_entry.insert(0,"127.0.0.1")
        self.port_entry = make_entry(f,"Port"); self.port_entry.insert(0,"5000")
        tk.Button(f,text="Connect",command=lambda: connect_server(self)).pack(pady=8)


    def close_all(self):
        self.stop_threads.set()
        disconnect_socket(self)
        self.root.destroy()

if __name__=="__main__":
    ChatClient()
