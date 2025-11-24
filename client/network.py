# network.py
import socket, threading, json, time
from tkinter import messagebox

def connect_server(client):
    try:
        port = int(client.port_entry.get().strip())
    except:
        return messagebox.showerror("Error", "Port must be a number.")

    disconnect_socket(client)
    client.stop_threads.clear()

    try:
        client.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.sock.connect((client.host_entry.get().strip(), port))
        client.sock.settimeout(None)
        client.connected = True
        messagebox.showinfo("Info", f"Connected to server")
    except Exception as e:
        client.connected = False
        client.sock = None
        return messagebox.showerror("Error", f"Connection failed: {e}")

    client.build_auth_view()
    threading.Thread(target=read_loop, args=(client,), daemon=True).start()
    threading.Thread(target=ping_loop, args=(client,), daemon=True).start()

def send_json(client, obj: dict):
    if not client.connected or not client.sock: return
    try:
        data = (json.dumps(obj) + "\n").encode("utf-8")
        client.sock.sendall(data)
    except:
        client.root.after(0, client.on_disconnect)

def read_loop(client):
    try:
        while client.connected and not client.stop_threads.is_set():
            data = client.sock.recv(4096)
            if not data: break
            client.buffer += data.decode("utf-8", errors="ignore")
            while "\n" in client.buffer:
                line, client.buffer = client.buffer.split("\n", 1)
                if line.strip():
                    client.root.after(0, client.handle_server_message, line)
    except:
        pass
    client.root.after(0, client.on_disconnect)

def ping_loop(client):
    while client.connected and not client.stop_threads.is_set():
        send_json(client, {"type": "ping"})
        for _ in range(20):
            if client.stop_threads.is_set(): return
            time.sleep(0.1)

def disconnect_socket(client):
    try:
        if client.sock:
            try: client.sock.shutdown(socket.SHUT_RDWR)
            except: pass
            client.sock.close()
    except: pass
    client.sock = None
    client.connected = False
