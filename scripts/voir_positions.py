"""Affiche, pour une plage d'images, la correction (yaw, pitch, roll) par rapport à la grille.

CONTEXTE
    Étapes 3E et 3H : après une optimisation, voir de combien chaque image s'est écartée de sa position
    théorique de grille. Les numéros d'images affichés (0 = première ligne `i`) servent à extraire_sous_projet.py
    et detecter_trous.py.

MODE OPÉRATOIRE
    Pour chaque image de la plage : lit lacet, tangage et roulis du projet, calcule sa position de grille
    ((18 - colonne) * PAS_H en lacet, (2,5 - ligne) * PAS_V en tangage) et affiche l'écart entre les deux.

ENTRÉES
    projet.pto         projet Hugin, grille 6 x 37
    PREMIERE DERNIERE  plage de numéros d'images (bornes comprises)
    PAS_H PAS_V        pas de la grille, en degrés (défaut 5.0 et 5.8)
    Constantes en tête de script : COLS, ROWS = 37, 6.

SORTIES
    Console : une ligne par image « rang, position L/C, lacet (écart), tangage (écart), roulis ». Rien n'est écrit.

EXEMPLE
    python voir_positions.py pano_grille_opt1.pto 44 53

Usage : python voir_positions.py projet.pto PREMIERE DERNIERE [PAS_H PAS_V]
"""
import re
import sys

COLS, ROWS = 37, 6
f, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
pas_h = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
pas_v = float(sys.argv[5]) if len(sys.argv) > 5 else 5.8
NUM = r"(-?[\d.]+(?:[eE][+-]?\d+)?)"

k = 0
for l in open(f, encoding="utf-8"):
    if l.startswith("i "):
        if a <= k <= b:
            y, p, r = (float(re.search(rf" {c}{NUM}", l).group(1)) for c in "ypr")
            ligne, col = divmod(k, COLS)
            gy, gp = ((COLS - 1) / 2 - col) * pas_h, ((ROWS - 1) / 2 - ligne) * pas_v
            print(f"{k:3d} L{ligne} C{col:02d}  yaw {y:8.3f} ({y - gy:+6.2f})  "
                  f"pitch {p:7.3f} ({p - gp:+6.2f})  roll {r:+6.2f}")
        k += 1
