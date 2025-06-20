import socket
import threading
import json
import os
import logging
import sqlite3
from datetime import datetime

HOST = '0.0.0.0'
PORT = 12345
CLIENTS = {}  # socket: {"username": ..., "channel": ...}
DEFAULT_CHANNEL = "#général"
AVAILABLE_CHANNELS = {"#général", "#admin", "#dev"}
LOCK = threading.Lock()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'database', 'classcord.db')


logging.basicConfig(
    filename='classcord.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logging.info("=== Démarrage du serveur Classcord ===")

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'online',
                ip TEXT,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                receiver TEXT,
                channel TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                username TEXT PRIMARY KEY,
                password TEXT
            )
        ''')
        conn.commit()

def register_user(username, password, ip):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (username, ip) VALUES (?, ?)", (username, ip))
            c.execute("INSERT INTO credentials (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def validate_login(username, password):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT password FROM credentials WHERE username = ?", (username,))
        row = c.fetchone()
        return row and row[0] == password

def save_message(sender, receiver, channel, content):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO messages (sender, receiver, channel, content)
            VALUES (?, ?, ?, ?)
        ''', (sender, receiver, channel, content))
        conn.commit()

def send_system_message(to_socket, content):
    message = {
        'type': 'system',
        'from': 'server',
        'content': content,
        'timestamp': datetime.now().isoformat()
    }
    try:
        to_socket.sendall((json.dumps(message) + '\n').encode())
        logging.info(f"[SYSTEM] Message envoyé à {to_socket.getpeername()}: {content}")
    except Exception as e:
        logging.warning(f"[ERREUR SYSTEM] Impossible d'envoyer un message système : {e}")

def broadcast_to_channel(message, sender_socket=None):
    sender_info = CLIENTS.get(sender_socket, {})
    channel = sender_info.get("channel", DEFAULT_CHANNEL)

    for client_socket, info in CLIENTS.items():
        if info["channel"] == channel and client_socket != sender_socket:
            try:
                client_socket.sendall((json.dumps(message) + '\n').encode())
                logging.info(f"[ENVOI] {info['username']} sur {channel} : {message}")
            except Exception as e:
                logging.warning(f"[ERREUR] Envoi échoué à {info['username']} : {e}")

def handle_client(client_socket):
    buffer = ''
    username = None
    address = client_socket.getpeername()
    logging.info(f"[CONNEXION] Nouvelle connexion depuis {address}")
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                logging.info(f"[RECU] {address} >> {line}")
                msg = json.loads(line)

                if msg['type'] == 'register':
                    with LOCK:
                        success = register_user(msg['username'], msg['password'], address[0])
                    if success:
                        response = {'type': 'register', 'status': 'ok'}
                    else:
                        response = {'type': 'error', 'message': 'Username already exists.'}
                    client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg['type'] == 'login':
                    with LOCK:
                        if validate_login(msg['username'], msg['password']):
                            username = msg['username']
                            CLIENTS[client_socket] = {"username": username, "channel": DEFAULT_CHANNEL}
                            response = {'type': 'login', 'status': 'ok'}
                            client_socket.sendall((json.dumps(response) + '\n').encode())

                            # Message système de bienvenue pour ce client uniquement
                            send_system_message(client_socket, f"Bienvenue {username} sur ClassCord !")

                            broadcast_to_channel({'type': 'status', 'user': username, 'state': 'online'}, client_socket)
                            logging.info(f"[LOGIN] {username} connecté")
                        else:
                            response = {'type': 'error', 'message': 'Login failed.'}
                            client_socket.sendall((json.dumps(response) + '\n').encode())
                            logging.warning(f"[LOGIN-ECHEC] {msg['username']} depuis {address[0]}")

                elif msg['type'] == 'message':
                    if not username:
                        username = msg.get('from', 'invité')
                        CLIENTS[client_socket] = {"username": username, "channel": DEFAULT_CHANNEL}

                    # Commande de changement de canal
                    if msg['content'].startswith('/join'):
                        parts = msg['content'].split()
                        if len(parts) < 2:
                            response = {'type': 'error', 'message': 'Usage: /join #nom_canal'}
                            client_socket.sendall((json.dumps(response) + '\n').encode())
                            continue
                        new_channel = parts[1]
                        if new_channel not in AVAILABLE_CHANNELS:
                            response = {'type': 'error', 'message': f'Canal {new_channel} inexistant.'}
                            client_socket.sendall((json.dumps(response) + '\n').encode())
                            continue
                        CLIENTS[client_socket]['channel'] = new_channel
                        response = {
                            'type': 'system',
                            'from': 'server',
                            'channel': new_channel,
                            'content': f"{username} a rejoint le canal {new_channel}",
                            'timestamp': datetime.now().isoformat()
                        }
                        broadcast_to_channel(response)
                        logging.info(f"[CHAN] {username} a rejoint {new_channel}")
                    else:
                        channel = CLIENTS[client_socket]['channel']
                        msg['from'] = username
                        msg['channel'] = channel
                        msg['timestamp'] = datetime.now().isoformat()

                        save_message(sender=username, receiver=None, channel=channel, content=msg['content'])
                        logging.info(f"[MSG] {username} ({channel}) >> {msg['content']}")
                        broadcast_to_channel(msg, client_socket)

                elif msg['type'] == 'status' and username:
                    broadcast_to_channel({'type': 'status', 'user': username, 'state': msg['state']}, client_socket)
                    logging.info(f"[STATUS] {username} est maintenant {msg['state']}")

    except Exception as e:
        logging.warning(f'[ERREUR] Problème avec {address} ({username}): {e}')
    finally:
        if username:
            broadcast_to_channel({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)

            # Message système de déconnexion pour ce client uniquement
            send_system_message(client_socket, f"{username} s'est déconnecté.")

        with LOCK:
            CLIENTS.pop(client_socket, None)
        client_socket.close()
        logging.info(f"[DECONNEXION] {address} déconnecté")

def main():
    init_db()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    logging.info(f"[DEMARRAGE] Serveur en écoute sur {HOST}:{PORT}")
    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == '__main__':
    main()

