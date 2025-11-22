import socket
import threading
import argparse

clients = []

def handle_client(conn, addr):
    print(f"[Connect] {addr}")
    while True:
        try:
            msg = conn.recv(1024).decode("utf-8")
            if not msg:
                break
            broadcast(msg, conn)
        except:
            break
    conn.close()
    if conn in clients:
        clients.remove(conn)

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
        clients.append(conn)
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat Server")
    parser.add_argument("--host", default="0.0.0.0", help="Listening IP")
    parser.add_argument("--port", type=int, default=5000, help="Listening Port")
    args = parser.parse_args()
    start_server(args.host, args.port)