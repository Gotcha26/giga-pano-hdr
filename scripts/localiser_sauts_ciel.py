"""Localise les endroits où la luminosité du ciel d'un panorama assemblé saute brutalement.

CONTEXTE
    Étape 3F (vignettage, tonalité du ciel). Même principe que mesurer_bandes_ciel.py, mais au lieu d'un
    chiffre global on obtient la position des sauts, donc l'image concernée dans la ligne du haut.

MODE OPÉRATOIRE
    Calcule la luminosité de chaque colonne de la bande de lignes (pixels opaques seulement), la compare à la
    moyenne de ses voisines (±200 colonnes), regroupe les colonnes dont l'écart dépasse SEUIL en zones, et
    convertit chaque zone en degrés de lacet puis en colonne d'image (pas de 5° par image, colonne centrale = 18).

ENTRÉES
    panorama.tif          panorama assemblé (vue centrée), même très grand
    LIGNE_DEBUT LIGNE_FIN bande de lignes de pixels de ciel pur
    X_DEBUT X_FIN         colonnes à analyser (sans bord noir)
    SEUIL                 écart de luminosité (échelle 0-255) au-delà duquel on signale (défaut 6)
    LARGEUR_DEG           largeur du panorama en degrés (défaut 185)

SORTIES
    Console : nombre de colonnes analysées et de zones, puis par zone : colonnes x, yaw en degrés, écart maximal,
    colonne d'image approximative. Rien n'est écrit.

EXEMPLE
    python localiser_sauts_ciel.py rendu.tif 160 220 1600 4400 6

Dépendance : Pillow.

Usage : python localiser_sauts_ciel.py panorama.tif LIGNE_DEBUT LIGNE_FIN X_DEBUT X_FIN [SEUIL=6] [LARGEUR_DEG=185]
"""
import statistics
import sys

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("panorama.tif", "Panorama assemblé (vue centrée)", type="chemin"),
    Arg("LIGNE_DEBUT", "Première ligne de pixels de ciel pur", type="entier"),
    Arg("LIGNE_FIN", "Dernière ligne de pixels de ciel pur", type="entier"),
    Arg("X_DEBUT", "Première colonne analysée (sans bord noir)", type="entier"),
    Arg("X_FIN", "Dernière colonne analysée", type="entier"),
    Arg("SEUIL", "Écart de luminosité (0-255) au-delà duquel on signale", type="entier", defaut=6),
    Arg("LARGEUR_DEG", "Largeur du panorama en degrés", type="nombre", defaut=185),
]
piloter(__doc__, ARGUMENTS, ecrit=None, globals_=globals())

f = sys.argv[1]
y0, y1, xd, xf = (int(a) for a in sys.argv[2:6])
seuil = float(sys.argv[6]) if len(sys.argv) > 6 else 6.0
largeur_deg = float(sys.argv[7]) if len(sys.argv) > 7 else 185.0

im = Image.open(f).convert("RGBA")
W, _ = im.size
px = im.load()
col = {}
for x in range(xd, xf):
    v = [0.299 * px[x, y][0] + 0.587 * px[x, y][1] + 0.114 * px[x, y][2]
         for y in range(y0, y1) if px[x, y][3] > 250]
    if len(v) > (y1 - y0) * 0.9:
        col[x] = statistics.fmean(v)

fen = 200
zones, courante = [], None
for x in sorted(col):
    voisins = [col[k] for k in range(max(xd, x - fen), min(xf, x + fen)) if k in col]
    r = col[x] - statistics.fmean(voisins)
    if abs(r) > seuil:
        if courante and x - courante[1] <= 3:
            courante[1] = x
            courante[2] = max(courante[2], abs(r))
        else:
            courante = [x, x, abs(r)]
            zones.append(courante)

print(f"{len(col)} colonnes analysées ; {len(zones)} zones avec écart > {seuil} niveaux")
for a, b, m in zones:
    deg = lambda x: x / W * largeur_deg - largeur_deg / 2      # yaw approximatif (0 = centre du panorama)
    col_img = 18 - deg((a + b) / 2) / 5.0
    print(f"x {a:5d}-{b:5d}  yaw {deg(a):+6.1f}° à {deg(b):+6.1f}°  écart max {m:5.1f}  ~ image colonne C{col_img:4.1f}")
