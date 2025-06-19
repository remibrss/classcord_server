# SECURITE.md

## Journalisation
Les logs sont stockés dans `/var/log/classcord/classcord.log`. Chaque connexion et erreur y est consignée.

## Fail2Ban
- Fichier de filtre : `/etc/fail2ban/filter.d/classcord.conf`
- Log surveillé : `/var/.../classcord.log`
- Bannissement après 5 tentatives invalides pendant 5 minutes.

## Pare-feu
- Seules les IP du réseau local sont autorisées.(via ufw)

## Sauvegarde
- Fichier `users.pkl` sauvegardé toutes les heures via cron.
