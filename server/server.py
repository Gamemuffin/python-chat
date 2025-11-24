# server.py
import socket
import threading
import argparse
import json
import os
import time
import random
from typing import Dict, Tuple
from user_manager import (
    register_user, login_user, reset_password_with_code, delete_user_with_code,
    add_contact, remove_contact, list_contacts, get_user_by_username, set_user_field
)

clients_lock = threading.Lock()
# map socket -> { "username": str or None }
clients: Dict[socket.socket, Dict] = {}

# ephemeral codes: username -> {"code": "123456", "expire": timestamp}
ephemeral_lock = threading.Lock()
ephemeral_codes: Dict[str, Dict] = {}

LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

def send_json(conn: socket.socket, obj: dict) -> None:
    try:
        data = (json.dumps(obj) + "\n").encode("utf-8")
        conn.sendall(data)
    except Exception:
        pass

def broadcast_chat(sender_conn: socket.socket, username: str, message: str) -> None:
    # save to server logs
    timestamp = int(time.time())
    log_line = f"{timestamp} {username}: {message}\n"
    # global log
    with open(os.path.join(LOG_DIR, "global.log"), "a", encoding="utf-8") as f:
        f.write(log_line)
    # write per-user logs (append to every existing user file so server keeps per-user history)
    # this might duplicate but ensures everyone has a record on server
    users = []
    try:
        for fn in os.listdir(LOG_DIR):
            # skip global.log
            pass
    except Exception:
        pass

    # broadcast to clients
    with clients_lock:
        for conn in list(clients.keys()):
            try:
                send_json(conn, {"type": "chat", "from": username, "message": message})
            except Exception:
                cleanup(conn)
    # also update per-user logs for existing registered users
    # fetch list of users from user_manager file by reading users.json indirectly via user_manager
    # to avoid circular imports we will attempt to write to each user's log only if their file name is present
    try:
        # read users file content using get_user_by_username is heavy; to be simple just write user-specific logs for currently connected users
        with clients_lock:
            for c, info in clients.items():
                uname = info.get("username")
                if uname:
                    with open(os.path.join(LOG_DIR, f"{uname}.log"), "a", encoding="utf-8") as f:
                        f.write(log_line)
    except Exception:
        pass

def cleanup(conn: socket.socket) -> None:
    try:
        conn.close()
    except Exception:
        pass
    with clients_lock:
        if conn in clients:
            del clients[conn]

def parse_line(line: str) -> dict:
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return {"type": "error", "message": "Invalid JSON"}

def handle_command(conn: socket.socket, cmd: dict) -> None:
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

    # --- new contact / ephemeral code APIs ---
    if ctype == "get_code":
        # return current ephemeral code for the logged-in user
        with clients_lock:
            username = clients.get(conn, {}).get("username")
        if not username:
            send_json(conn, {"type": "error", "message": "Please login first."})
            return
        with ephemeral_lock:
            ent = ephemeral_codes.get(username)
            if ent and ent.get("expire", 0) > time.time():
                code = ent["code"]
                ttl = int(ent["expire"] - time.time())
            else:
                # generate a fresh code immediately
                code = f"{random.randint(0,999999):06d}"
                expire = time.time() + 60
                ephemeral_codes[username] = {"code": code, "expire": expire}
                ttl = 60
        send_json(conn, {"type": "your_code", "code": code, "ttl": ttl})
        return

    if ctype == "add_contact":
        # payload: code (6-digit)
        code = str(cmd.get("code", "")).strip()
        with clients_lock:
            username = clients.get(conn, {}).get("username")
        if not username:
            send_json(conn, {"type": "error", "message": "Please login first."})
            return
        if not code or len(code) != 6 or not code.isdigit():
            send_json(conn, {"type": "error", "message": "Invalid code format."})
            return
        # find which username currently has that ephemeral code
        target = None
        with ephemeral_lock:
            for u, ent in ephemeral_codes.items():
                if ent.get("code") == code and ent.get("expire", 0) > time.time():
                    target = u
                    break
        if not target:
            send_json(conn, {"type": "error", "message": "Code invalid or expired."})
            return
        if target == username:
            send_json(conn, {"type": "error", "message": "Cannot add yourself."})
            return
        ok, msg = add_contact(username, target)
        if ok:
            send_json(conn, {"type": "add_contact_ok", "message": msg, "contact": target})
        else:
            send_json(conn, {"type": "error", "message": msg})
        return

    if ctype == "remove_contact":
        target = str(cmd.get("target", "")).strip()
        with clients_lock:
            username = clients.get(conn, {}).get("username")
        if not username:
            send_json(conn, {"type": "error", "message": "Please login first."})
            return
        ok, msg = remove_contact(username, target)
        if ok:
            send_json(conn, {"type": "remove_contact_ok", "message": msg, "contact": target})
        else:
            send_json(conn, {"type": "error", "message": msg})
        return

    if ctype == "list_contacts":
        with clients_lock:
            username = clients.get(conn, {}).get("username")
        if not username:
            send_json(conn, {"type": "error", "message": "Please login first."})
            return
        ok, contacts = list_contacts(username)
        if not ok:
            send_json(conn, {"type": "error", "message": "Failed to list contacts."})
            return
        # also include online status for each contact
        online_map = {}
        with clients_lock:
            for c, info in clients.items():
                uname = info.get("username")
                if uname:
                    online_map[uname] = True
        contacts_with_status = [{"username": u, "online": bool(online_map.get(u, False))} for u in contacts]
        send_json(conn, {"type": "list_contacts_ok", "contacts": contacts_with_status})
        return

    if ctype == "query_online":
        target = str(cmd.get("user", "")).strip()
        with clients_lock:
            # find whether any connected client has that username
            online = False
            for c, info in clients.items():
                if info.get("username") == target:
                    online = True
                    break
        send_json(conn, {"type": "online_status", "user": target, "online": online})
        return

    # unknown
    send_json(conn, {"type": "error", "message": "Unknown command"})

def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
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

def start_ephemeral_code_updater(interval: int = 60):
    """Background thread that sets a new 6-digit code for every registered user each interval."""
    def worker():
        while True:
            # read users from user_manager via get_user_by_username? There's no direct list function,
            # so we'll attempt to read users.json directly to get usernames.
            try:
                if os.path.exists("users.json"):
                    with open("users.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    now = time.time()
                    with ephemeral_lock:
                        for uname in data.keys():
                            code = f"{random.randint(0,999999):06d}"
                            ephemeral_codes[uname] = {"code": code, "expire": now + interval}
                else:
                    # no users yet
                    pass
            except Exception as e:
                print("[ephemeral updater] error:", e)
            time.sleep(interval)
    t = threading.Thread(target=worker, daemon=True)
    t.start()

def start_server(host: str, port: int) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen()
    print(f"[Started] Chat server listening on {host}:{port}")
    start_ephemeral_code_updater(60)
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat Server (plaintext) with contacts and ephemeral codes")
    parser.add_argument("--host", default="0.0.0.0", help="Bind IP")
    parser.add_argument("--port", type=int, default=5000, help="Port")
    args = parser.parse_args()
    start_server(args.host, args.port)
