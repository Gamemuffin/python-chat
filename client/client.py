import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

class ChatClient:
    def __init__(self):
        self.sock = None
        self.username = None
        self.show_connect_window()

    # Step 1: Connect window for IP and port
    def show_connect_window(self):
        self.conn_root = tk.Tk()
        self.conn_root.title("Connect to server")

        tk.Label(self.conn_root, text="Server IP address").pack(pady=5)
        self.host_entry = tk.Entry(self.conn_root)
        self.host_entry.insert(0, "127.0.0.1")  # default value
        self.host_entry.pack(pady=5)

        tk.Label(self.conn_root, text="Port").pack(pady=5)
        self.port_entry = tk.Entry(self.conn_root)
        self.port_entry.insert(0, "5000")  # default value
        self.port_entry.pack(pady=5)

        tk.Button(self.conn_root, text="Connect", command=self.connect_server).pack(pady=10)
        self.conn_root.mainloop()

    def connect_server(self):
        host = self.host_entry.get().strip()
        port_text = self.port_entry.get().strip()
        try:
            port = int(port_text)
        except ValueError:
            messagebox.showerror("Error", "Port must be a number.")
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            messagebox.showinfo("Info", f"Connected to {host}:{port}")
            self.conn_root.destroy()
            self.show_auth_window()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {e}")

    # Step 2: Authentication window (login/register/forgot password)
    def show_auth_window(self):
        self.auth_root = tk.Tk()
        self.auth_root.title("Login or Register")

        tk.Label(self.auth_root, text="Username").pack(pady=5)
        self.username_entry = tk.Entry(self.auth_root)
        self.username_entry.pack(pady=5)

        tk.Label(self.auth_root, text="Password").pack(pady=5)
        self.password_entry = tk.Entry(self.auth_root, show="*")
        self.password_entry.pack(pady=5)

        btn_frame = tk.Frame(self.auth_root)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Login", width=12, command=self.login).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Register", width=12, command=self.register).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Forgot password", width=16, command=self.reset_password).grid(row=0, column=2, padx=5)

        self.auth_root.mainloop()

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showerror("Error", "Username and password are required.")
            return
        try:
            self.sock.send(f"LOGIN {username} {password}".encode("utf-8"))
            result = self.sock.recv(4096).decode("utf-8")
            if "Login successful" in result:
                messagebox.showinfo("Info", result)
                self.username = username
                self.auth_root.destroy()
                self.start_chat()
            else:
                messagebox.showerror("Error", result)
        except Exception as e:
            messagebox.showerror("Error", f"Login failed: {e}")

    def register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showerror("Error", "Username and password are required.")
            return
        try:
            self.sock.send(f"REGISTER {username} {password}".encode("utf-8"))
            result = self.sock.recv(4096).decode("utf-8")
            if "Registration successful" in result:
                # Show recovery codes in a scrollable dialog
                messagebox.showinfo("Registration", "Registration successful! Recovery codes will be shown next.")
                self.show_codes_window(result)
            else:
                messagebox.showerror("Error", result)
        except Exception as e:
            messagebox.showerror("Error", f"Registration failed: {e}")

    def show_codes_window(self, result_text):
        codes_win = tk.Toplevel(self.auth_root)
        codes_win.title("Your recovery codes")
        tk.Label(codes_win, text="Please save these codes securely. Each code can be used once to reset your password.").pack(pady=5)
        txt = scrolledtext.ScrolledText(codes_win, width=60, height=15)
        txt.pack(padx=10, pady=10)
        txt.insert(tk.END, result_text)
        txt.config(state="disabled")
        tk.Button(codes_win, text="Close", command=codes_win.destroy).pack(pady=5)

    def reset_password(self):
        reset_win = tk.Toplevel(self.auth_root)
        reset_win.title("Reset password with recovery code")

        tk.Label(reset_win, text="Username").pack(pady=5)
        user_entry = tk.Entry(reset_win)
        user_entry.pack(pady=5)

        tk.Label(reset_win, text="Recovery code").pack(pady=5)
        code_entry = tk.Entry(reset_win)
        code_entry.pack(pady=5)

        tk.Label(reset_win, text="New password").pack(pady=5)
        newpass_entry = tk.Entry(reset_win, show="*")
        newpass_entry.pack(pady=5)

        def do_reset():
            u = user_entry.get().strip()
            c = code_entry.get().strip()
            p = newpass_entry.get()
            if not u or not c or not p:
                messagebox.showerror("Error", "All fields are required.")
                return
            try:
                self.sock.send(f"RESET {u} {c} {p}".encode("utf-8"))
                result = self.sock.recv(4096).decode("utf-8")
                if "successfully" in result or "reset" in result.lower():
                    messagebox.showinfo("Info", result)
                    reset_win.destroy()
                else:
                    messagebox.showerror("Error", result)
            except Exception as e:
                messagebox.showerror("Error", f"Reset failed: {e}")

        tk.Button(reset_win, text="Confirm reset", command=do_reset).pack(pady=10)

    # Step 3: Chat window
    def start_chat(self):
        self.chat_root = tk.Tk()
        self.chat_root.title(f"Chat - {self.username}")

        self.text_area = tk.Text(self.chat_root, state="disabled", width=70, height=20)
        self.text_area.pack(padx=10, pady=10)

        entry_frame = tk.Frame(self.chat_root)
        entry_frame.pack(fill="x", padx=10, pady=5)

        self.entry = tk.Entry(entry_frame)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.send_message)

        tk.Button(entry_frame, text="Send", width=10, command=self.send_message).pack(side="right", padx=5)

        threading.Thread(target=self.receive_messages, daemon=True).start()
        self.chat_root.mainloop()

    def send_message(self, event=None):
        msg = self.entry.get()
        if msg.strip():
            try:
                self.sock.send(msg.encode("utf-8"))
            except Exception as e:
                messagebox.showerror("Error", f"Send failed: {e}")
        self.entry.delete(0, tk.END)

    def receive_messages(self):
        while True:
            try:
                data = self.sock.recv(1024)
                if not data:
                    break
                msg = data.decode("utf-8", errors="ignore")
                self.text_area.config(state="normal")
                self.text_area.insert(tk.END, msg + "\n")
                self.text_area.config(state="disabled")
                self.text_area.see(tk.END)
            except:
                break

if __name__ == "__main__":
    ChatClient()