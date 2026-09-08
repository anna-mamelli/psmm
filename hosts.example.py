"""
Gabarit de configuration PSMM.

Copier ce fichier en `hosts.py` (dans le même dossier) et renseigner les
vraies valeurs. `hosts.py` est gitignoré : ne jamais committer de vrais
identifiants, mots de passe ou clés.

    cp config/hosts.example.py config/hosts.py
"""

# --- Job 01/02 : serveurs cibles et VM sonde -------------------------------
HOSTS = {
    "ftp": {
        "hostname": "192.168.X.X",
        "user": "monitor",
        "key_path": "~/.ssh/id_ed25519",
    },
    "web": {
        "hostname": "192.168.X.X",
        "user": "monitor",
        "key_path": "~/.ssh/id_ed25519",
    },
    "sql": {
        "hostname": "192.168.X.X",
        "user": "monitor",
        "key_path": "~/.ssh/id_ed25519",
    },
}

# --- Job 05/06 : accès MariaDB ----------------------------------------------
MYSQL = {
    "host": "192.168.X.X",  # = HOSTS["sql"]["hostname"]
    "user": "psmm_app",
    "password": "CHANGE_ME",
    "database": "psmm_logs",
}

# --- Job 09/12 : envoi de mail -----------------------------------------------
MAIL = {
    "smtp_server": "smtp.example.com",
    "smtp_port": 587,
    "sender": "psmm-monitor@example.com",
    "sender_password": "CHANGE_ME",
    "admin_recipient": "admin@example.com",
}

# --- Job 12 : seuils d'alerte système (modifiables librement) --------------
THRESHOLDS = {
    "cpu_percent": 70,
    "disk_percent": 90,
    "ram_percent": 80,
}

# --- Job 13 : anti-spam des alertes ------------------------------------------
ALERT_RATE_LIMIT_SECONDS = 3600  # 1 mail maximum par heure

# --- Job 10 : sauvegardes ----------------------------------------------------
BACKUP = {
    "retention_count": 7,
    "backup_dir": "/home/monitor/backups",
}

# --- Job 11 : rétention des métriques système --------------------------------
SYSTEM_STATUS_RETENTION_HOURS = 72

# --- Job 14 : mise à jour via Alcasar ----------------------------------------
ALCASAR = {
    "hostname": "alcasar.local",
    "user": "CHANGE_ME",
    "password": "CHANGE_ME",
}

# --- Job 15 : notification Google Chat ---------------------------------------
GOOGLE_CHAT_WEBHOOK = "CHANGE_ME"
