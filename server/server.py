# server.py (optimized)
import socket, threading, argparse, json, os, time, random
from typing import Dict, Tuple
from user_manager import (
    register_user, login_user, reset_password_with_code, delete_user_with_code,
    add_contact, remove_contact, list_contacts
)

clients_lock = threading.Lock()
clients: Dict[socket.socket, Dict] = {}

ephemeral_lock = threading.Lock()
ephemeral_codes: Dict[str, Dict] = {}

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ---------------------
# Helpers
# ---------------------
def send_json(conn, obj): 
    try: conn.sendall((json.dumps(obj) + "\n").encode())
    except: cleanup(conn)

def get_username(conn): 
    with clients_lock: return clients.get(conn, {}).get("username")

def write_log(username, msg):
    ts = int(time.time())
    line = f"{ts} {username}: {msg}\n"
    open(os.path.join(LOG_DIR, "global.log"), "a", encoding="utf-8").write(line)
    with clients_lock:
        for _, info in clients.items():
            u = info.get("username")
            if u: open(os.path.join(LOG_DIR, f"{u}.log"), "a", encoding="utf-8").write(line)

def broadcast_chat(sender, username, msg):
    write_log(username, msg)
    with clients_lock:
        for c in list(clients.keys()):
            send_json(c, {"type": "chat", "from": username, "message": msg})

def cleanup(conn):
    try: conn.close()
    except: pass
    with clients_lock: clients.pop(conn, None)

def parse_line(line): 
    try: return json.loads(line)
    except: return {"type": "error", "message": "Invalid JSON"}

# ---------------------
# Command Handlers
# ---------------------
def cmd_register(conn, cmd):
    ok, res = register_user(cmd.get("username",""), cmd.get("password",""))
    send_json(conn, {"type": "register_ok", "recovery_codes": res} if ok else {"type":"error","message":res})

def cmd_login(conn, cmd):
    ok, res = login_user(cmd.get("username",""), cmd.get("password",""))
    if ok:
        with clients_lock: clients[conn] = {"username": cmd.get("username","").strip()}
        send_json(conn, {"type":"login_ok","message":res})
    else: send_json(conn, {"type":"error","message":res})

def cmd_reset(conn, cmd):
    ok, res = reset_password_with_code(cmd.get("username",""), cmd.get("recovery_code",""), cmd.get("new_password",""))
    send_json(conn, {"type":"reset_ok","message":res} if ok else {"type":"error","message":res})

def cmd_delete(conn, cmd):
    ok, res = delete_user_with_code(cmd.get("username",""), cmd.get("recovery_code",""))
    send_json(conn, {"type":"delete_ok","message":res} if ok else {"type":"error","message":res})

def cmd_chat(conn, cmd):
    u = get_username(conn)
    if not u: return send_json(conn, {"type":"error","message":"Please login first."})
    msg = str(cmd.get("message","")).strip()
    if msg: broadcast_chat(conn, u, msg)

def cmd_get_code(conn, cmd):
    u = get_username(conn)
    if not u: return send_json(conn, {"type":"error","message":"Please login first."})
    with ephemeral_lock:
        ent = ephemeral_codes.get(u)
        if ent and ent["expire"] > time.time():
            code, ttl = ent["code"], int(ent["expire"]-time.time())
        else:
            code = f"{random.randint(0,999999):06d}"
            ephemeral_codes[u] = {"code":code,"expire":time.time()+60}
            ttl = 60
    send_json(conn, {"type":"your_code","code":code,"ttl":ttl})

def cmd_add_contact(conn, cmd):
    u = get_username(conn)
    code = str(cmd.get("code","")).strip()
    if not u: return send_json(conn, {"type":"error","message":"Please login first."})
    if not (code.isdigit() and len(code)==6): return send_json(conn, {"type":"error","message":"Invalid code format."})
    target=None
    with ephemeral_lock:
        for name, ent in ephemeral_codes.items():
            if ent["code"]==code and ent["expire"]>time.time(): target=name; break
    if not target: return send_json(conn, {"type":"error","message":"Code invalid or expired."})
    if target==u: return send_json(conn, {"type":"error","message":"Cannot add yourself."})
    ok,msg = add_contact(u,target)
    send_json(conn, {"type":"add_contact_ok","message":msg,"contact":target} if ok else {"type":"error","message":msg})

