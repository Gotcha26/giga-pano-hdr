"""Liste les images dont la correction (yaw/pitch/roll) s'écarte de celle de leurs voisines.

CONTEXTE
    Étape 3H : contrôle après optimisation. La correction d'une image = position optimisée - position
    de grille. Elle varie lentement d'une image à l'autre ; un écart brusque trahit une image mal contrainte
    (typiquement dans le ciel). Un écart de 1-2° entre voisines n'est pas forcément une erreur (précision
    mécanique de la rotule) : l'outil sert à repérer des tendances.

MODE OPÉRATOIRE
    1. lit la position (y, p, r) de chaque image et compte ses points de contrôle ;
    2. calcule sa correction par rapport à la grille théorique (pas 5° en lacet, 5,8° en tangage) ;
    3. compare cette correction à la médiane de celles de ses voisines (jusqu'à 8 voisines dans la grille) ;
    4. affiche les images dont l'écart dépasse le seuil sur au moins un des trois axes.

ENTRÉES
    projet.pto    projet Hugin optimisé, grille 6 x 37
    SEUIL_DEG     écart maximal toléré par axe, en degrés (défaut 1.0)
    Constantes en tête de script : COLS, ROWS, PAS_H = 5.0, PAS_V = 5.8.

SORTIES
    Console : une ligne par image au-delà du seuil (rang, position L/C, nombre de points de contrôle, écarts en
    lacet, tangage, roulis), puis le total. Rien n'est écrit.

EXEMPLE
    python detecter_aberrantes.py pano_grille_opt.pto 1.0

Usage : python detecter_aberrantes.py projet.pto [SEUIL_DEG]
"""
import re
import statistics
import sys

COLS, ROWS = 37, 6

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("projet.pto", "Projet optimisé", type="pto", phase="3_optimisation"),
    Arg("SEUIL_DEG", "Écart maximal toléré par axe, en degrés", type="nombre", defaut=1.0),
]
piloter(__doc__, ARGUMENTS, ecrit=None, globals_=globals())

fichier = sys.argv[1]
seuil = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
PAS_H, PAS_V = 5.0, 5.8
NUM = r"(-?[\d.]+(?:[eE][+-]?\d+)?)"

delta = []
nb_cp = []
for l in open(fichier, encoding="utf-8"):
    if l.startswith("i "):
        k = len(delta)
        ligne, col = divmod(k, COLS)
        y, p, r = (float(re.search(rf" {c}{NUM}", l).group(1)) for c in "ypr")
        delta.append((y - ((COLS - 1) / 2 - col) * PAS_H, p - ((ROWS - 1) / 2 - ligne) * PAS_V, r))
        nb_cp.append(0)
    m = re.match(r"c n(\d+) N(\d+) ", l)
    if m:
        nb_cp[int(m.group(1))] += 1
        nb_cp[int(m.group(2))] += 1

print("img  pos       CP   écart yaw  écart pitch  écart roll   (par rapport à la médiane des voisines)")
n = 0
for k in range(len(delta)):
    ligne, col = divmod(k, COLS)
    voisines = [delta[(ligne + dl) * COLS + col + dc] for dl in (-1, 0, 1) for dc in (-1, 0, 1)
                if (dl or dc) and 0 <= ligne + dl < ROWS and 0 <= col + dc < COLS]
    ecarts = [delta[k][i] - statistics.median(v[i] for v in voisines) for i in range(3)]
    if abs(ecarts[0]) > seuil or abs(ecarts[1]) > seuil or abs(ecarts[2]) > seuil:
        n += 1
        print(f"{k:3d}  L{ligne} C{col:02d}  {nb_cp[k]:4d}   {ecarts[0]:+7.2f}    {ecarts[1]:+7.2f}     {ecarts[2]:+7.2f}")
print(f"{n} images au-delà de {seuil}°")
