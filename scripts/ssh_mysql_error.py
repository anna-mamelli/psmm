#!/usr/bin/env python3
"""
Job 06 — ssh_mysql_error.py

Récupère, dans le journal système de PSMM-mariadb, les tentatives d'accès
avec un compte/mot de passe invalide, et les stocke dans la base psmm_logs
(table partagée `tentatives_connexion`, réutilisée aux Jobs 07/08 pour FTP
et Web).

Sur Debian, MariaDB journalise ses avertissements ("Access denied for
user...") dans le journal systemd (journalctl -u mariadb), pas dans un
fichier /var/log/mysql/error.log comme on pourrait s'y attendre par défaut
— vérifié par observation directe avant d'écrire ce script.

Usage :
    python3 ssh_mysql_error.py
"""

import sys
import os
import re
import getpass
import pymysql

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh_login_sudo import ssh_run_sudo_command

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config.hosts import MYSQL

# Exemple de ligne réelle observée (sortie de "journalctl -u mariadb -o cat") :
# 2026-09-21 10:48:12 33 [Warning] Access denied for user 'faux_user1'@'192.168.163.141'
MOTIF_ACCES_REFUSE = re.compile(
    r"^(?P<date_heure>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) "
    r"\d+ \[Warning\] Access denied for user '(?P<compte>[^']+)'@'(?P<ip>[^']+)'"
)


def recuperer_lignes_journal(mot_de_passe_sudo: str) -> list[str]:
    """Récupère, via SSH+sudo, les lignes 'Access denied' du journal MariaDB."""
    commande = "journalctl -u mariadb --no-pager -o cat | grep 'Access denied for user'"
    sortie, _ = ssh_run_sudo_command("sql", commande, mot_de_passe_sudo)
    return [ligne for ligne in sortie.splitlines() if ligne.strip()]


def parser_tentatives(lignes: list[str]) -> list[dict]:
    """Extrait compte / ip / date_heure de chaque ligne d'échec reconnue."""
    tentatives = []
    for ligne in lignes:
        correspondance = MOTIF_ACCES_REFUSE.match(ligne)
        if correspondance:
            tentatives.append(correspondance.groupdict())
    return tentatives


def creer_table_si_absente(connexion) -> None:
    """Crée la table partagée des tentatives (mysql/ftp/web) si elle n'existe pas."""
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
    """Insère les tentatives en base ; les doublons déjà présents sont ignorés
    grâce à la contrainte UNIQUE (INSERT IGNORE), ce qui permet de relancer
    ce script plusieurs fois sans créer de lignes en double."""
    nb_inserees = 0
    with connexion.cursor() as curseur:
        for t in tentatives:
            nb_inserees += curseur.execute(
                """
                INSERT IGNORE INTO tentatives_connexion (service, compte, adresse_ip, date_heure)
                VALUES ('mysql', %s, %s, %s)
                """,
                (t["compte"], t["ip"], t["date_heure"]),
            )
    connexion.commit()
    return nb_inserees


if __name__ == "__main__":
    mdp_sudo = getpass.getpass("Mot de passe sudo de monitor sur PSMM-mariadb : ")

    print("Récupération du journal MariaDB...")
    lignes = recuperer_lignes_journal(mdp_sudo)
    print(f"{len(lignes)} ligne(s) 'Access denied' trouvée(s) dans le journal.")

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
