#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import threading
import sys
import os
import time
import base64
import argparse
import datetime
import ctypes
import subprocess
from pathlib import Path

# ====================== ANSI Colors ======================
def enable_ansi_windows():
    """Enable ANSI support on Windows (newer versions)"""
    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

enable_ansi_windows()

RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"

def print_red(text):
    print(RED + text + RESET)

def print_green(text):
    print(GREEN + text + RESET)

def print_banner():
    print(BOLD + "Welcome to BLACK ceo studio" + RESET)

# ====================== Server ======================
class ChatServer:
    def __init__(self, host='0.0.0.0', port=100, history_file='chat_history.txt'):
        self.host = host
        self.port = port
        self.history_file = history_file
        self.clients = []          # list of (conn, name)
        self.messages = []         # message history (list of strings)
        self.lock = threading.Lock()
        self.load_history()

    def load_history(self):
        """Load history from file"""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r', encoding='utf-8') as f:
                self.messages = [line.strip() for line in f.readlines()]
        else:
            self.messages = []

    def save_history(self):
        """Save history to file"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            for msg in self.messages:
                f.write(msg + '\n')

    def broadcast(self, message, exclude_conn=None):
        """Send message to all clients except exclude_conn"""
        with self.lock:
            for conn, name in self.clients:
                if conn != exclude_conn:
                    try:
                        conn.sendall((message + '\n').encode('utf-8'))
                    except:
                        pass

    def send_history(self, conn):
        """Send chat history to a newly connected client"""
        for msg in self.messages:
            try:
                conn.sendall((msg + '\n').encode('utf-8'))
            except:
                break

    def handle_client(self, conn, addr):
        """Handle a single client connection"""
        print(f"[+] Connection from {addr}")
        name = None
        try:
            # Authentication phase
            name = conn.recv(1024).decode('utf-8').strip()
            if name not in ['Farzad', 'DrNesteD']:
                conn.sendall(('ERROR: Invalid name\n').encode('utf-8'))
                conn.close()
                return
            conn.sendall(b'OK_NAME\n')

            # Receive password
            password = conn.recv(1024).decode('utf-8').strip()
            if password != '0990':
                conn.sendall(('ERROR: Wrong password\n').encode('utf-8'))
                conn.close()
                return
            conn.sendall(b'OK_PASS\n')

            # Success
            conn.sendall(b'LOGIN_SUCCESS\n')
            print_green(f"[+] User {name} logged in")

            # Add to client list
            with self.lock:
                self.clients.append((conn, name))

            # Send history
            self.send_history(conn)

            # Message loop
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                msg = data.decode('utf-8').strip()
                if not msg:
                    continue

                # Process message
                if msg.startswith('/image '):
                    # Send image
                    parts = msg.split(' ', 1)
                    if len(parts) < 2:
                        continue
                    filename = parts[1].strip()
                    try:
                        with open(filename, 'rb') as f:
                            img_data = base64.b64encode(f.read()).decode('utf-8')
                        full_msg = f"IMAGE:{os.path.basename(filename)}:{img_data}"
                        with self.lock:
                            self.messages.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {name} sent image: {filename}")
                        self.save_history()
                        self.broadcast(full_msg, exclude_conn=conn)
                        conn.sendall((full_msg + '\n').encode('utf-8'))
                    except Exception as e:
                        conn.sendall((f"Error sending image: {e}\n").encode('utf-8'))
                else:
                    # Normal text message
                    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
                    formatted = f"[{timestamp}] {name}: {msg}"
                    with self.lock:
                        self.messages.append(formatted)
                    self.save_history()
                    self.broadcast(formatted, exclude_conn=conn)
                    conn.sendall((formatted + '\n').encode('utf-8'))

        except Exception as e:
            print(f"[-] Error with {addr}: {e}")
        finally:
            with self.lock:
                self.clients = [(c, n) for c, n in self.clients if c != conn]
            try:
                conn.close()
            except:
                pass
            print(f"[-] User {name or 'Unknown'} from {addr} disconnected")

    def start(self):
        """Start the server"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(5)
        print_banner()
        print_green(f"[*] Server running on port {self.port}...")
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.daemon = True
            thread.start()

