"""Mesure l'écart de luminosité entre deux images voisines sur la même portion de ciel.

CONTEXTE
    Étape 3F (vignettage). Complète mesurer_ciel.py : au lieu de comparer des zones de même position
    dans l'image, on compare la même portion de ciel vue dans les deux images. Un rapport différent de 1,000
    indique que les deux images n'ont pas la même exposition (ou le même vignettage) à cet endroit.

MODE OPÉRATOIRE
    Pour chaque paire (colonne n, n+1) d'une ligne : la géométrie du projet donne le décalage en pixels entre les
    deux images ; on mesure la luminosité moyenne d'une même zone (fraction de l'image, indépendante de la
    taille des fichiers) dans l'image n et dans l'image n+1 décalée, et on en fait le rapport n+1 / n.

ENTRÉES
    projet.pto   projet optimisé (positions des images et champ)
    DOSSIER_IMAGES  dossier des images L_C_E0
    LIGNE COL_DEBUT COL_FIN  ligne de la grille et plage de colonnes à comparer (paires COL_DEBUT à COL_FIN)
    Constantes en tête de script : COLS = 37 ; la zone comparée est 4,3-24,6 % de la largeur et 5,8-25 % de la hauteur.

SORTIES
    Console : par paire, décalage en pixels, luminosité de chaque image et rapport ; puis le rapport moyen et son
    écart-type (1,0000 = exposition identique ; 1 % = 0,014 IL).

EXEMPLE
    python mesurer_gain_paires.py pano_grille_opt4.pto D:\\Panoramas\\Export-TIFF-L 0 0 21

Dépendance : Pillow.

Usage : python mesurer_gain_paires.py projet.pto DOSSIER_IMAGES LIGNE COL_DEBUT COL_FIN
"""
import re
import statistics
import sys
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
COLS = 37
NUM = r"(-?[\d.]+(?:[eE][+-]?\d+)?)"
projet, dossier = sys.argv[1], Path(sys.argv[2])
ligne, c0, c1 = (int(v) for v in sys.argv[3:6])

pos, fov = [], None
for l in open(projet, encoding="utf-8"):
    if l.startswith("i "):
        pos.append(tuple(float(re.search(rf" {c}{NUM}", l).group(1)) for c in "ypr"))
        if fov is None:
            fov = float(re.search(rf" v{NUM}", l).group(1))
w, h = (int(v) for v in re.search(r" w(\d+) h(\d+)", next(l for l in open(projet, encoding="utf-8") if l.startswith("i "))).groups())
ppd = w / fov                      # pixels par degré (approximation rectilinéaire au centre)


def charge(c):
    return Image.open(dossier / f"L{ligne}_C{c:02d}_E0.tif").convert("L")


def moyenne(im, x0, x1, y0, y1):
    x0, x1, y0, y1 = max(0, x0), min(w, x1), max(0, y0), min(h, y1)
    if x1 - x0 < 200 or y1 - y0 < 200:
        return None
    return statistics.fmean(im.crop((x0, y0, x1, y1)).resize((1, 1), Image.BOX).getdata())


rapports = []
prec = charge(c0)
print("paire        décalage px (x, y)   luminosité n   luminosité n+1   rapport n+1 / n")
for c in range(c0, c1):
    suiv = charge(c + 1)
    a, b = pos[ligne * COLS + c], pos[ligne * COLS + c + 1]
    dx = round((a[0] - b[0]) * ppd)          # un point à x dans n est à x + dx dans n+1
    dy = round((a[1] - b[1]) * ppd)
    # zone de comparaison exprimée en fraction de l'image (indépendante de la taille des fichiers)
    x0, x1, y0, y1 = round(w * 0.043), round(w * 0.246), round(h * 0.058), round(h * 0.25)
    m1 = moyenne(prec, x0, x1, y0, y1)
    m2 = moyenne(suiv, x0 + dx, x1 + dx, y0 + dy, y1 + dy)
    if m1 and m2:
        rapports.append(m2 / m1)
        print(f"C{c:02d}-C{c + 1:02d}   ({dx:5d},{dy:5d})        {m1:7.2f}      {m2:7.2f}        {m2 / m1:.4f}")
    prec = suiv

if rapports:
    print(f"\nrapport moyen {statistics.fmean(rapports):.4f}, écart-type {statistics.pstdev(rapports):.4f} "
          f"(1,0000 = exposition identique ; 1 % = 0,014 IL)")
