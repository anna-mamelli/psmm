#!/usr/bin/env python3
"""
Job 04 — ssh_login_sudo.py

Reprend ssh_login.py (Job 03) et exécute la commande distante en mode sudo,
en transmettant le mot de passe via l'entrée standard (sudo -S) plutôt que
d'exiger un terminal interactif — nécessaire car exec_command() ne fournit
pas de pseudo-terminal par défaut.

Le mot de passe n'est jamais stocké : il est saisi à l'exécution (getpass),
jamais écrit dans le code ni dans config/hosts.py.

Usage :
    python3 ssh_login_sudo.py <cible> ["<commande>"]

Exemples :
    python3 ssh_login_sudo.py ftp
    python3 ssh_login_sudo.py web "systemctl status apache2"
"""

import sys
import os
import getpass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh_login import connect, HOSTS


def ssh_run_sudo_command(cible: str, commande: str, mot_de_passe_sudo: str) -> tuple[str, str]:
    """
    Se connecte au serveur désigné par `cible` et exécute `commande` en sudo.
    Retourne (sortie_standard, sortie_erreur) — le prompt sudo lui-même est
    filtré de la sortie d'erreur.
    """
    client = connect(cible)
    try:
        stdin, stdout, stderr = client.exec_command(f"sudo -S {commande}")
        stdin.write(mot_de_passe_sudo + "\n")
        stdin.flush()

        sortie = stdout.read().decode()
        erreur_brute = stderr.read().decode()
    finally:
        client.close()

    # sudo -S écrit son propre prompt ("[sudo] password for monitor:")
    # sur stderr : on le retire pour ne garder que les vraies erreurs.
    erreur = "\n".join(
        ligne for ligne in erreur_brute.splitlines()
        if "password for" not in ligne.lower()
    )

    return sortie, erreur


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage : {sys.argv[0]} <ftp|web|sql> [\"<commande>\"]")
        sys.exit(1)

    cible = sys.argv[1]
    # whoami par défaut : la sortie doit passer de 'monitor' (Job 03) à
    # 'root' (Job 04), ce qui prouve visuellement que le sudo fonctionne.
    commande = sys.argv[2] if len(sys.argv) > 2 else "whoami"

    mdp = getpass.getpass(f"Mot de passe sudo de monitor sur '{cible}' : ")

    print(f"Connexion à '{cible}' ({HOSTS[cible]['hostname']}) — commande en sudo...")
    sortie, erreur = ssh_run_sudo_command(cible, commande, mdp)

    print("--- Sortie ---")
    print(sortie)
    if erreur:
        print("--- Erreurs ---")
        print(erreur)
