"""Ondulation de couleur (pas seulement de luminosité) d'une zone de ciel, pour un ou plusieurs rendus.

CONTEXTE
    Mesure de qualité du ciel (vignettage, raccords). Complète comparer_rendus.py, qui ne regarde que la
    luminosité : ici on suit aussi la couleur, pour voir si un fusionneur ou une correction introduit des bandes
    colorées.

MODE OPÉRATOIRE
    Pour chaque rendu : recadre la zone, moyenne chaque colonne de pixels (en ignorant les pixels transparents ;
    une colonne n'est gardée que si plus de 90 % de ses pixels sont opaques), retire la tendance lente (moyenne
    mobile de ±150 colonnes), puis calcule l'écart-type et l'amplitude du résidu pour R, G, B et pour deux
    rapports de chrominance (B/R et G/R, en %).

ENTRÉES
    X0 X1 Y0 Y1   zone de ciel en pixels (colonnes X0 à X1, lignes Y0 à Y1) : sans bord noir ni transparence
    rendu1.tif …  un ou plusieurs rendus à comparer (même repère de zone pour tous)

SORTIES
    Console : pour chaque rendu, une ligne par canal (R, G, B, B/R, G/R) avec « écart-type » et « amplitude ».
    Plus ces valeurs sont petites, plus le ciel est uniforme. Arrêt avec message si aucune colonne n'est exploitable.

EXEMPLE
    python comparer_couleur.py 1600 4400 160 220 enblend.tif multiblend.tif

Dépendance : Pillow. Les très grands TIFF sont acceptés (limite de pixels levée).

Usage : python comparer_couleur.py X0 X1 Y0 Y1 rendu1.tif [rendu2.tif ...]
"""
import statistics
import sys

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
x0, x1, y0, y1 = (int(v) for v in sys.argv[1:5])


def colonnes(f):
    im = Image.open(f).convert("RGBA").crop((x0, y0, x1, y1))
    px = im.load()
    cols = []
    for x in range(x1 - x0):
        pts = [px[x, y] for y in range(y1 - y0) if px[x, y][3] > 250]
        if len(pts) > (y1 - y0) * 0.9:
            cols.append(tuple(statistics.fmean(p[i] for p in pts) for i in range(3)))   # Pillow rend déjà 0-255, même pour un TIFF 16 bits
        else:
            cols.append(None)
    return cols


def onde(serie, fen=150):
    res = []
    for i, v in enumerate(serie):
        voisins = [u for u in serie[max(0, i - fen):i + fen + 1] if u is not None]
        if v is not None and len(voisins) > fen:
            res.append(v - statistics.fmean(voisins))
    return res


for f in sys.argv[5:]:
    c = colonnes(f)
    print(f"== {f} ==")
    for nom, ser in (("R", [p[0] if p else None for p in c]),
                     ("G", [p[1] if p else None for p in c]),
                     ("B", [p[2] if p else None for p in c]),
                     ("B/R (%)", [100 * p[2] / p[0] if p and p[0] else None for p in c]),
                     ("G/R (%)", [100 * p[1] / p[0] if p and p[0] else None for p in c])):
        o = onde(ser)
        if not o:
            sys.exit("aucune colonne de ciel exploitable dans cette zone : choisir une zone sans bord noir ni transparence")
        print(f"  {nom:8s} écart-type {statistics.pstdev(o):6.3f}   amplitude {max(o) - min(o):6.3f}")