def cmd_remove_contact(conn, cmd):
    u = get_username(conn)
    if not u: return send_json(conn, {"type":"error","message":"Please login first."})
    ok,msg = remove_contact(u, cmd.get("target","").strip())
    send_json(conn, {"type":"remove_contact_ok","message":msg,"contact":cmd.get("target","")} if ok else {"type":"error","message":msg})

def cmd_list_contacts(conn, cmd):
    u = get_username(conn)
    if not u: return send_json(conn, {"type":"error","message":"Please login first."})
    ok, contacts = list_contacts(u)
    if not ok: return send_json(conn, {"type":"error","message":"Failed to list contacts."})
    online = {info.get("username"):True for _,info in clients.items()}
    send_json(conn, {"type":"list_contacts_ok","contacts":[{"username":c,"online":online.get(c,False)} for c in contacts]})

def cmd_query_online(conn, cmd):
    target = cmd.get("user","").strip()
    online = any(info.get("username")==target for _,info in clients.items())
    send_json(conn, {"type":"online_status","user":target,"online":online})

# ---------------------
# Dispatcher
# ---------------------
COMMANDS = {
    "register": cmd_register,
    "login": cmd_login,
    "reset_password": cmd_reset,
    "delete_account": cmd_delete,
    "chat": cmd_chat,
    "get_code": cmd_get_code,
    "add_contact": cmd_add_contact,
    "remove_contact": cmd_remove_contact,
    "list_contacts": cmd_list_contacts,
    "query_online": cmd_query_online,
    "ping": lambda c,_: send_json(c, {"type":"pong"})
}

def handle_command(conn, cmd):
    handler = COMMANDS.get(cmd.get("type"))
    if handler: handler(conn, cmd)
    else: send_json(conn, {"type":"error","message":"Unknown command"})

# ---------------------
# Client loop
# ---------------------
def handle_client(conn, addr):
    print(f"[Connected] {addr}")
    with clients_lock: clients[conn]={"username":None}
    buf=""
    try:
        while True:
            data=conn.recv(4096)
            if not data: break
            buf+=data.decode(errors="ignore")
            while "\n" in buf:
                line,buf=buf.split("\n",1)
                if line.strip(): handle_command(conn, parse_line(line))
    except Exception as e: print(f"[Error] {addr}: {e}")
    finally: cleanup(conn); print(f"[Disconnected] {addr}")

# ---------------------
# Ephemeral updater
# ---------------------
def start_ephemeral_code_updater(interval=60):
    def worker():
        while True:
            try:
                if os.path.exists("users.json"):
                    data=json.load(open("users.json",encoding="utf-8"))
                    now=time.time()
                    with ephemeral_lock:
                        for u in data.keys():
                            ephemeral_codes[u]={"code":f"{random.randint(0,999999):06d}","expire":now+interval}
            except Exception as e: print("[ephemeral updater] error:",e)
            time.sleep(interval)
    threading.Thread(target=worker,daemon=True).start()

# ---------------------
# Server start
# ---------------------
def start_server(host, port):
    srv=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    srv.bind((host,port)); srv.listen()
    print(f"[Started] Chat server listening on {host}:{port}")
    start_ephemeral_code_updater()
    while True:
        conn,addr=srv.accept()
        threading.Thread(target=handle_client,args=(conn,addr),daemon=True).start()

if __name__=="__main__":
    p=argparse.ArgumentParser(description="Chat Server (optimized)")
    p.add_argument("--host",default="0.0.0.0"); p.add_argument("--port",type=int,default=5000)
    args=p.parse_args(); start_server(args.host,args.port)
