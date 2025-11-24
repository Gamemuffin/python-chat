# ui_helpers.py
import tkinter as tk
from tkinter import messagebox

def make_entry(parent, label, show=None):
    tk.Label(parent, text=label).pack(pady=4)
    e = tk.Entry(parent, show=show) if show else tk.Entry(parent)
    e.pack(pady=4, fill="x")
    return e

def append_text(text_area, line: str):
    text_area.config(state="normal")
    text_area.insert("end", line + "\n")
    text_area.config(state="disabled")
    text_area.see("end")

def show_codes_window(root, codes):
    if not codes:
        return messagebox.showinfo("Recovery Codes", "No recovery codes received.")

    win = tk.Toplevel(root)
    win.title("Your Recovery Codes")
    win.geometry("400x300")
    win.grab_set()

    tk.Label(
        win,
        text="Please save these recovery codes safely.\n"
             "They are required for password reset or account deletion.",
        justify="center"
    ).pack(pady=10)

    text = tk.Text(win, height=12, width=40)
    text.pack(padx=10, pady=10, fill="both", expand=True)
    text.insert("end", "\n".join(codes))
    text.config(state="disabled")

    tk.Button(win, text="Close", command=win.destroy).pack(pady=10)
