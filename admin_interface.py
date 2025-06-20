import os
from server_classcord import get_clients, get_lock, get_disabled_channels, get_available_channels
from datetime import datetime
import json
import logging

CLIENTS = get_clients()
LOCK = get_lock()
DISABLED_CHANNELS = get_disabled_channels()
AVAILABLE_CHANNELS = get_available_channels()

logging.basicConfig(
    filename='classcord.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

import logging
audit_logger = logging.getLogger('audit')
audit_handler = logging.FileHandler('audit.log')
audit_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
audit_handler.setFormatter(formatter)
audit_logger.addHandler(audit_handler)

def afficher_clients():
    os.system('clear')
    print("=== Utilisateurs connectés ===")
    clients = get_clients()
    lock = get_lock()
    with LOCK:
        if not CLIENTS:
            print("Aucun utilisateur connecté.")
        else:
            for sock, info in CLIENTS.items():
                try:
                    addr = sock.getpeername()
                except:
                    addr = "?"
                print(f"- {info['username']} (canal: {info['channel']}, IP: {addr})")
    input("\nAppuyez sur Entrée pour revenir au menu.")

def afficher_statut_canaux():
    os.system('clear')
    print("=== Statut des canaux ===")
    for canal in sorted(AVAILABLE_CHANNELS):
        statut = "DÉSACTIVÉ" if canal in DISABLED_CHANNELS else "ACTIF"
        print(f"- {canal} : {statut}")
    input("\nAppuyez sur Entrée pour revenir au menu.")

def modifier_etat_canal():
    os.system('clear')
    print("=== Activer/Désactiver un canal ===")
    disabled = get_disabled_channels()
    available = get_available_channels()
    lock = get_lock()
    with lock:
        for canal in sorted(available):
            statut = "DÉSACTIVÉ" if canal in disabled else "ACTIF"
            print(f"- {canal} : {statut}")

    choix = input("\nNom du canal à modifier (#...): ").strip()
    if choix not in available:
        print("Canal inconnu.")
    else:
        with lock:
            if choix in disabled:
                disabled.remove(choix)
                print(f"✅ Canal {choix} activé.")
            else:
                disabled.add(choix)
                print(f"❌ Canal {choix} désactivé.")
    input("Appuyez sur Entrée pour continuer.")


def envoyer_alerte_globale():
    message = input("Message d'alerte à envoyer à TOUS les canaux : ")
    alert = {
        "type": "message",
        "from": "admin",
        "channel": "ALL",
        "content": f"[ALERTE GLOBALE] {message}",
        "timestamp": datetime.now().isoformat()
    }

    if not CLIENTS:
        print("[INFO] Aucun client connecté.")
        input("Appuyez sur Entrée pour revenir au menu.")
        return

    for sock in list(CLIENTS.keys()):
        try:
            sock.sendall((json.dumps(alert) + '\n').encode())
            print(f"[OK] Alerte envoyée à {CLIENTS[sock]['username']}")
        except Exception as e:
            print(f"[ERREUR] Envoi échoué vers {CLIENTS[sock]['username']} : {e}")

    logging.info(f"[ALERTE GLOBALE] {message}")
    audit_logger.info(f"[ALERTE GLOBALE] {message}")

def menu():
    while True:
        os.system('clear')
        print("""
===== Interface d'administration Classcord =====

1. Voir les utilisateurs connectés
2. Voir le statut des canaux
3. Activer / Désactiver un canal
4. Envoyer une alerte globale
5. Quitter
""")
        choix = input("Choix: ").strip()
        if choix == '1':
            afficher_clients()
        elif choix == '2':
            afficher_statut_canaux()
        elif choix == '3':
            modifier_etat_canal()
        elif choix == '4':
            envoyer_alerte_globale()
        elif choix == '5':
            print("Fermeture de l'interface admin.")
            break
        else:
            input("Choix invalide. Appuyez sur Entrée.")

if __name__ == "__main__":
    menu()

