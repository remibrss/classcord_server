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
DISABLED_CHANNELS = set()
LOCK = threading.Lock()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'database', 'classcord.db')

# Logger principal (classcord.log)
logging.basicConfig(
    filename=os.path.join(BASE_DIR, 'classcord.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.info("=== Démarrage du serveur Classcord ===")

# Logger audit dédié (audit.log)
audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.DEBUG)
audit_handler = logging.FileHandler(os.path.join(BASE_DIR, 'audit.log'))
audit_handler.setLevel(logging.DEBUG)
audit_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
audit_handler.setFormatter(audit_formatter)
audit_logger.addHandler(audit_handler)

def log_received_message(address, username, message_type, content):
    audit_logger.info(f"Reçu de '{username}' @ {address} - Type: {message_type} - Contenu: {content}")

def log_error(address, username, error):
    audit_logger.error(f"Erreur avec '{username}' @ {address} - {error}")

def log_system_event(event):
    audit_logger.info(f"[SYSTEM EVENT] {event}")

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
        logging.info(f"[REGISTER] Utilisateur '{username}' enregistré depuis {ip}")
        log_system_event(f"Nouvel utilisateur enregistré: {username} @ {ip}")
        return True
    except sqlite3.IntegrityError:
        logging.warning(f"[REGISTER-ECHEC] Tentative d'inscription avec username existant: '{username}' @ {ip}")
        return False

def validate_login(username, password):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT password FROM credentials WHERE username = ?", (username,))
        row = c.fetchone()
        valid = row and row[0] == password
        logging.info(f"[LOGIN-VALIDATION] Tentative login '{username}': {'réussie' if valid else 'échouée'}")
        return valid

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
        log_system_event(f"Message système envoyé à {to_socket.getpeername()}: {content}")
    except Exception as e:
        logging.warning(f"[ERREUR SYSTEM] Impossible d'envoyer un message système : {e}")
        log_error(to_socket.getpeername(), 'SYSTEM', e)

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
                log_error(client_socket.getpeername(), info['username'], e)

def handle_client(client_socket):
    buffer = ''
    username = None
    address = client_socket.getpeername()
    logging.info(f"[CONNEXION] Nouvelle connexion depuis {address}")
    log_system_event(f"Connexion client depuis {address}")
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
                log_received_message(address, username or 'invité', msg.get('type'), msg.get('content'))

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

                            send_system_message(client_socket, f"Bienvenue {username} sur ClassCord !")

                            broadcast_to_channel({'type': 'status', 'user': username, 'state': 'online'}, client_socket)
                            logging.info(f"[LOGIN] {username} connecté")
                            log_system_event(f"Utilisateur connecté : {username} @ {address}")
                        else:
                            response = {'type': 'error', 'message': 'Login failed.'}
                            client_socket.sendall((json.dumps(response) + '\n').encode())
                            logging.warning(f"[LOGIN-ECHEC] {msg['username']} depuis {address[0]}")
                            log_system_event(f"Échec de login pour {msg['username']} @ {address}")

                elif msg['type'] == 'message':
                    if not username:
                        username = msg.get('from', 'invité')
                        CLIENTS[client_socket] = {"username": username, "channel": DEFAULT_CHANNEL}

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
                        log_system_event(f"{username} a rejoint le canal {new_channel}")
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
                    log_system_event(f"Statut changé : {username} est {msg['state']}")

    except Exception as e:
        logging.warning(f'[ERREUR] Problème avec {address} ({username}): {e}')
        log_error(address, username, e)
    finally:
        if username:
            broadcast_to_channel({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)
            send_system_message(client_socket, f"{username} s'est déconnecté.")
            log_system_event(f"Utilisateur déconnecté : {username} @ {address}")

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
    log_system_event(f"Serveur démarré sur {HOST}:{PORT}")
    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

def get_clients():
    return CLIENTS

def get_lock():
    return LOCK

def get_disabled_channels():
    return DISABLED_CHANNELS

def get_available_channels():
    return AVAILABLE_CHANNELS

if __name__ == '__main__':
    main()
