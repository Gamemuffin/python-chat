import socket
import threading
import argparse
from user_manager import register_user, login_user

clients = {}
authenticated = {}

def handle_client(conn, addr):
    print(f"[Connect] {addr}")
    authenticated[conn] = False
    while True:
        try:
            msg = conn.recv(1024).decode("utf-8")
            if not msg:
                break

            if msg.startswith("REGISTER"):
                _, username, password = msg.split(" ", 2)
                success, result = register_user(username, password)
                if success:
                    conn.send(f"Sign up suscessfully, recovery code:\n{result}".encode("utf-8"))
                else:
                    conn.send(f"Sign up failed: {result}".encode("utf-8"))

            elif msg.startswith("LOGIN"):
                _, username, password = msg.split(" ", 2)
                success, result = login_user(username, password)
                if success:
                    authenticated[conn] = True
                    clients[conn] = username
                    conn.send(f"{result}".encode("utf-8"))
                else:
                    conn.send(f"Sign in failed: {result}".encode("utf-8"))

            else:
                if authenticated.get(conn, False):
                    broadcast(f"{clients[conn]}: {msg}", conn)
                else:
                    conn.send("Sign in or sigh up first!".encode("utf-8"))

        except:
            break
    conn.close()
    if conn in clients:
        del clients[conn]
    if conn in authenticated:
        del authenticated[conn]

def broadcast(msg, sender):
    for client in clients:
        if client != sender:
            try:
                client.send(msg.encode("utf-8"))
            except:
                pass

def start_server(host, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[Start] Chat server is running at {host}:{port}")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat Server")
    parser.add_argument("--host", default="0.0.0.0", help="Listening IP")
    parser.add_argument("--port", type=int, default=5000, help="Listening Port")
    args = parser.parse_args()
    start_server(args.host, args.port)