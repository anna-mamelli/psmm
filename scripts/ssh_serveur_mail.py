#!/usr/bin/env python3
"""
Job 09 — ssh_serveur_mail.py

Envoie à l'administrateur un mail récapitulant les tentatives de connexion
échouées (MySQL, FTP, Web) de la veille, à partir de la table partagée
`tentatives_connexion` (Jobs 06-08).

Usage :
    python3 ssh_serveur_mail.py               # tentatives d'hier (usage normal, en tâche planifiée)
    python3 ssh_serveur_mail.py 2026-09-21     # tentatives d'une date précise (pratique pour tester
                                                # le jour même, sans attendre le lendemain)
"""

import sys
import os
import smtplib
from email.mime.text import MIMEText
from datetime import date, datetime, timedelta
import pymysql

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config.hosts import MYSQL, MAIL


def recuperer_tentatives(jour: date) -> list[tuple]:
    """Retourne les tentatives du jour donné : (service, compte, ip, date_heure)."""
    connexion = pymysql.connect(
        host=MYSQL["host"], user=MYSQL["user"],
        password=MYSQL["password"], database=MYSQL["database"],
    )
    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT service, compte, adresse_ip, date_heure
                FROM tentatives_connexion
                WHERE DATE(date_heure) = %s
                ORDER BY date_heure
                """,
                (jour,),
            )
            return curseur.fetchall()
    finally:
        connexion.close()


def construire_corps_mail(tentatives: list[tuple], jour: date) -> str:
    """Construit le corps du mail (texte brut) à partir des tentatives du jour."""
    if not tentatives:
        return f"Aucune tentative de connexion échouée enregistrée le {jour}."

    lignes = [f"Tentatives de connexion échouées du {jour} :", ""]
    for service, compte, ip, date_heure in tentatives:
        lignes.append(f"- [{service.upper()}] {date_heure} — compte « {compte} » depuis {ip}")

    lignes.append("")
    lignes.append(f"Total : {len(tentatives)} tentative(s).")
    return "\n".join(lignes)


def envoyer_mail(sujet: str, corps: str) -> None:
    """Envoie le mail via le serveur SMTP configuré dans config/hosts.py."""
    message = MIMEText(corps, "plain", "utf-8")
    message["Subject"] = sujet
    message["From"] = MAIL["sender"]
    message["To"] = MAIL["admin_recipient"]

    with smtplib.SMTP(MAIL["smtp_server"], MAIL["smtp_port"]) as serveur:
        serveur.starttls()
        serveur.login(MAIL["sender"], MAIL["sender_password"])
        serveur.send_message(message)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        jour_cible = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    else:
        jour_cible = date.today() - timedelta(days=1)

    print(f"Récupération des tentatives du {jour_cible}...")
    tentatives = recuperer_tentatives(jour_cible)
    print(f"{len(tentatives)} tentative(s) trouvée(s).")

    corps = construire_corps_mail(tentatives, jour_cible)
    sujet = f"[PSMM] Rapport des tentatives de connexion — {jour_cible}"

    print(f"Envoi du mail à {MAIL['admin_recipient']}...")
    envoyer_mail(sujet, corps)
    print("Mail envoyé.")
