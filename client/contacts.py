# contacts.py
import tkinter as tk
from tkinter import simpledialog
from network import send_json

def open_contacts_window(client):
    win = tk.Toplevel(client.root)
    win.title("Contacts")
    win.geometry("400x300")
    win.grab_set()

    listbox = tk.Listbox(win)
    listbox.pack(fill="both", expand=True, padx=6, pady=6)

    def add_contact():
        code = simpledialog.askstring("Add contact", "Enter 6-digit code:", parent=win)
        if code:
            send_json(client, {"type": "add_contact", "code": code})

    def remove_contact():
        sel = listbox.curselection()
        if sel:
            target = listbox.get(sel[0]).split(" ")[0]
            send_json(client, {"type": "remove_contact", "target": target})

    tk.Button(win, text="Add", command=add_contact).pack(side="left", padx=4, pady=4)
    tk.Button(win, text="Remove", command=remove_contact).pack(side="left", padx=4, pady=4)
    tk.Button(win, text="Close", command=win.destroy).pack(side="right", padx=4, pady=4)

def show_contacts_list(client, contacts):
    win = tk.Toplevel(client.root)
    win.title("Contacts List")
    win.geometry("300x300")
    win.grab_set()

    listbox = tk.Listbox(win)
    listbox.pack(fill="both", expand=True, padx=6, pady=6)

    for c in contacts:
        listbox.insert("end", f"{c['username']} ({'online' if c['online'] else 'offline'})")

def request_my_code(client):
    send_json(client, {"type": "get_code"})

def request_list_contacts(client):
    send_json(client, {"type": "list_contacts"})
