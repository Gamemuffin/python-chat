
import json, os, hashlib, random, string, uuid

USER_FILE = "users.json"
CHARSET = string.ascii_letters + string.digits + "-_=+@#"

def _json(path, data=None):
    if data is None:
        if not os.path.exists(path): return {}
        try: return json.load(open(path, encoding="utf-8"))
        except: return {}
    else:
        tmp = path + ".tmp"
        json.dump(data, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return data

def _hash(pw): return hashlib.sha256(pw.encode()).hexdigest()

def _codes(n=10, length=16): return sorted(
    {"".join(random.choices(CHARSET, k=length)) for _ in range(n)}
)

def register_user(username, password):
    users = _json(USER_FILE)
    u = username.strip()
    if not u or not password: return False, "Username and password required."
    if u in users: return False, "User exists."
    users[u] = {
        "uuid": str(uuid.uuid4()),
        "password": _hash(password),
        "contacts": {},
        "recovery_codes": _codes()
    }
    _json(USER_FILE, users)
    return True, users[u]["recovery_codes"]

def login_user(username, password):
    users = _json(USER_FILE)
    u = username.strip()
    if u not in users: return False, "User does not exist."
    return (True, "Login successful.") if users[u]["password"] == _hash(password) else (False, "Incorrect password.")

def reset_password_with_code(username, code, new_pw):
    users = _json(USER_FILE)
    u, c = username.strip(), code.strip()
    if u not in users: return False, "User does not exist."
    if c not in users[u].get("recovery_codes", []): return False, "Invalid recovery code."
    if not new_pw: return False, "New password required."
    users[u]["password"] = _hash(new_pw)
    _json(USER_FILE, users)
    return True, "Password reset successfully."

def delete_user_with_code(username, code):
    users = _json(USER_FILE)
    u, c = username.strip(), code.strip()
    if u not in users: return False, "User does not exist."
    if c not in users[u].get("recovery_codes", []): return False, "Invalid recovery code."
    del users[u]; _json(USER_FILE, users)
    return True, "Account deleted successfully."

def add_contact(owner, target):
    users = _json(USER_FILE)
    o, t = owner.strip(), target.strip()
    if o not in users: return False, "Owner does not exist."
    if t not in users: return False, "Target user does not exist."
    contacts = users[o].setdefault("contacts", {})
    if t in contacts: return False, "Already in contacts."
    contacts[t] = True; _json(USER_FILE, users)
    return True, f"{t} added to contacts."

def remove_contact(owner, target):
    users = _json(USER_FILE)
    o, t = owner.strip(), target.strip()
    if o not in users: return False, "Owner does not exist."
    contacts = users[o].get("contacts", {})
    if t not in contacts: return False, "Contact not found."
    del contacts[t]; _json(USER_FILE, users)
    return True, f"{t} removed from contacts."

def list_contacts(username):
    users = _json(USER_FILE)
    u = username.strip()
    if u not in users: return False, []
    return True, sorted(users[u].get("contacts", {}).keys())
