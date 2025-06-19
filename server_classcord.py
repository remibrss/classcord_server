import socket
import threading
import json
import pickle
import os
import logging
from datetime import datetime

HOST = '0.0.0.0'
PORT = 12345

USER_FILE = 'users.pkl'
CLIENTS = {}  # socket: username
USERS = {}    # username: password
LOCK = threading.Lock()

logging.basicConfig(
    filename='/home/classcord/Desktop/BTS_SIO/classcord-server-perso/classcord.log',  # ← chemin absolu
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logging.info("=== Démarrage du serveur Classcord ===")

def load_users():
    global USERS
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'rb') as f:
            USERS = pickle.load(f)
    logging.info(f"[INIT] Utilisateurs chargés: {list(USERS.keys())}")

def save_users():
    with open(USER_FILE, 'wb') as f:
        pickle.dump(USERS, f)
    logging.info("[SAVE] Utilisateurs sauvegardés.")

def broadcast(message, sender_socket=None):
    for client_socket, username in CLIENTS.items():
        if client_socket != sender_socket:
            try:
                client_socket.sendall((json.dumps(message) + '\n').encode())
                logging.info(f"[ENVOI] Message envoyé à {username} : {message}")
            except Exception as e:
                logging.info(f"[ERREUR] Échec d'envoi à {username} : {e}")

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
                        if msg['username'] in USERS:
                            response = {'type': 'error', 'message': 'Username already exists.'}
                        else:
                            USERS[msg['username']] = msg['password']
                            save_users()
                            response = {'type': 'register', 'status': 'ok'}
                        client_socket.sendall((json.dumps(response) + '\n').encode())

                elif msg['type'] == 'login':
                    with LOCK:
                        if USERS.get(msg['username']) == msg['password']:
                            username = msg['username']
                            CLIENTS[client_socket] = username
                            response = {'type': 'login', 'status': 'ok'}
                            client_socket.sendall((json.dumps(response) + '\n').encode())
                            broadcast({'type': 'status', 'user': username, 'state': 'online'}, client_socket)
                            logging.info(f"[LOGIN] {username} connecté")
                        else:
                            response = {'type': 'error', 'message': 'Login failed.'}
                            client_socket.sendall((json.dumps(response) + '\n').encode())
                            ip = address[0]
                            logging.warning(f"[LOGIN-ECHEC] Tentative échouée pour {msg['username']} depuis {ip}")

                elif msg['type'] == 'message':
                    if not username:
                        username = msg.get('from', 'invité')
                        with LOCK:
                            CLIENTS[client_socket] = username
                        logging.info(f"[INFO] Connexion invitée détectée : {username}")

                    msg['from'] = username
                    msg['timestamp'] = datetime.now().isoformat()
                    logging.info(f"[MSG] {username} >> {msg['content']}")
                    broadcast(msg, client_socket)

                elif msg['type'] == 'status' and username:
                    broadcast({'type': 'status', 'user': username, 'state': msg['state']}, client_socket)
                    logging.info(f"[STATUS] {username} est maintenant {msg['state']}")

    except Exception as e:
        logging.info(f'[ERREUR] Problème avec {address} ({username}):', e)
    finally:
        if username:
            broadcast({'type': 'status', 'user': username, 'state': 'offline'}, client_socket)
        with LOCK:
            CLIENTS.pop(client_socket, None)
        client_socket.close()
        logging.info(f"[DECONNEXION] {address} déconnecté")

def main():
    load_users()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    logging.info(f"[DEMARRAGE] Serveur en écoute sur {HOST}:{PORT}")
    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == '__main__':
    main()
