#!/usr/bin/env python3
"""
Job 05 — ssh_mysql.py

Vérifie l'accès direct au serveur MariaDB depuis la sonde, via `pymysql`
(connexion réseau directe au port 3306, indépendante de SSH — contrairement
aux Jobs 03/04 qui passaient par paramiko).

Usage :
    python3 ssh_mysql.py
"""

import sys
import os
import pymysql

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config.hosts import MYSQL


def verifier_acces() -> None:
    """Se connecte à MariaDB et affiche la version + les tables existantes."""
    connexion = pymysql.connect(
        host=MYSQL["host"],
        user=MYSQL["user"],
        password=MYSQL["password"],
        database=MYSQL["database"],
    )
    try:
        with connexion.cursor() as curseur:
            curseur.execute("SELECT VERSION();")
            version = curseur.fetchone()[0]
            print(f"Connexion réussie à MariaDB {version} sur {MYSQL['host']}")

            curseur.execute("SHOW TABLES;")
            tables = [ligne[0] for ligne in curseur.fetchall()]
            print(f"Tables dans '{MYSQL['database']}' : {tables or 'aucune pour le moment'}")
    finally:
        connexion.close()


if __name__ == "__main__":
    verifier_acces()
