import json
import os
import hashlib
import random
import string

USER_FILE = "users.json"
CHARSET = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{};:,.<>?/"

def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def generate_recovery_codes(n=10, length=16):
    codes = set()
    while len(codes) < n:
        code = "".join(random.choices(CHARSET, k=length))
        codes.add(code)
    return list(codes)

def register_user(username, password):
    users = load_users()
    if username in users:
        return False, "User already exists"
    recovery_codes = generate_recovery_codes()
    users[username] = {
        "password": hash_password(password),
        "recovery_codes": recovery_codes
    }
    save_users(users)
    return True, recovery_codes

def login_user(username, password):
    users = load_users()
    if username not in users:
        return False, "User not exists"
    if users[username]["password"] != hash_password(password):
        return False, "Incorrect password"
    return True, "Login suscessfully"