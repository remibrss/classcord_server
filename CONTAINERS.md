# CONTAINERS.md

## 🐳 Pourquoi Docker ?

Docker permet d’emballer le serveur ClassCord dans un environnement portable, reproductible et indépendant de la machine hôte. Cela présente plusieurs avantages :

- Le serveur fonctionne toujours de la même manière, quel que soit le système hôte.
- Plus besoin de configurer manuellement Python ou les dépendances.
- Il peut être redéployé sur une autre machine ou dans le cloud.
- Il est facile à lancer, arrêter et maintenir.

> Dans notre cas, Docker est utilisé **dans la VM Linux** car :
> - Le système hôte (Windows/macOS) n’est pas homogène.
> - Le projet doit rester entièrement sous Linux.
> - Le réseau pédagogique impose une redirection NAT depuis l’hôte vers la VM.

---

## 🛠️ Comment build, run

### Construction de l'image

```bash
docker build -t classcord-server .

## 🌐 Ports à exposer

Le serveur ClassCord fonctionne sur le port **12345**. Ce port doit être configuré et exposé à tous les niveaux :

- **Dans Docker** :
  - Dans le `Dockerfile` : `EXPOSE 12345`
  - Avec `docker run` : `-p 12345:12345`
  - Ou dans `docker-compose.yml` :
    ```yaml
    ports:
      - "12345:12345"
    ```

- **Dans la VM Linux** :
  - Autoriser le port avec le pare-feu :
    ```bash
    sudo ufw allow 12345/tcp
    ```

- **Au niveau de l’hôte réel (Poste SISR)** :
  - Une règle **NAT** doit rediriger le port 12345 vers la VM

---

## 🖥️ Spécificités réseau avec VM + NAT

Dans l’environnement pédagogique :

- La **VM** est en réseau NAT 
- L’**IP visible par le SLAM** est celle de l’hôte réel 
- Une **redirection NAT** est mise en place sur l’hôte pour rediriger le port 12345 vers la VM

### Schéma réseau
╭────────────╮         NAT (port 12345)       ╭────────────╮
│ Poste SLAM │ ─────────────────────────────▶ │ Poste SISR │
│ 10.0.108.X │                                │ 10.0.108.X │
╰────────────╯                                │     ▲      │
                                              │     │ NAT  │
                                              │     ▼      │
                                              │  VM Linux  │
                                              │ 192.168.x  │
                                              ╰────────────╯


