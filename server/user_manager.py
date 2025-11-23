import json
import os
import hashlib
import random
import string
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
        json.dump(data, f, indent=2)
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
        "password": _hash_password(password),
        "recovery_codes": _generate_recovery_codes(),
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
    codes.remove(recovery_code)  # consume
    users[username]["recovery_codes"] = codes
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
