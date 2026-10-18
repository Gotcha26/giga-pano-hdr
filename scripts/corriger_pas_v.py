"""Réécrit le pitch de départ des images d'un .pto (grille 6 x 37) avec un nouveau pas vertical.

CONTEXTE
    Étape 3C.3. Le pas vertical théorique du projet de grille (5,8° par défaut) peut différer du pas réel
    mesuré avec diagnostic_pas_v.py. Ce script remet les images à la grille correspondant au pas mesuré, pour que
    la suite (filtrage des faux points, optimisation) parte d'une grille juste.

MODE OPÉRATOIRE
    Pour chaque ligne `i` du projet, remplace le tangage (p) par ((ROWS - 1) / 2 - ligne) * PAS_V, la ligne se
    déduisant du rang de l'image (rang // 37). Les points de contrôle, les lacets et les variables à optimiser
    sont conservés tels quels.

ENTRÉES
    entree.pto    projet Hugin de grille 6 x 37 (222 images)
    sortie.pto    projet à écrire
    PAS_V         nouveau pas vertical, en degrés entre deux lignes (ex. 5.8)
    Constantes en tête de script : COLS, ROWS = 37, 6.

SORTIES
    sortie.pto + message « N images mises à jour, pas vertical PAS_V° -> sortie ».

EXEMPLE
    python corriger_pas_v.py cp_clean.pto cp_clean_v58.pto 5.8

Usage : python corriger_pas_v.py entree.pto sortie.pto PAS_V
"""
import re
import sys

COLS, ROWS = 37, 6

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("entree.pto", "Projet de grille", type="pto", phase="3_optimisation"),
    Arg("sortie.pto", "Projet à écrire", type="pto"),
    Arg("PAS_V", "Nouveau pas vertical, en degrés", type="nombre", config="pas_v"),
]
piloter(__doc__, ARGUMENTS, ecrit='le projet de sortie', globals_=globals())

entree, sortie, pas_v = sys.argv[1], sys.argv[2], float(sys.argv[3])

lignes, idx = [], 0
for ligne in open(entree, encoding="utf-8"):
    if ligne.startswith("i "):
        pitch = ((ROWS - 1) / 2 - idx // COLS) * pas_v
        ligne = re.sub(r" p-?[\d.]+", f" p{pitch:.4f}", ligne, count=1)
        idx += 1
    lignes.append(ligne)
open(sortie, "w", encoding="utf-8", newline="\n").writelines(lignes)
print(f"{idx} images mises à jour, pas vertical {pas_v}° -> {sortie}")
