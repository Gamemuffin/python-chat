# history.py
import os

def load_local_history(client):
    path = f"chat_history/{client.username}.txt"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                client.append_text(line.strip())

def save_local_history(client, line: str):
    if client.username:
        os.makedirs("chat_history", exist_ok=True)
        path = f"chat_history/{client.username}.txt"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        