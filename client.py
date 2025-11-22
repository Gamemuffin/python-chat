import socket
import threading
import tkinter as tk
import argparse

class ChatClient:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        self.root = tk.Tk()
        self.root.title(f"Chat Client - {host}:{port}")

        self.text_area = tk.Text(self.root, state="disabled", width=50, height=20)
        self.text_area.pack(padx=10, pady=10)

        self.entry = tk.Entry(self.root, width=50)
        self.entry.pack(padx=10, pady=5, fill="x")
        self.entry.bind("<Return>", self.send_message)

        threading.Thread(target=self.receive_messages, daemon=True).start()
        self.root.mainloop()

    def send_message(self, event=None):
        msg = self.entry.get()
        if msg.strip():
            try:
                self.sock.send(msg.encode("utf-8"))
            except:
                pass
        self.entry.delete(0, tk.END)

    def receive_messages(self):
        while True:
            try:
                msg = self.sock.recv(1024).decode("utf-8")
                if not msg:
                    break
                self.text_area.config(state="normal")
                self.text_area.insert(tk.END, msg + "\n")
                self.text_area.config(state="disabled")
                self.text_area.see(tk.END)
            except:
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat Client")
    parser.add_argument("--host", default="127.0.0.1", help="Server IP address")
    parser.add_argument("--port", type=int, default=5000, help="Server Port")
    args = parser.parse_args()
    ChatClient(args.host, args.port)