# ====================== Client ======================
class ChatClient:
    def __init__(self, host='127.0.0.1', port=100):
        self.host = host
        self.port = port
        self.sock = None
        self.running = True
        self.name = None

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            return True
        except Exception as e:
            print_red(f"Connection error: {e}")
            return False

    def login(self):
        """Authentication with color feedback"""
        print_banner()
        # Get name
        while True:
            name = input(RED + "Enter your name : " + RESET).strip()
            if not name:
                continue
            self.sock.sendall((name + '\n').encode('utf-8'))
            resp = self.sock.recv(1024).decode('utf-8').strip()
            if resp == 'OK_NAME':
                print_green("Name accepted")
                self.name = name
                break
            else:
                print_red("Invalid name. Allowed: Farzad, DrNesteD.")
                continue

        # Get password
        while True:
            password = input(RED + "Please enter the password : " + RESET).strip()
            self.sock.sendall((password + '\n').encode('utf-8'))
            resp = self.sock.recv(1024).decode('utf-8').strip()
            if resp == 'OK_PASS':
                print_green("Password correct")
                break
            else:
                print_red("Wrong password.")
                continue

        # Get success message
        resp = self.sock.recv(1024).decode('utf-8').strip()
        if resp == 'LOGIN_SUCCESS':
            print_green("Login successful! Welcome to the team.")
            return True
        else:
            print_red("Login failed.")
            return False

    def receive_messages(self):
        """Receive messages from server and display"""
        while self.running:
            try:
                data = self.sock.recv(4096).decode('utf-8')
                if not data:
                    break
                lines = data.split('\n')
                for line in lines:
                    if not line:
                        continue
                    if line.startswith('IMAGE:'):
                        _, filename, b64data = line.split(':', 2)
                        self.handle_image(filename, b64data)
                    else:
                        if ':' in line:
                            if line.startswith('['):
                                parts = line.split('] ', 1)
                                if len(parts) == 2:
                                    rest = parts[1]
                                    if ': ' in rest:
                                        sender, msg = rest.split(': ', 1)
                                        print(GREEN + sender + RESET + ": " + msg)
                                    else:
                                        print(line)
                                else:
                                    print(line)
                            else:
                                print(line)
                        else:
                            print(line)
            except Exception as e:
                print_red(f"Receive error: {e}")
                break
        self.running = False

    def handle_image(self, filename, b64data):
        """Save and display received image"""
        try:
            img_bytes = base64.b64decode(b64data)
            os.makedirs('images', exist_ok=True)
            base, ext = os.path.splitext(filename)
            if not ext:
                ext = '.png'
            new_name = f"{base}_{int(time.time())}{ext}"
            save_path = os.path.join('images', new_name)
            with open(save_path, 'wb') as f:
                f.write(img_bytes)
            print_green(f"[Image received: {save_path}]")
            self.open_image(save_path)
        except Exception as e:
            print_red(f"Error receiving image: {e}")

    def open_image(self, path):
        """Open image with default system viewer"""
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
        except:
            print_red("Could not open image. Please open manually.")

    def send_messages(self):
        """Send user messages"""
        while self.running:
            try:
                msg = input()
                if not msg:
                    continue
                if msg.lower() == '/quit':
                    self.running = False
                    break
                self.sock.sendall((msg + '\n').encode('utf-8'))
            except:
                break

    def start(self):
        if not self.connect():
            return
        if not self.login():
            return
        recv_thread = threading.Thread(target=self.receive_messages)
        recv_thread.daemon = True
        recv_thread.start()
        self.send_messages()
        self.sock.close()

# ====================== Entry Point ======================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Chat Server/Client for BLACK ceo studio')
    parser.add_argument('mode', choices=['server', 'client'], help='Run as server or client')
    parser.add_argument('--host', default='127.0.0.1', help='Server IP address (for client)')
    parser.add_argument('--port', type=int, default=100, help='Port (default 100)')
    args = parser.parse_args()

    if args.mode == 'server':
        server = ChatServer(host='0.0.0.0', port=args.port)
        try:
            server.start()
        except KeyboardInterrupt:
            print("\nServer stopped.")
        except Exception as e:
            print_red(f"Error: {e}")
    else:
        client = ChatClient(host=args.host, port=args.port)
        try:
            client.start()
        except KeyboardInterrupt:
            print("\nExited chat.")
