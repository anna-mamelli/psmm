#!/usr/bin/env python3
"""
Job 15 — ssh_google_chat.py

Envoie périodiquement un résumé de l'état des serveurs (CPU/RAM/Disque,
depuis la table etat_systeme du Job 11) et du nombre de tentatives de
connexion échouées des dernières 24h (Jobs 06-08) dans le Google Space
créé pour le groupe, via un webhook entrant.

Usage :
    python3 ssh_google_chat.py
"""

import sys
import os
from datetime import datetime

import requests
import pymysql

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config.hosts import MYSQL, GOOGLE_CHAT_WEBHOOK


def recuperer_dernier_etat_par_serveur(curseur) -> list[tuple]:
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


def recuperer_nombre_tentatives_24h(curseur) -> int:
    curseur.execute(
        "SELECT COUNT(*) FROM tentatives_connexion WHERE date_heure >= NOW() - INTERVAL 24 HOUR"
    )
    (nb,) = curseur.fetchone()
    return nb


def construire_message(etats: list[tuple], nb_tentatives: int) -> str:
    lignes = [f"*État des serveurs PSMM — {datetime.now():%Y-%m-%d %H:%M}*", ""]
    if etats:
        for serveur, cpu, ram, disk, date_heure in etats:
            lignes.append(f"• *{serveur.upper()}* — CPU {cpu:.1f}% · RAM {ram:.1f}% · Disque {disk:.1f}%")
    else:
        lignes.append("Aucune donnée d'état disponible pour le moment.")

    lignes.append("")
    lignes.append(f"🔐 Tentatives de connexion échouées (24h) : {nb_tentatives}")
    return "\n".join(lignes)


def envoyer_message_chat(texte: str) -> None:
    reponse = requests.post(GOOGLE_CHAT_WEBHOOK, json={"text": texte}, timeout=10)
    if reponse.status_code != 200:
        raise RuntimeError(f"Échec de l'envoi vers Google Chat (code {reponse.status_code}) : {reponse.text}")


if __name__ == "__main__":
    connexion = pymysql.connect(
        host=MYSQL["host"], user=MYSQL["user"],
        password=MYSQL["password"], database=MYSQL["database"],
    )
    try:
        with connexion.cursor() as curseur:
            print("Lecture de l'état des serveurs et des tentatives récentes...")
            etats = recuperer_dernier_etat_par_serveur(curseur)
            nb_tentatives = recuperer_nombre_tentatives_24h(curseur)
    finally:
        connexion.close()

    message = construire_message(etats, nb_tentatives)
    print("Envoi vers Google Chat...")
    envoyer_message_chat(message)
    print("Message envoyé.")
