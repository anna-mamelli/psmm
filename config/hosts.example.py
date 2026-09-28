"""
Gabarit de configuration PSMM.

Copier ce fichier en `hosts.py` (dans le même dossier) et renseigner les
vraies valeurs. `hosts.py` est gitignoré : ne jamais committer de vrais
identifiants, mots de passe ou clés.

    cp config/hosts.example.py config/hosts.py
"""

# --- Job 01/02 : serveurs cibles et VM sonde -------------------------------
# key_path pointe vers la clé dédiée générée SUR la sonde (Job 02),
# pas vers une clé du PC Windows.
HOSTS = {
    "ftp": {
        "hostname": "192.168.X.X",
        "user": "monitor",
        "key_path": "~/.ssh/psmm_sonde",
    },
    "web": {
        "hostname": "192.168.X.X",
        "user": "monitor",
        "key_path": "~/.ssh/psmm_sonde",
    },
    "sql": {
        "hostname": "192.168.X.X",
        "user": "monitor",
        "key_path": "~/.ssh/psmm_sonde",
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
# L'envoi passe par msmtp (voir doc LIN-SMTP-001), configuré séparément dans
# ~/.msmtprc sur la sonde (compte SMTP, expéditeur, mot de passe d'application).
# Rien de tout ça n'est stocké ici : ~/.msmtprc est protégé en chmod 600,
# et seul le destinataire des rapports est nécessaire côté script.
MAIL = {
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
