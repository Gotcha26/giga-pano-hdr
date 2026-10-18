"""Mesure la luminosité du ciel dans la ligne du haut : variation d'une image à l'autre et vignettage.

CONTEXTE
    Étape 3F (vignettage, tonalité du ciel), sur les images originales (pas sur un panorama assemblé) :
    donne la mesure de base du vignettage et des écarts d'exposition entre images voisines.

MODE OPÉRATOIRE
    Pour chaque image L{ligne}_C{00..36}_E0.tif : moyenne (0-255) de 5 zones horizontales (bord gauche, 1/4,
    centre, 3/4, bord droit) dans la bande supérieure de l'image (les 300 premières lignes de pixels, le ciel),
    chaque zone faisant 300 px de large.

ENTRÉES
    DOSSIER   dossier des images L_C_E0
    LIGNE     ligne de la grille à mesurer (défaut 0 = ligne du haut)
    Constantes en tête de script : COLS = 37, BANDE = (0, 300), LARGEUR = 300.

SORTIES
    Console : une ligne par image (luminosité des 5 zones et couleur du centre), puis le vignettage moyen
    (rapport bord / centre) et le saut moyen et maximal de luminosité entre images voisines.

EXEMPLE
    python mesurer_ciel.py D:\\Panoramas\\Export-TIFF-L 0

Dépendance : Pillow.

Usage : python mesurer_ciel.py DOSSIER [LIGNE]
"""
import sys

COLS = 37
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("DOSSIER", "Dossier des images L_C_E0", type="dossier", config="export_l"),
    Arg("LIGNE", "Ligne de la grille à mesurer (0 = haut)", type="entier", defaut=0),
]
piloter(__doc__, ARGUMENTS, ecrit=None, globals_=globals())

dossier = Path(sys.argv[1])
ligne = int(sys.argv[2]) if len(sys.argv) > 2 else 0
BANDE = (0, 300)       # lignes de pixels analysées (haut de l'image)
LARGEUR = 300          # largeur de chaque zone


def lum(p):
    return 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]


print(f"ligne {ligne} : luminosité moyenne (0-255) par zone ; ciel dans les {BANDE[1]} px du haut")
print("img   bord gauche   1/4    centre   3/4   bord droit   | couleur centre (R,G,B)")
lignes_zones = []
for c in range(COLS):
    f = dossier / f"L{ligne}_C{c:02d}_E0.tif"
    im = Image.open(f).convert("RGB")
    w, _ = im.size
    zones = []
    for x0 in (0, w // 4 - LARGEUR // 2, w // 2 - LARGEUR // 2, 3 * w // 4 - LARGEUR // 2, w - LARGEUR):
        r = im.crop((x0, BANDE[0], x0 + LARGEUR, BANDE[1])).resize((1, 1), Image.BOX).getpixel((0, 0))
        zones.append(r)
    lignes_zones.append(zones)
    print(f"C{c:02d}   " + "   ".join(f"{lum(z):6.1f}" for z in zones) + f"   | {zones[2]}")

import statistics
centres = [lum(z[2]) for z in lignes_zones]
bords = [(lum(z[0]) + lum(z[4])) / 2 for z in lignes_zones]
sauts = [abs(centres[i + 1] - centres[i]) for i in range(COLS - 1)]
print(f"\nvignettage moyen : bord / centre = {statistics.mean(b / c for b, c in zip(bords, centres)):.3f}")
print(f"saut moyen de luminosité entre images voisines (centre) : {statistics.mean(sauts):.2f} ; max : {max(sauts):.2f}")
