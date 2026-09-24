#!/usr/bin/env python3
"""
Job 11 — ssh_system_status.py

Récupère l'utilisation CPU/RAM/Disque des serveurs surveillés (ftp, web, sql)
via SSH, les enregistre dans une table dédiée `etat_systeme`, et purge les
lignes plus anciennes que SYSTEM_STATUS_RETENTION_HOURS (72h par défaut).

Conçu pour tourner en tâche planifiée (cron), par exemple toutes les 5
minutes, en cohérence avec le Job 12 à venir qui s'appuiera sur ces données
pour générer des alertes mail.

Usage :
    python3 ssh_system_status.py
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config.hosts import HOSTS, MYSQL, SYSTEM_STATUS_RETENTION_HOURS
from ssh_login import ssh_run_command
import pymysql

# Une seule commande shell par serveur : calcule CPU/RAM/Disque et les
# renvoie sur une ligne, séparés par '|'. LC_ALL=C évite tout souci de
# décimales locales (virgule vs point) sur le CPU/RAM.
COMMANDE_METRIQUES = (
    "export LC_ALL=C; "
    "CPU_IDLE=$(top -bn1 | grep '%Cpu(s)' | grep -oP '\\d+\\.\\d+(?= id)'); "
    "RAM=$(free | awk '/Mem:/ {printf \"%.2f\", ($3/$2)*100}'); "
    "DISK=$(df / | awk 'NR==2 {gsub(\"%\",\"\",$5); print $5}'); "
    "echo \"${CPU_IDLE}|${RAM}|${DISK}\""
)


def creer_table_si_absente(curseur) -> None:
    curseur.execute(
        """
        CREATE TABLE IF NOT EXISTS etat_systeme (
            id INT AUTO_INCREMENT PRIMARY KEY,
            serveur VARCHAR(20) NOT NULL,
            cpu_percent DECIMAL(5,2) NOT NULL,
            ram_percent DECIMAL(5,2) NOT NULL,
            disk_percent DECIMAL(5,2) NOT NULL,
            date_heure DATETIME NOT NULL
        )
        """
    )


def recuperer_metriques(cible: str) -> tuple[float, float, float]:
    """Exécute la commande de collecte sur le serveur cible, retourne (cpu, ram, disk) en %."""
    sortie, erreur = ssh_run_command(cible, COMMANDE_METRIQUES)
    idle_str, ram_str, disk_str = sortie.strip().split("|")
    cpu_percent = 100 - float(idle_str)  # on mesure l'inverse de l'inactivité
    ram_percent = float(ram_str)
    disk_percent = float(disk_str)
    return cpu_percent, ram_percent, disk_percent


def enregistrer_etat(curseur, serveur: str, cpu: float, ram: float, disk: float) -> None:
    curseur.execute(
        """
        INSERT INTO etat_systeme (serveur, cpu_percent, ram_percent, disk_percent, date_heure)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (serveur, cpu, ram, disk, datetime.now()),
    )


def purger_anciennes_lignes(curseur) -> int:
    """Supprime les lignes plus vieilles que SYSTEM_STATUS_RETENTION_HOURS. Retourne le nb supprimé."""
    curseur.execute(
        "DELETE FROM etat_systeme WHERE date_heure < NOW() - INTERVAL %s HOUR",
        (SYSTEM_STATUS_RETENTION_HOURS,),
    )
    return curseur.rowcount


if __name__ == "__main__":
    connexion = pymysql.connect(
        host=MYSQL["host"], user=MYSQL["user"],
        password=MYSQL["password"], database=MYSQL["database"],
    )
    try:
        with connexion.cursor() as curseur:
            creer_table_si_absente(curseur)

            for serveur in HOSTS:
                print(f"Collecte des métriques sur '{serveur}'...")
                cpu, ram, disk = recuperer_metriques(serveur)
                print(f"  CPU={cpu:.2f}%  RAM={ram:.2f}%  Disque={disk:.2f}%")
                enregistrer_etat(curseur, serveur, cpu, ram, disk)

            connexion.commit()

            supprimees = purger_anciennes_lignes(curseur)
            connexion.commit()
            print(f"Purge : {supprimees} ligne(s) de plus de {SYSTEM_STATUS_RETENTION_HOURS}h supprimée(s).")
    finally:
        connexion.close()
