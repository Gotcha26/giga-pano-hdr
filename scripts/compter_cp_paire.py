"""Nombre de points de contrôle entre des paires d'images données.

CONTEXTE
    Diagnostic de la géométrie (étape 3H, détecter les trous) : une jonction qui reste imparfaite vient souvent
    d'une paire d'images voisines qui n'a presque aucun point de contrôle.

MODE OPÉRATOIRE
    Lit les lignes `c n<i> N<j>` du projet, compte les points pour chaque paire (sans tenir compte de l'ordre)
    et affiche le compte des paires demandées.

ENTRÉES
    projet.pto    projet Hugin contenant des points de contrôle
    I-J ...       une ou plusieurs paires, numéros d'images du projet (0 = première ligne `i`), par ex. 135-136

SORTIES
    Console : une ligne « I-J : N points de contrôle » par paire demandée. Rien n'est écrit.

EXEMPLE
    python compter_cp_paire.py pano_grille_opt.pto 135-136 165-166 199-200

Usage : python compter_cp_paire.py projet.pto 135-136 165-166 ...
"""
import re
import sys
from collections import Counter

paires = [tuple(sorted(map(int, a.split("-")))) for a in sys.argv[2:]]
nb = Counter()
for l in open(sys.argv[1], encoding="utf-8"):
    m = re.match(r"c n(\d+) N(\d+) ", l)
    if m:
        nb[tuple(sorted((int(m.group(1)), int(m.group(2)))))] += 1
for p in paires:
    print(f"{p[0]}-{p[1]} : {nb[p]} points de contrôle")
