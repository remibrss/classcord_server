import os
from server_classcord import get_clients, get_lock, get_disabled_channels, get_available_channels

CLIENTS = get_clients()
LOCK = get_lock()
DISABLED_CHANNELS = get_disabled_channels()
AVAILABLE_CHANNELS = get_available_channels()

def afficher_clients():
    os.system('clear')
    print("=== Utilisateurs connectés ===")
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
    for canal in sorted(AVAILABLE_CHANNELS):
        statut = "DÉSACTIVÉ" if canal in DISABLED_CHANNELS else "ACTIF"
        print(f"- {canal} : {statut}")

    choix = input("\nNom du canal à modifier (#...): ").strip()
    if choix not in AVAILABLE_CHANNELS:
        print("Canal inconnu.")
    elif choix in DISABLED_CHANNELS:
        DISABLED_CHANNELS.remove(choix)
        print(f"✅ Canal {choix} activé.")
    else:
        DISABLED_CHANNELS.add(choix)
        print(f"❌ Canal {choix} désactivé.")
    input("Appuyez sur Entrée pour continuer.")

def envoyer_alerte_globale():
    print("=== Envoyer une alerte globale ===")
    message = input("Contenu de l'alerte: ").strip()
    with LOCK:
        for sock in CLIENTS:
            try:
                sock.sendall((f'{{"type": "system", "from": "admin", "content": "{message}"}}\n').encode())
            except Exception as e:
                print(f"Erreur lors de l'envoi à un client: {e}")
    input("Alerte envoyée. Appuyez sur Entrée pour continuer.")

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

