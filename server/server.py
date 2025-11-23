import socket
import threading
import argparse
import json
from typing import Dict, Tuple
from user_manager import register_user, login_user, reset_password_with_code, delete_user_with_code

# 保存客户端连接和用户名
clients_lock = threading.Lock()
clients: Dict[socket.socket, Dict] = {}

def send_json(conn: socket.socket, obj: dict) -> None:
    """发送 JSON 行到客户端"""
    try:
        data = (json.dumps(obj) + "\n").encode("utf-8")
        conn.sendall(data)
    except Exception:
        pass

def broadcast_chat(sender_conn: socket.socket, username: str, message: str) -> None:
    """广播聊天消息给其他客户端"""
    with clients_lock:
        for conn in list(clients.keys()):
            if conn is sender_conn:
                continue  # 自己的消息客户端已经显示，不需要再发回
            try:
                send_json(conn, {"type": "chat", "from": username, "message": message})
            except Exception:
                cleanup(conn)

def cleanup(conn: socket.socket) -> None:
    """清理断开的连接"""
    try:
        conn.close()
    except Exception:
        pass
    with clients_lock:
        if conn in clients:
            del clients[conn]

def parse_line(line: str) -> dict:
    """解析一行 JSON"""
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return {"type": "error", "message": "Invalid JSON"}

def handle_command(conn: socket.socket, cmd: dict) -> None:
    """处理客户端命令"""
    ctype = cmd.get("type")

    if ctype == "ping":
        send_json(conn, {"type": "pong"})
        return

    if ctype == "register":
        ok, result = register_user(cmd.get("username", ""), cmd.get("password", ""))
        if ok:
            send_json(conn, {"type": "register_ok", "recovery_codes": result})
        else:
            send_json(conn, {"type": "error", "message": result})
        return

    if ctype == "login":
        ok, result = login_user(cmd.get("username", ""), cmd.get("password", ""))
        if ok:
            with clients_lock:
                clients[conn] = {"username": cmd.get("username", "").strip()}
            send_json(conn, {"type": "login_ok", "message": result})
        else:
            send_json(conn, {"type": "error", "message": result})
        return

    if ctype == "reset_password":
        ok, result = reset_password_with_code(
            cmd.get("username", ""),
            cmd.get("recovery_code", ""),
            cmd.get("new_password", ""),
        )
        if ok:
            send_json(conn, {"type": "reset_ok", "message": result})
        else:
            send_json(conn, {"type": "error", "message": result})
        return

    if ctype == "delete_account":
        ok, result = delete_user_with_code(
            cmd.get("username", ""),
            cmd.get("recovery_code", ""),
        )
        if ok:
            send_json(conn, {"type": "delete_ok", "message": result})
        else:
            send_json(conn, {"type": "error", "message": result})
        return

    if ctype == "chat":
        with clients_lock:
            username = clients.get(conn, {}).get("username")
        if not username:
            send_json(conn, {"type": "error", "message": "Please login first."})
            return
        msg = str(cmd.get("message", "")).strip()
        if msg:
            broadcast_chat(conn, username, msg)
        return

    send_json(conn, {"type": "error", "message": "Unknown command"})

def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
    """处理单个客户端连接"""
    print(f"[Connected] {addr}")
    with clients_lock:
        clients[conn] = {"username": None}

    buf = ""
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buf += data.decode("utf-8", errors="ignore")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                if not line.strip():
                    continue
                cmd = parse_line(line)
                handle_command(conn, cmd)
    except Exception as e:
        print(f"[Error] {addr}: {e}")
    finally:
        cleanup(conn)
        print(f"[Disconnected] {addr}")

def start_server(host: str, port: int) -> None:
    """启动服务器"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen()
    print(f"[Started] Chat server listening on {host}:{port}")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat Server (plaintext)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind IP")
    parser.add_argument("--port", type=int, default=5000, help="Port")
    args = parser.parse_args()
    start_server(args.host, args.port)
