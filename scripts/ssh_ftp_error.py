#!/usr/bin/env python3
"""
Job 07 — ssh_ftp_error.py

Récupère, dans le log de PSMM-ftp, les tentatives de connexion avec un
compte/mot de passe invalide, et les stocke dans la table partagée
`tentatives_connexion` (créée au Job 06), avec service='ftp'.

Nécessite log_ftp_protocol=YES dans /etc/vsftpd.conf (activé manuellement
avant ce Job) : sans ce réglage, vsftpd ne journalise que les transferts
réussis (format xferlog), jamais les échecs d'authentification.

Usage :
    python3 ssh_ftp_error.py
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

# Exemple de ligne réelle observée dans /var/log/vsftpd.log :
# Mon Sep 21 11:16:13 2026 [pid 2996] [identifiant fake 1] FAIL LOGIN: Client "::ffff:192.168.163.141"
MOTIF_FAIL_LOGIN = re.compile(
    r'^(?P<date_heure>\w{3} \w{3} +\d{1,2} \d{2}:\d{2}:\d{2} \d{4}) '
    r'\[pid \d+\] \[(?P<compte>[^\]]+)\] FAIL LOGIN: Client "(?:::ffff:)?(?P<ip>[\d.]+)"'
)


def convertir_date(chaine: str) -> str:
    """Convertit le format de date vsftpd ('Mon Sep 21 11:16:13 2026')
    vers le format attendu par MySQL ('YYYY-MM-DD HH:MM:SS')."""
    dt = datetime.strptime(chaine, "%a %b %d %H:%M:%S %Y")
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def recuperer_lignes_log(mot_de_passe_sudo: str) -> list[str]:
    """Récupère, via SSH+sudo, les lignes FAIL LOGIN du log vsftpd."""
    commande = "grep 'FAIL LOGIN' /var/log/vsftpd.log"
    sortie, _ = ssh_run_sudo_command("ftp", commande, mot_de_passe_sudo)
    return [ligne for ligne in sortie.splitlines() if ligne.strip()]


def parser_tentatives(lignes: list[str]) -> list[dict]:
    """Extrait compte / ip / date_heure de chaque ligne FAIL LOGIN reconnue."""
    tentatives = []
    for ligne in lignes:
        correspondance = MOTIF_FAIL_LOGIN.match(ligne)
        if correspondance:
            donnees = correspondance.groupdict()
            donnees["date_heure"] = convertir_date(donnees["date_heure"])
            tentatives.append(donnees)
    return tentatives


def creer_table_si_absente(connexion) -> None:
    """Même table que le Job 06 — s'assure qu'elle existe même si ce
    script venait à tourner avant ssh_mysql_error.py."""
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
                VALUES ('ftp', %s, %s, %s)
                """,
                (t["compte"], t["ip"], t["date_heure"]),
            )
    connexion.commit()
    return nb_inserees


if __name__ == "__main__":
    mdp_sudo = getpass.getpass("Mot de passe sudo de monitor sur PSMM-ftp : ")

    print("Récupération du log vsftpd...")
    lignes = recuperer_lignes_log(mdp_sudo)
    print(f"{len(lignes)} ligne(s) 'FAIL LOGIN' trouvée(s).")

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
