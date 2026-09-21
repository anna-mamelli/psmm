#!/usr/bin/env python3
"""
Job 08 — ssh_web_error.py

Récupère, dans error.log de PSMM-web, les tentatives d'authentification
basic échouées (compte inexistant OU mauvais mot de passe), et les stocke
dans la table partagée `tentatives_connexion` (Job 06), avec service='web'.

Important : access.log ne suffit pas ici — en cas d'échec d'authentification
basic, Apache y note juste un code 401 sans le nom d'utilisateur tenté.
Le détail (compte, IP, date) n'est disponible que dans error.log.

Usage :
    python3 ssh_web_error.py
"""

import sys
import os
import re
import getpass
from datetime import datetime
import pymysql

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh_login_sudo import ssh_run_sudo_command

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config.hosts import MYSQL

# Deux formats réels observés dans /var/log/apache2/error.log :
# [Mon Sep 21 11:39:09.076258 2026] [auth_basic:error] [pid 4106:tid 4109] [client 192.168.163.141:56172] AH01618: user faux1 not found: /
# [Mon Sep 21 11:41:39.228075 2026] [auth_basic:error] [pid 4105:tid 4126] [client 192.168.163.141:37692] AH01617: user webuser: authentication failure for "/": Password Mismatch
MOTIF_AUTH_ECHEC = re.compile(
    r'^\[(?P<date_heure>[^\]]+)\] \[auth_basic:error\] \[pid \d+:tid \d+\] '
    r'\[client (?P<ip>[\d.]+):\d+\] AH0161[78]: user (?P<compte>.+?)(?: not found|:)'
)


def convertir_date(chaine: str) -> str:
    """Convertit 'Mon Sep 21 11:39:09.076258 2026' (avec microsecondes)
    vers le format MySQL 'YYYY-MM-DD HH:MM:SS'."""
    dt = datetime.strptime(chaine, "%a %b %d %H:%M:%S.%f %Y")
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def recuperer_lignes_log(mot_de_passe_sudo: str) -> list[str]:
    """Récupère, via SSH+sudo, les lignes d'échec d'auth basic dans error.log."""
    commande = "grep 'auth_basic:error' /var/log/apache2/error.log"
    sortie, _ = ssh_run_sudo_command("web", commande, mot_de_passe_sudo)
    return [ligne for ligne in sortie.splitlines() if ligne.strip()]


def parser_tentatives(lignes: list[str]) -> list[dict]:
    """Extrait compte / ip / date_heure de chaque ligne d'échec reconnue."""
    tentatives = []
    for ligne in lignes:
        correspondance = MOTIF_AUTH_ECHEC.match(ligne)
        if correspondance:
            donnees = correspondance.groupdict()
            donnees["date_heure"] = convertir_date(donnees["date_heure"])
            tentatives.append(donnees)
    return tentatives


def creer_table_si_absente(connexion) -> None:
    """Même table que les Jobs 06/07."""
    with connexion.cursor() as curseur:
        curseur.execute(
            """
            CREATE TABLE IF NOT EXISTS tentatives_connexion (
                id INT AUTO_INCREMENT PRIMARY KEY,
                service VARCHAR(10) NOT NULL,
                compte VARCHAR(100) NOT NULL,
                adresse_ip VARCHAR(45) NOT NULL,
                date_heure DATETIME NOT NULL,
                UNIQUE KEY unique_tentative (service, compte, adresse_ip, date_heure)
            )
            """
        )
    connexion.commit()


def enregistrer_tentatives(connexion, tentatives: list[dict]) -> int:
    """Insère en base ; les doublons déjà présents sont ignorés (UNIQUE + INSERT IGNORE)."""
    nb_inserees = 0
    with connexion.cursor() as curseur:
        for t in tentatives:
            nb_inserees += curseur.execute(
                """
                INSERT IGNORE INTO tentatives_connexion (service, compte, adresse_ip, date_heure)
                VALUES ('web', %s, %s, %s)
                """,
                (t["compte"], t["ip"], t["date_heure"]),
            )
    connexion.commit()
    return nb_inserees


if __name__ == "__main__":
    mdp_sudo = getpass.getpass("Mot de passe sudo de monitor sur PSMM-web : ")

    print("Récupération du log Apache (error.log)...")
    lignes = recuperer_lignes_log(mdp_sudo)
    print(f"{len(lignes)} ligne(s) d'échec d'authentification trouvée(s).")

    tentatives = parser_tentatives(lignes)
    print(f"{len(tentatives)} tentative(s) correctement analysée(s).")

    connexion = pymysql.connect(
        host=MYSQL["host"], user=MYSQL["user"],
        password=MYSQL["password"], database=MYSQL["database"],
    )
    try:
        creer_table_si_absente(connexion)
        nb_nouvelles = enregistrer_tentatives(connexion, tentatives)
        print(f"{nb_nouvelles} nouvelle(s) tentative(s) enregistrée(s) en base (doublons ignorés).")
    finally:
        connexion.close()
