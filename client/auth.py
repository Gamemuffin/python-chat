import tkinter as tk
from tkinter import messagebox
from network import send_json
from ui_helpers import make_entry

def login(client):
    _auth_cmd(client, "login")

def register(client):
    _auth_cmd(client, "register")

def _auth_cmd(client, typ):
    u, p = client.username_entry.get().strip(), client.password_entry.get()
    if not u or not p:
        return messagebox.showerror("Error", "Username and password required.")
    send_json(client, {"type": typ, "username": u, "password": p})

def reset_password(client):
    _popup_form(client, "Reset Password",
                [("Username", None), ("Recovery code", None), ("New password", "*")],
                lambda u, c, p: send_json(client, {"type": "reset_password",
                                                   "username": u, "recovery_code": c, "new_password": p}))

def delete_account(client):
    _popup_form(client, "Delete Account",
                [("Username", None), ("Recovery code", None)],
                lambda u, c: send_json(client, {"type": "delete_account",
                                                "username": u, "recovery_code": c}))

def _popup_form(client, title, fields, callback):
    win = tk.Toplevel(client.root)
    win.title(title)
    win.grab_set()
    entries = [make_entry(win, label, show) for label, show in fields]

    def do():
        vals = [e.get().strip() for e in entries]
        if any(not v for v in vals):
            return messagebox.showerror("Error", "All fields required.")
        callback(*vals)
        win.destroy()

    tk.Button(win, text="Confirm", command=do).pack()
