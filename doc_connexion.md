# 📡 Documentation de Connexion - Serveur ClassCord

## 🔗 Informations de connexion

- **IP d’accès** : `10.0.108.90` 
- **Port utilisé** : `12345`
- **Protocole** : `TCP`
- **Chemin complet du serveur** : `/home/classcord/Desktop/BTS_SIO/classcord-server/server_classcord.py`

## 🖥️ Schéma réseau

╭────────────╮                  NAT (redir. port) ╭────────────╮
│ Poste SLAM │ ─────────────────────────────────▶ │ Poste SISR │
│ 10.0.108.xx│                                    │ 10.0.108.90│
╰────────────╯                                    │ (Hôte réel)│
                                                  ╰────────────╯
                                                         ▲ 
                                                         │ NAT
                                                         │
                                                         │
                                                  ╭────────────╮
                                                  │ VM Linux   │
                                                  │ 127.0.1.1  │
                                                  │ Port 12345 │
                                                  ╰────────────╯
