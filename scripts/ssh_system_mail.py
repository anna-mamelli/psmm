#!/usr/bin/env python3
"""
Job 12/13 — ssh_system_mail.py

Vérifie, pour chaque serveur surveillé, la dernière ligne enregistrée dans
`etat_systeme` (Job 11) et alerte l'administrateur par mail si un seuil
défini dans THRESHOLDS (config/hosts.py) est dépassé : CPU, RAM ou disque.

Anti-spam (Job 13) : un historique des mails d'alerte envoyés est conservé
dans la table `alertes_envoyees`. Si un mail a déjà été envoyé il y a moins
de ALERT_RATE_LIMIT_SECONDS (1h par défaut), un nouveau dépassement ne
déclenche pas de nouvel envoi — mais reste visible dans la sortie du script
("Envoi ignoré"), donc rien n'est silencieusement perdu dans les logs cron.

L'envoi passe par msmtp (même méthode que le Job 09).

Conçu pour tourner en tâche planifiée toutes les 5 minutes, juste après le
Job 11 (pour lire une donnée fraîche).

Usage :
    python3 ssh_system_mail.py
"""

import sys
import os
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config.hosts import MYSQL, MAIL, THRESHOLDS, ALERT_RATE_LIMIT_SECONDS
import pymysql


def creer_table_alertes_si_absente(curseur) -> None:
    curseur.execute(
        """
        CREATE TABLE IF NOT EXISTS alertes_envoyees (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nb_depassements INT NOT NULL,
            date_heure DATETIME NOT NULL
        )
        """
    )


def recuperer_dernier_etat_par_serveur(curseur) -> list[tuple]:
    """Retourne la dernière ligne de etat_systeme pour chaque serveur distinct."""
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


def peut_envoyer_alerte(curseur) -> bool:
    """Anti-spam : True si aucune alerte n'a été envoyée depuis ALERT_RATE_LIMIT_SECONDS."""
    curseur.execute("SELECT MAX(date_heure) FROM alertes_envoyees")
    (derniere,) = curseur.fetchone()
    if derniere is None:
        return True
    ecoule = (datetime.now() - derniere).total_seconds()
    return ecoule >= ALERT_RATE_LIMIT_SECONDS


def enregistrer_envoi_alerte(curseur, nb_depassements: int) -> None:
    curseur.execute(
        "INSERT INTO alertes_envoyees (nb_depassements, date_heure) VALUES (%s, %s)",
        (nb_depassements, datetime.now()),
    )


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
    connexion = pymysql.connect(
        host=MYSQL["host"], user=MYSQL["user"],
        password=MYSQL["password"], database=MYSQL["database"],
    )
    try:
        with connexion.cursor() as curseur:
            creer_table_alertes_si_absente(curseur)
            connexion.commit()

            print("Lecture du dernier état de chaque serveur...")
            etats = recuperer_dernier_etat_par_serveur(curseur)
            print(f"{len(etats)} serveur(s) trouvé(s) dans etat_systeme.")

            alertes = detecter_depassements(etats)

            if not alertes:
                print("Aucun dépassement de seuil. Pas de mail envoyé.")
                sys.exit(0)

            print(f"{len(alertes)} dépassement(s) détecté(s).")

            if not peut_envoyer_alerte(curseur):
                print(f"Anti-spam : un mail d'alerte a déjà été envoyé il y a moins de "
                      f"{ALERT_RATE_LIMIT_SECONDS}s. Envoi ignoré.")
                sys.exit(0)

            corps = "Dépassement(s) de seuil détecté(s) :\n\n" + "\n".join(alertes)
            sujet = f"[PSMM] ALERTE — {len(alertes)} dépassement(s) de seuil"

            print("Envoi du mail d'alerte...")
            envoyer_mail(sujet, corps)
            enregistrer_envoi_alerte(curseur, len(alertes))
            connexion.commit()
            print("Mail d'alerte envoyé et enregistré dans l'historique.")
    finally:
        connexion.close()
