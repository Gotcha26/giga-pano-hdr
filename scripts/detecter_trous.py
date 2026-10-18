"""Cherche les paires d'images voisines qui se recouvrent trop peu (risque de bande noire).

CONTEXTE
    Étape 3H, et contrôle après la première optimisation (chercher un pas de ~180° : image expulsée).
    Le champ d'une image (portrait, 200 mm) est de 6,87° en horizontal et 10,29° en vertical ; deux images
    voisines trop écartées laissent un trou dans le panorama.

MODE OPÉRATOIRE
    Pour chaque image : compare sa position à celle de sa voisine de la ligne (écart de lacet) et à celle de la
    voisine du dessous (écart de tangage). Le recouvrement = champ - écart ; on signale les paires dont le
    recouvrement est inférieur à MARGE.

ENTRÉES
    projet.pto    projet Hugin, grille 6 x 37
    MARGE_DEG     recouvrement minimal exigé, en degrés (défaut 0.8)
    Constantes en tête de script : COLS, ROWS, FOV_H = 6.87, FOV_V = 10.29 (adapter si la focale ou le boîtier change).

SORTIES
    Console : une ligne par paire insuffisante (« horizontal » ou « vertical », rangs, position L/C, pas et
    recouvrement en degrés), puis le total. Rien n'est écrit.

EXEMPLE
    python detecter_trous.py pano_grille_opt1.pto 1.0

Usage : python detecter_trous.py projet.pto [MARGE_DEG]
"""
import re
import sys

COLS, ROWS = 37, 6
FOV_H, FOV_V = 6.87, 10.29
marge = float(sys.argv[2]) if len(sys.argv) > 2 else 0.8
NUM = r"(-?[\d.]+(?:[eE][+-]?\d+)?)"

pos = []
for l in open(sys.argv[1], encoding="utf-8"):
    if l.startswith("i "):
        pos.append(tuple(float(re.search(rf" {c}{NUM}", l).group(1)) for c in "ypr"))

n = 0
for k in range(len(pos)):
    ligne, col = divmod(k, COLS)
    if col + 1 < COLS:                                   # voisine à gauche (dans la ligne)
        dy = abs(pos[k][0] - pos[k + 1][0])
        if FOV_H - dy < marge:
            n += 1
            print(f"horizontal  {k:3d}-{k + 1:3d} (L{ligne} C{col:02d}-C{col + 1:02d})  "
                  f"pas {dy:5.2f}°  recouvrement {FOV_H - dy:+5.2f}°")
    if ligne + 1 < ROWS:                                 # voisine du dessous
        dp = abs(pos[k][1] - pos[k + COLS][1])
        if FOV_V - dp < marge:
            n += 1
            print(f"vertical    {k:3d}-{k + COLS:3d} (L{ligne}-L{ligne + 1} C{col:02d})  "
                  f"pas {dp:5.2f}°  recouvrement {FOV_V - dp:+5.2f}°")
print(f"{n} paires avec moins de {marge}° de recouvrement")
