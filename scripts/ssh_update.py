#!/usr/bin/env python3
"""
Job 14 — ssh_update.py

Vérifie et applique les mises à jour système (apt) sur chaque serveur
surveillé (ftp, web, sql), détecte si un redémarrage est nécessaire suite
à ces mises à jour, et alerte l'administrateur par mail le cas échéant.

Écart avec la consigne d'origine : celle-ci prévoyait une connexion puis
déconnexion via le portail captif Alcasar, avant/après la mise à jour.
L'école n'utilisant plus Alcasar (confirmé en cours de projet), cette
étape a été retirée — les serveurs ont un accès réseau direct pour
atteindre les dépôts Debian, sans portail captif à traverser.

Exécution manuelle (pas de cron) : la mise à jour nécessite sudo sur les
3 serveurs, demandé de façon interactive (comme les Jobs 06-08), pour ne
jamais stocker de mot de passe sudo dans un script ou un fichier de config.
Automatiser ce Job impliquerait de configurer une règle sudo NOPASSWD
dédiée à `apt` sur chaque serveur — décision de sécurité volontairement
laissée de côté ici.

Usage :
    python3 ssh_update.py
"""

import sys
import os
import subprocess
import getpass

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config.hosts import HOSTS, MAIL
from ssh_login_sudo import ssh_run_sudo_command

COMMANDE_MAJ = "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y upgrade"
COMMANDE_REBOOT_REQUIS = "test -f /var/run/reboot-required && echo OUI || echo NON"


def mettre_a_jour(cible: str, mot_de_passe_sudo: str) -> str:
    """Lance la mise à jour sur le serveur cible, retourne la sortie."""
    sortie, erreur = ssh_run_sudo_command(cible, COMMANDE_MAJ, mot_de_passe_sudo)
    return sortie


def redemarrage_necessaire(cible: str, mot_de_passe_sudo: str) -> bool:
    """Vérifie /var/run/reboot-required (créé par dpkg/needrestart après certaines mises à jour)."""
    sortie, erreur = ssh_run_sudo_command(cible, COMMANDE_REBOOT_REQUIS, mot_de_passe_sudo)
    return sortie.strip() == "OUI"


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
    mot_de_passe_sudo = getpass.getpass("Mot de passe sudo de monitor (identique sur les 3 serveurs) : ")

    serveurs_a_redemarrer = []

    for serveur in HOSTS:
        print(f"Mise à jour de '{serveur}'...")
        mettre_a_jour(serveur, mot_de_passe_sudo)
        print(f"  Mise à jour terminée sur '{serveur}'.")

        if redemarrage_necessaire(serveur, mot_de_passe_sudo):
            print(f"  Redémarrage nécessaire sur '{serveur}'.")
            serveurs_a_redemarrer.append(serveur)
        else:
            print(f"  Pas de redémarrage nécessaire sur '{serveur}'.")

    if serveurs_a_redemarrer:
        corps = (
            "Les serveurs suivants ont besoin d'être redémarrés suite aux "
            "mises à jour système :\n\n"
            + "\n".join(f"- {s}" for s in serveurs_a_redemarrer)
        )
        sujet = f"[PSMM] Redémarrage requis sur {len(serveurs_a_redemarrer)} serveur(s)"
        print("Envoi du mail d'alerte redémarrage...")
        envoyer_mail(sujet, corps)
        print("Mail envoyé.")
    else:
        print("Aucun serveur ne nécessite de redémarrage.")
