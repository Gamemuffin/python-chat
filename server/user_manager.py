# user_manager.py
import json
import os
import hashlib
import random
import string
import uuid
from typing import Tuple, List, Dict, Any

USER_FILE = "users.json"
CHARSET = string.ascii_letters + string.digits + "-_=+@#"

def _read_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def _write_json(path: str, data: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def _generate_recovery_codes(n: int = 10, length: int = 16) -> List[str]:
    codes = set()
    while len(codes) < n:
        codes.add("".join(random.choices(CHARSET, k=length)))
    return sorted(list(codes))

def register_user(username: str, password: str) -> Tuple[bool, str or List[str]]:
    users = _read_json(USER_FILE)
    username = username.strip()
    if not username or not password:
        return False, "Username and password are required."
    if username in users:
        return False, "User already exists."
    users[username] = {
        "uuid": str(uuid.uuid4()),
        "password": _hash_password(password),
        # contacts stored as dict of username -> True (future: store metadata)
        "contacts": {},
        # recovery codes: fixed 10 and reusable (not popped)
        "recovery_codes": _generate_recovery_codes(10, 16),
    }
    _write_json(USER_FILE, users)
    return True, users[username]["recovery_codes"]

def login_user(username: str, password: str) -> Tuple[bool, str]:
    users = _read_json(USER_FILE)
    username = username.strip()
    if username not in users:
        return False, "User does not exist."
    if users[username]["password"] != _hash_password(password):
        return False, "Incorrect password."
    return True, "Login successful."

def reset_password_with_code(username: str, recovery_code: str, new_password: str) -> Tuple[bool, str]:
    users = _read_json(USER_FILE)
    username = username.strip()
    recovery_code = recovery_code.strip()
    if username not in users:
        return False, "User does not exist."
    codes = users[username].get("recovery_codes", [])
    if recovery_code not in codes:
        return False, "Invalid recovery code."
    if not new_password:
        return False, "New password is required."
    users[username]["password"] = _hash_password(new_password)
    # DO NOT remove the recovery code (reusable)
    _write_json(USER_FILE, users)
    return True, "Password has been reset successfully."

def delete_user_with_code(username: str, recovery_code: str) -> Tuple[bool, str]:
    users = _read_json(USER_FILE)
    username = username.strip()
    recovery_code = recovery_code.strip()
    if username not in users:
        return False, "User does not exist."
    codes = users[username].get("recovery_codes", [])
    if recovery_code not in codes:
        return False, "Invalid recovery code."
    del users[username]
    _write_json(USER_FILE, users)
    return True, "Account deleted successfully."

# ---------------------
# contact related helpers
# ---------------------
def add_contact(owner: str, target: str) -> Tuple[bool, str]:
    """Add target (username) to owner's contacts. does not require target acceptance."""
    users = _read_json(USER_FILE)
    owner = owner.strip()
    target = target.strip()
    if owner not in users:
        return False, "Owner does not exist."
    if target not in users:
        return False, "Target user does not exist."
    contacts = users[owner].get("contacts", {})
    if target in contacts:
        return False, "Already in contacts."
    contacts[target] = True
    users[owner]["contacts"] = contacts
    _write_json(USER_FILE, users)
    return True, f"{target} added to contacts."

def remove_contact(owner: str, target: str) -> Tuple[bool, str]:
    users = _read_json(USER_FILE)
    owner = owner.strip()
    target = target.strip()
    if owner not in users:
        return False, "Owner does not exist."
    contacts = users[owner].get("contacts", {})
    if target not in contacts:
        return False, "Contact not found."
    del contacts[target]
    users[owner]["contacts"] = contacts
    _write_json(USER_FILE, users)
    return True, f"{target} removed from contacts."

def list_contacts(username: str) -> Tuple[bool, List[str]]:
    users = _read_json(USER_FILE)
    username = username.strip()
    if username not in users:
        return False, []
    contacts = users[username].get("contacts", {})
    return True, sorted(list(contacts.keys()))

def get_user_by_username(username: str) -> Dict[str, Any]:
    users = _read_json(USER_FILE)
    return users.get(username)

# utility for server to update user data
def set_user_field(username: str, field: str, value) -> None:
    users = _read_json(USER_FILE)
    if username not in users:
        return
    users[username][field] = value
    _write_json(USER_FILE, users)
