# PSMM — Centralisation des protocoles de gestion d'erreurs

> Rapport du Commandeur Data — Sous-système PSMM (Python, Shell, MariaDB, Mail)
> Bachelor Administrateur Systèmes et Réseaux — La Plateforme_

## 1. Objectif

Récupérer les logs des serveurs FTP, Web et SQL, archiver les tentatives d'accès avec un
compte / mot de passe invalide dans une base MariaDB, superviser l'état système des serveurs,
et alerter automatiquement l'administrateur (mail quotidien, alertes de seuil, Google Chat).

## 2. Architecture

### VM cibles (Job 01)

| VM | Rôle | RAM | vCPU | Disque |
|---|---|---|---|---|
| `PSSM_ftp` | Serveur FTP | 1 Go | 1 | 8 Go |
| `PSSM_web` | Apache/Nginx + site en auth basic | 1 Go | 1 | 8 Go |
| `PSSM_mariadb` | Serveur MariaDB | 2 Go | 2 | 8 Go |

Contraintes communes aux trois VM :
- Pas d'accès SSH au compte `root`
- Seul le compte `monitor` peut se connecter en SSH, authentification **par clé SSH uniquement**
- `monitor` fait partie du groupe `sudo`

> ⚠️ L'énoncé nomme le sous-système « PSMM » mais demande un préfixe de VM « PSSM_ » —
> conservé tel quel, comme indiqué dans le sujet.

### VM sonde (Job 02)

VM Debian **sans interface graphique**, qui exécute tous les scripts `ssh_*.py` :
- Python 3
- Client MySQL/MariaDB (pas le serveur)
- Client FTP en CLI
- Bibliothèque d'envoi de mail (`smtplib`)

Nom proposé : `PSSM_monitor` (à ajuster selon convention retenue).

## 3. Feuille de route

| Phase | Job(s) | Script | Objet | Statut |
|---|---|---|---|---|
| 0 — Infra | 01, 02 | — | 3 VM cibles + VM sonde, compte `monitor` + clé SSH + sudo | ☐ |
| 1 — Connexion | 03 | `ssh_login.py` | Connexion SSH + commande shell simple | ☐ |
| 1 — Connexion | 04 | `ssh_login_sudo.py` | Idem en mode sudo | ☐ |
| 1 — Connexion | 05 | `ssh_mysql.py` | Vérification de l'accès au serveur MariaDB | ☐ |
| 2 — Collecte logs | 06 | `ssh_mysql_error.py` | Échecs d'auth MariaDB → base SQL | ☐ |
| 2 — Collecte logs | 07 | `ssh_ftp_error.py` | Échecs d'auth FTP → base SQL | ☐ |
| 2 — Collecte logs | 08 | `ssh_web_error.py` | Échecs d'auth Web → base SQL | ☐ |
| 3 — Alerte & sauvegarde | 09 | `ssh_serveur_mail.py` | Mail quotidien (historique de la veille) | ☐ |
| 3 — Alerte & sauvegarde | 10 | `ssh_cron_backup.py` | Backup horodaté, rétention 7, cron 3h | ☐ |
| 4 — Supervision | 11 | `ssh_system_status.py` | Relevé RAM/CPU/DISK, rétention 72h | ☐ |
| 4 — Supervision | 12 | `ssh_system_mail.py` | Alerte mail si seuils dépassés (cron 5 min) | ☐ |
| 4 — Supervision | 13 | `ssh_system_mail.py` (maj) | Anti-spam : 1 mail max / heure | ☐ |
| 5 — Maintenance | 14 | `ssh_update.py` | MAJ serveurs via Alcasar + check reboot | ☐ |
| 6 — Bonus | 15 | `ssh_chat_notify.py` | Notifications Google Chat Space | ☐ |

## 4. Structure du dépôt

```
psmm/
├── README.md
├── .gitignore
├── docs/                      # procédures VM, captures d'écran, notes de soutenance
├── config/
│   └── hosts.example.py       # gabarit de config — à copier en hosts.py (gitignoré)
└── scripts/
    ├── ssh_login.py
    ├── ssh_login_sudo.py
    ├── ssh_mysql.py
    ├── ssh_mysql_error.py
    ├── ssh_ftp_error.py
    ├── ssh_web_error.py
    ├── ssh_serveur_mail.py
    ├── ssh_cron_backup.py
    ├── ssh_system_status.py
    ├── ssh_system_mail.py
    ├── ssh_update.py
    └── ssh_chat_notify.py
```

## 5. Configuration

Toutes les infos de connexion (IP, utilisateurs, mots de passe, seuils, webhook) sont centralisées
dans `config/hosts.py`, à créer à partir du gabarit :

```bash
cp config/hosts.example.py config/hosts.py
# puis éditer config/hosts.py avec les vraies valeurs
```

`config/hosts.py` est gitignoré : il ne doit **jamais** être poussé sur le dépôt public.

## 6. Sécurité

- Aucun mot de passe, clé privée ou secret en dur dans les scripts versionnés
- `config/hosts.py`, clés SSH et fichiers `.env` sont dans `.gitignore`
- Les comptes utilisés pour générer volontairement des échecs d'authentification (Jobs 06-08)
  doivent être des comptes de test dédiés, distincts des comptes d'administration réels
- Seuils d'alerte (Job 12) centralisés dans `config/hosts.py`, modifiables sans toucher au code

## 7. Rendu

- Dépôt : https://github.com/anna-mamelli/psmm
- Évaluation : présentation avec support à l'équipe pédagogique
