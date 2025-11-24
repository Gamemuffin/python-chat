# user_manager.py (optimized)
import json, os, hashlib, random, string, uuid
from typing import Tuple, List, Dict, Any

USER_FILE = "users.json"
CHARSET = string.ascii_letters + string.digits + "-_=+@#"

# ---------------------
# JSON helpers
# ---------------------
def _json(path: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Read or write JSON file depending on whether data is provided."""
    if data is None:  # read
        if not os.path.exists(path): return {}
        try:
            with open(path, encoding="utf-8") as f: return json.load(f)
        except: return {}
    else:  # write
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return data

# ---------------------
# Utility helpers
# ---------------------
def _hash(pw: str) -> str: return hashlib.sha256(pw.encode()).hexdigest()
def _codes(n: int = 10, length: int = 16) -> List[str]:
    return sorted({"".join(random.choices(CHARSET, k=length)) for _ in range(n)})

# ---------------------
# User management
# ---------------------
def register_user(username: str, password: str) -> Tuple[bool, str | List[str]]:
    users = _json(USER_FILE)
    username = username.strip()
    if not username or not password: return False, "Username and password required."
    if username in users: return False, "User already exists."
    users[username] = {
        "uuid": str(uuid.uuid4()),
        "password": _hash(password),
        "contacts": {},
        "recovery_codes": _codes()
    }
    _json(USER_FILE, users)
    return True, users[username]["recovery_codes"]

def login_user(username: str, password: str) -> Tuple[bool, str]:
    users = _json(USER_FILE)
    u = username.strip()
    if u not in users: return False, "User does not exist."
    return (True, "Login successful.") if users[u]["password"] == _hash(password) else (False, "Incorrect password.")

def reset_password_with_code(username: str, code: str, new_pw: str) -> Tuple[bool, str]:
    users = _json(USER_FILE)
    u, c = username.strip(), code.strip()
    if u not in users: return False, "User does not exist."
    if c not in users[u].get("recovery_codes", []): return False, "Invalid recovery code."
    if not new_pw: return False, "New password required."
    users[u]["password"] = _hash(new_pw)
    _json(USER_FILE, users)
    return True, "Password reset successfully."

def delete_user_with_code(username: str, code: str) -> Tuple[bool, str]:
    users = _json(USER_FILE)
    u, c = username.strip(), code.strip()
    if u not in users: return False, "User does not exist."
    if c not in users[u].get("recovery_codes", []): return False, "Invalid recovery code."
    del users[u]; _json(USER_FILE, users)
    return True, "Account deleted successfully."

# ---------------------
# Contacts
# ---------------------
def add_contact(owner: str, target: str) -> Tuple[bool, str]:
    users = _json(USER_FILE)
    o, t = owner.strip(), target.strip()
    if o not in users: return False, "Owner does not exist."
    if t not in users: return False, "Target user does not exist."
    contacts = users[o].setdefault("contacts", {})
    if t in contacts: return False, "Already in contacts."
    contacts[t] = True; _json(USER_FILE, users)
    return True, f"{t} added to contacts."

def remove_contact(owner: str, target: str) -> Tuple[bool, str]:
    users = _json(USER_FILE)
    o, t = owner.strip(), target.strip()
    if o not in users: return False, "Owner does not exist."
    contacts = users[o].get("contacts", {})
    if t not in contacts: return False, "Contact not found."
    del contacts[t]; _json(USER_FILE, users)
    return True, f"{t} removed from contacts."

def list_contacts(username: str) -> Tuple[bool, List[str]]:
    users = _json(USER_FILE)
    u = username.strip()
    if u not in users: return False, []
    return True, sorted(users[u].get("contacts", {}).keys())

def get_user_by_username(username: str) -> Dict[str, Any]:
    return _json(USER_FILE).get(username.strip())

def set_user_field(username: str, field: str, value) -> None:
    users = _json(USER_FILE)
    if username.strip() in users:
        users[username.strip()][field] = value
        _json(USER_FILE, users)
