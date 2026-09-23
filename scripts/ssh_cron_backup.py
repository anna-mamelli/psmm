#!/usr/bin/env python3
"""
Job 10 — ssh_cron_backup.py

Sauvegarde locale et horodatée de la base MariaDB `psmm_logs`, avec
rotation : seules les BACKUP["retention_count"] sauvegardes les plus
récentes sont conservées, les plus anciennes sont supprimées.

Conçu pour tourner en tâche planifiée (cron) toutes les 3h depuis
PSMM-sonde, en visant directement le serveur MariaDB par le réseau
(mysqldump -h ...), sans passer par SSH.

Usage :
    python3 ssh_cron_backup.py
"""

import os
import subprocess
from datetime import datetime
from glob import glob

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config.hosts import MYSQL, BACKUP


def effectuer_sauvegarde() -> str:
    """Lance mysqldump et écrit le résultat dans un fichier horodaté. Retourne le chemin créé."""
    os.makedirs(BACKUP["backup_dir"], exist_ok=True)

    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    nom_fichier = f"{MYSQL['database']}_{horodatage}.sql"
    chemin = os.path.join(BACKUP["backup_dir"], nom_fichier)

    # Le mot de passe passe par la variable d'environnement MYSQL_PWD plutôt
    # que par l'argument -p en clair, pour ne pas l'exposer dans la liste des
    # processus (ps aux) pendant l'exécution de mysqldump.
    environnement = os.environ.copy()
    environnement["MYSQL_PWD"] = MYSQL["password"]

    commande = [
        "mysqldump",
        "-h", MYSQL["host"],
        "-u", MYSQL["user"],
        MYSQL["database"],
    ]

    with open(chemin, "w") as fichier_sortie:
        resultat = subprocess.run(
            commande, stdout=fichier_sortie, stderr=subprocess.PIPE,
            text=True, env=environnement,
        )

    if resultat.returncode != 0:
        os.remove(chemin)  # pas de fichier vide/corrompu en cas d'échec
        raise RuntimeError(f"Échec de mysqldump (code {resultat.returncode}) : {resultat.stderr}")

    return chemin


def appliquer_rotation() -> list[str]:
    """Supprime les sauvegardes les plus anciennes au-delà de la rétention configurée.

    Retourne la liste des fichiers supprimés.
    """
    motif = os.path.join(BACKUP["backup_dir"], f"{MYSQL['database']}_*.sql")
    sauvegardes = sorted(glob(motif))  # tri alphabétique = tri chronologique (format horodatage)

    a_conserver = BACKUP["retention_count"]
    excedentaires = sauvegardes[:-a_conserver] if len(sauvegardes) > a_conserver else []

    for fichier in excedentaires:
        os.remove(fichier)

    return excedentaires


if __name__ == "__main__":
    print(f"Sauvegarde de la base '{MYSQL['database']}' en cours...")
    chemin = effectuer_sauvegarde()
    print(f"Sauvegarde créée : {chemin}")

    supprimees = appliquer_rotation()
    if supprimees:
        print(f"Rotation : {len(supprimees)} ancienne(s) sauvegarde(s) supprimée(s) :")
        for f in supprimees:
            print(f"  - {f}")
    else:
        print(f"Rotation : rien à supprimer (rétention = {BACKUP['retention_count']}).")
