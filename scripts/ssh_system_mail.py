#!/usr/bin/env python3
"""
Job 12 — ssh_system_mail.py

Vérifie, pour chaque serveur surveillé, la dernière ligne enregistrée dans
`etat_systeme` (Job 11) et alerte l'administrateur par mail si un seuil
défini dans THRESHOLDS (config/hosts.py) est dépassé : CPU, RAM ou disque.

L'envoi passe par msmtp (même méthode que le Job 09).

Conçu pour tourner en tâche planifiée toutes les 5 minutes, juste après le
Job 11 (pour lire une donnée fraîche).

Usage :
    python3 ssh_system_mail.py
"""

import sys
import os
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config.hosts import MYSQL, MAIL, THRESHOLDS
import pymysql


def recuperer_dernier_etat_par_serveur() -> list[tuple]:
    """Retourne la dernière ligne de etat_systeme pour chaque serveur distinct."""
    connexion = pymysql.connect(
        host=MYSQL["host"], user=MYSQL["user"],
        password=MYSQL["password"], database=MYSQL["database"],
    )
    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT e.serveur, e.cpu_percent, e.ram_percent, e.disk_percent, e.date_heure
                FROM etat_systeme e
                INNER JOIN (
                    SELECT serveur, MAX(date_heure) AS derniere
                    FROM etat_systeme
                    GROUP BY serveur
                ) dernier
                ON e.serveur = dernier.serveur AND e.date_heure = dernier.derniere
                """
            )
            return curseur.fetchall()
    finally:
        connexion.close()


def detecter_depassements(etats: list[tuple]) -> list[str]:
    """Compare chaque serveur aux seuils configurés, retourne une liste de lignes d'alerte."""
    alertes = []
    for serveur, cpu, ram, disk, date_heure in etats:
        if cpu > THRESHOLDS["cpu_percent"]:
            alertes.append(f"- [{serveur.upper()}] CPU à {cpu:.2f} % (seuil : {THRESHOLDS['cpu_percent']} %) — relevé le {date_heure}")
        if disk > THRESHOLDS["disk_percent"]:
            alertes.append(f"- [{serveur.upper()}] Disque à {disk:.2f} % (seuil : {THRESHOLDS['disk_percent']} %) — relevé le {date_heure}")
        if ram > THRESHOLDS["ram_percent"]:
            alertes.append(f"- [{serveur.upper()}] RAM à {ram:.2f} % (seuil : {THRESHOLDS['ram_percent']} %) — relevé le {date_heure}")
    return alertes


def envoyer_mail(sujet: str, corps: str) -> None:
    """Envoie le mail via msmtp (compte 'gmail' configuré par défaut dans ~/.msmtprc)."""
    destinataire = MAIL["admin_recipient"]
    contenu = f"To: {destinataire}\nSubject: {sujet}\n\n{corps}"

    resultat = subprocess.run(
        ["msmtp", destinataire],
        input=contenu, text=True, capture_output=True,
    )
    if resultat.returncode != 0:
        raise RuntimeError(f"Échec de l'envoi via msmtp (code {resultat.returncode}) : {resultat.stderr}")


if __name__ == "__main__":
    print("Lecture du dernier état de chaque serveur...")
    etats = recuperer_dernier_etat_par_serveur()
    print(f"{len(etats)} serveur(s) trouvé(s) dans etat_systeme.")

    alertes = detecter_depassements(etats)

    if not alertes:
        print("Aucun dépassement de seuil. Pas de mail envoyé.")
        sys.exit(0)

    corps = "Dépassement(s) de seuil détecté(s) :\n\n" + "\n".join(alertes)
    sujet = f"[PSMM] ALERTE — {len(alertes)} dépassement(s) de seuil"

    print(f"{len(alertes)} dépassement(s) détecté(s), envoi du mail d'alerte...")
    envoyer_mail(sujet, corps)
    print("Mail d'alerte envoyé.")
