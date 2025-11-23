import socket
import threading
import argparse
from user_manager import register_user, login_user, reset_password_with_code, delete_user_with_code

clients = {}
authenticated = {}

def handle_client(conn, addr):
    print(f"[Connected] {addr}")
    authenticated[conn] = False
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            msg = data.decode("utf-8", errors="ignore")

            if msg == "PING":
                conn.send(b"PONG")
                continue

            if msg.startswith("REGISTER "):
                _, username, password = msg.split(" ", 2)
                success, result = register_user(username.strip(), password)
                if success:
                    codes_text = "\n".join(result)
                    response = f"Registration successful!\nYour recovery codes:\n{codes_text}"
                    conn.send(response.encode("utf-8"))
                else:
                    conn.send(f"Register failed: {result}".encode("utf-8"))

            elif msg.startswith("LOGIN "):
                _, username, password = msg.split(" ", 2)
                success, result = login_user(username.strip(), password)
                if success:
                    authenticated[conn] = True
                    clients[conn] = username.strip()
                    conn.send(result.encode("utf-8"))
                else:
                    conn.send(f"Login failed: {result}".encode("utf-8"))

            elif msg.startswith("RESET "):
                _, username, recovery_code, new_password = msg.split(" ", 3)
                success, result = reset_password_with_code(username.strip(), recovery_code.strip(), new_password)
                if success:
                    conn.send(result.encode("utf-8"))
                else:
                    conn.send(f"Reset failed: {result}".encode("utf-8"))

            elif msg.startswith("DELETE "):
                _, username, recovery_code = msg.split(" ", 2)
                success, result = delete_user_with_code(username.strip(), recovery_code.strip())
                if success:
                    conn.send(result.encode("utf-8"))
                else:
                    conn.send(f"Delete failed: {result}".encode("utf-8"))

            else:
                if authenticated.get(conn, False):
                    username = clients.get(conn, "Unknown")
                    broadcast(f"{username}: {msg}", conn)
                else:
                    conn.send(b"Please login or register first.")
    except Exception as e:
        print(f"[Error] {addr} -> {e}")
    finally:
        cleanup_connection(conn)

def broadcast(msg, sender):
    for client in list(clients.keys()):
        try:
            client.send(msg.encode("utf-8"))
        except:
            cleanup_connection(client)

def cleanup_connection(conn):
    try:
        conn.close()
    except:
        pass
    if conn in clients:
        del clients[conn]
    if conn in authenticated:
        del authenticated[conn]

def start_server(host, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen()
    print(f"[Started] Chat server listening on {host}:{port}")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind IP address")
    parser.add_argument("--port", type=int, default=5000, help="Listening port")
    args = parser.parse_args()
    start_server(args.host, args.port)
