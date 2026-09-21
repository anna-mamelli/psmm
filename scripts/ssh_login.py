#!/usr/bin/env python3
"""
Job 03 — ssh_login.py

Se connecte en SSH à l'un des serveurs cibles (ftp, web ou sql) et exécute
une commande shell simple, en utilisant la clé SSH dédiée de la sonde.

Usage :
    python3 ssh_login.py <cible> ["<commande>"]

Exemples :
    python3 ssh_login.py ftp
    python3 ssh_login.py web "ls -la /var/www/html"
    python3 ssh_login.py sql "df -h"
"""

import sys
import os
import paramiko

# scripts/ et config/ sont deux dossiers voisins à la racine du dépôt :
# on ajoute la racine au chemin de recherche pour pouvoir importer config.hosts
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config.hosts import HOSTS


def connect(cible: str) -> paramiko.SSHClient:
    """
    Établit et retourne une connexion SSH vers la cible demandée
    (clé du dictionnaire HOSTS). Réutilisée par ssh_login_sudo.py (Job 04).
    """
    if cible not in HOSTS:
        raise ValueError(f"Cible inconnue : {cible!r} (attendu : {list(HOSTS)})")

    info = HOSTS[cible]
    key_path = os.path.expanduser(info["key_path"])
    private_key = paramiko.Ed25519Key.from_private_key_file(key_path)

    client = paramiko.SSHClient()
    # Simplification pour ce projet de labo : on accepte automatiquement
    # la clé d'hôte au premier contact, plutôt que de la vérifier contre
    # un known_hosts pré-rempli.
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=info["hostname"], username=info["user"], pkey=private_key)
    return client


def ssh_run_command(cible: str, commande: str) -> tuple[str, str]:
    """
    Se connecte au serveur désigné par `cible` et exécute `commande`.
    Retourne (sortie_standard, sortie_erreur).
    """
    client = connect(cible)
    try:
        _, stdout, stderr = client.exec_command(commande)
        sortie = stdout.read().decode()
        erreur = stderr.read().decode()
    finally:
        client.close()

    return sortie, erreur


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage : {sys.argv[0]} <ftp|web|sql> [\"<commande>\"]")
        sys.exit(1)

    cible = sys.argv[1]
    commande = sys.argv[2] if len(sys.argv) > 2 else "hostname && df -h"

    print(f"Connexion à '{cible}' ({HOSTS[cible]['hostname']})...")
    sortie, erreur = ssh_run_command(cible, commande)

    print("--- Sortie ---")
    print(sortie)
    if erreur:
        print("--- Erreurs ---")
        print(erreur)
