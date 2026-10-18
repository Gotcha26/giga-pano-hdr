"""Mesure l'ondulation périodique de luminosité dans le ciel d'un panorama assemblé (effet « store vénitien »).

CONTEXTE
    Étape 3F (vignettage, tonalité du ciel). Quand chaque image est plus sombre sur les bords qu'au
    centre, le ciel du panorama assemblé montre des bandes qui se répètent à chaque image. Ce script chiffre cet
    effet, avant et après correction. Pour localiser les sauts, voir localiser_sauts_ciel.py.

MODE OPÉRATOIRE
    On moyenne la luminosité sur une bande de lignes de pixels de ciel (en ignorant les pixels transparents),
    on retire la tendance lente (moyenne mobile de ± 3 périodes), puis on regarde ce qui reste et s'il est
    périodique avec le pas des images (5 degrés) : corrélation du résidu avec lui-même décalé d'une période.

ENTRÉES
    panorama.tif        panorama assemblé (vue centrée)
    LIGNE_DEBUT LIGNE_FIN  bande de lignes de pixels de ciel
    LARGEUR_DEG         largeur du panorama en degrés (défaut 185)
    PAS_DEG             pas angulaire entre images, en degrés (défaut 5)
    X_DEBUT X_FIN       (facultatif) restreint l'analyse aux colonnes qui ne contiennent que du ciel

SORTIES
    Console : taille analysée, période attendue d'une image en pixels, nombre de colonnes exploitables, écart-type
    et amplitude de l'ondulation (échelle 0-255), corrélation à une période (proche de +1 = bandes qui se
    répètent à chaque image).

EXEMPLE
    python mesurer_bandes_ciel.py rendu.tif 160 220 185 5 1600 4400

Dépendance : Pillow.

Usage : python mesurer_bandes_ciel.py panorama.tif LIGNE_DEBUT LIGNE_FIN [LARGEUR_DEG=185] [PAS_DEG=5] [X_DEBUT X_FIN]
"""
import statistics
import sys

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("panorama.tif", "Panorama assemblé (vue centrée)", type="chemin"),
    Arg("LIGNE_DEBUT", "Première ligne de pixels de ciel", type="entier"),
    Arg("LIGNE_FIN", "Dernière ligne de pixels de ciel", type="entier"),
    Arg("LARGEUR_DEG", "Largeur du panorama en degrés", type="nombre", defaut=185),
    Arg("PAS_DEG", "Pas angulaire entre images, en degrés", type="nombre", config="pas_h", defaut=5),
    Arg("X_DEBUT", "Première colonne analysée (ciel seul ; défaut : toute la largeur)", type="entier", obligatoire=False),
    Arg("X_FIN", "Dernière colonne analysée", type="entier", obligatoire=False),
]
piloter(__doc__, ARGUMENTS, ecrit=None, globals_=globals())

f, y0, y1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
largeur_deg = float(sys.argv[4]) if len(sys.argv) > 4 else 185.0
pas_deg = float(sys.argv[5]) if len(sys.argv) > 5 else 5.0

im = Image.open(f).convert("RGBA")
w, h = im.size
x_debut = int(sys.argv[6]) if len(sys.argv) > 6 else 0
x_fin = int(sys.argv[7]) if len(sys.argv) > 7 else w
largeur_totale = w          # la période se calcule sur la largeur du panorama entier
im = im.crop((x_debut, 0, x_fin, h))
w, h = im.size
bande = im.crop((0, y0, w, y1))
px = bande.load()
col = []
for x in range(w):
    vals = [px[x, y] for y in range(y1 - y0)]
    vals = [0.299 * r + 0.587 * g + 0.114 * b for (r, g, b, a) in vals if a > 250]
    col.append(statistics.fmean(vals) if len(vals) > (y1 - y0) * 0.9 else None)

periode = largeur_totale * pas_deg / largeur_deg
fen = int(periode * 3)
residu = []
for x in range(w):
    lo, hi = max(0, x - fen), min(w, x + fen + 1)
    voisins = [v for v in col[lo:hi] if v is not None]
    residu.append(None if col[x] is None or len(voisins) < fen else col[x] - statistics.fmean(voisins))

valides = [r for r in residu if r is not None]
print(f"{w} x {h} px ; période attendue d'une image : {periode:.0f} px ; {len(valides)} colonnes de ciel exploitables")
if valides:
    print(f"écart-type de l'ondulation (0-255) : {statistics.pstdev(valides):.2f} ; amplitude max : {max(valides) - min(valides):.2f}")
    # corrélation avec un décalage d'une période : proche de 1 si l'ondulation se répète à chaque image
    p = round(periode)
    paires = [(residu[x], residu[x + p]) for x in range(w - p) if residu[x] is not None and residu[x + p] is not None]
    if len(paires) > 50:
        a = [u for u, _ in paires]
        b = [v for _, v in paires]
        ma, mb = statistics.fmean(a), statistics.fmean(b)
        cov = sum((u - ma) * (v - mb) for u, v in paires)
        va = sum((u - ma) ** 2 for u in a)
        vb = sum((v - mb) ** 2 for v in b)
        print(f"corrélation à une période ({p} px) : {cov / (va * vb) ** 0.5:+.2f}  (proche de +1 = bandes qui se répètent à chaque image)")
