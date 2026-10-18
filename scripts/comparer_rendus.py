"""Compare deux rendus de même taille (avant/après une correction) sur une zone de ciel.

CONTEXTE
    Mesure de qualité du ciel : sert à juger l'effet d'une correction (vignettage, exposition, fusionneur) en
    comparant deux rendus de la même zone, avant et après. Pour la couleur, voir comparer_couleur.py.

MODE OPÉRATOIRE
    Calcule la luminosité de chaque colonne de la zone dans les deux rendus (0,299 R + 0,587 G + 0,114 B, pixels
    opaques seulement ; colonne gardée si plus de 90 % de ses pixels sont opaques), puis compare.

ENTRÉES
    avant.tif apres.tif   deux rendus de même taille
    X0 X1 Y0 Y1           zone de ciel en pixels, présente et sans bord noir dans les deux rendus
    PERIODE_PX            (facultatif, lu mais non utilisé dans le calcul actuel)

SORTIES
    Console :
    - nombre de colonnes comparables ;
    - différence moyenne de luminosité (après - avant), son écart-type, ses extrêmes ;
    - ondulation de chaque rendu (écart-type après retrait de la tendance lente, échelle 0-255) ;
    - amplitude crête à crête de chaque rendu.

EXEMPLE
    python comparer_rendus.py avant.tif apres.tif 3900 4900 160 220

Dépendance : Pillow.

Usage : python comparer_rendus.py avant.tif apres.tif X0 X1 Y0 Y1 [PERIODE_PX]
"""
import statistics
import sys

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("avant.tif", "Premier rendu", type="chemin"),
    Arg("apres.tif", "Second rendu, de même taille", type="chemin"),
    Arg("X0", "Zone de ciel : première colonne", type="entier"),
    Arg("X1", "Zone de ciel : dernière colonne", type="entier"),
    Arg("Y0", "Zone de ciel : première ligne", type="entier"),
    Arg("Y1", "Zone de ciel : dernière ligne", type="entier"),
    Arg("PERIODE_PX", "Période en pixels (facultatif)", type="entier"),
]
piloter(__doc__, ARGUMENTS, ecrit=None, globals_=globals())

a, b = sys.argv[1], sys.argv[2]
x0, x1, y0, y1 = (int(v) for v in sys.argv[3:7])
periode = float(sys.argv[7]) if len(sys.argv) > 7 else None


def profil(f):
    im = Image.open(f).convert("RGBA").crop((x0, y0, x1, y1))
    px = im.load()
    out = []
    for x in range(x1 - x0):
        v = [0.299 * px[x, y][0] + 0.587 * px[x, y][1] + 0.114 * px[x, y][2]
             for y in range(y1 - y0) if px[x, y][3] > 250]
        out.append(statistics.fmean(v) if len(v) > (y1 - y0) * 0.9 else None)
    return out


def ondulation(p, fen=150):
    res = []
    for i, v in enumerate(p):
        voisins = [u for u in p[max(0, i - fen):i + fen + 1] if u is not None]
        if v is not None and len(voisins) > fen:
            res.append(v - statistics.fmean(voisins))
    return res


pa, pb = profil(a), profil(b)
diff = [vb - va for va, vb in zip(pa, pb) if va is not None and vb is not None]
print(f"zone x {x0}-{x1}, y {y0}-{y1} : {len(diff)} colonnes comparables")
if not diff:
    sys.exit("aucune colonne comparable : choisir une zone de ciel sans bord noir ni transparence, présente dans les deux rendus")
print(f"différence moyenne (après - avant) : {statistics.fmean(diff):+.3f} niveaux ; écart-type de la différence : {statistics.pstdev(diff):.3f} ; extrêmes {min(diff):+.2f} / {max(diff):+.2f}")
oa, ob = ondulation(pa), ondulation(pb)
print(f"ondulation (écart-type, 0-255) : avant {statistics.pstdev(oa):.2f}   après {statistics.pstdev(ob):.2f}")
print(f"amplitude crête à crête      : avant {max(oa) - min(oa):.2f}   après {max(ob) - min(ob):.2f}")
