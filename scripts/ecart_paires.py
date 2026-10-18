"""Écart de luminosité et de teinte entre images voisines, mesuré sur la même portion de scène (16 bits).

CONTEXTE
    Étapes 2E et 6A.2, et contrôle de la vue d'ensemble (6C.1). Des réglages enregistrés identiques ne garantissent pas
    un rendu identique (encadré de 2B) : ce script mesure le rendu. Pour chaque paire de colonnes voisines d'une ligne, il
    compare la même scène dans les deux images et signale les paires qui sortent du lot. Sur ce panorama, il a montré
    des sauts de 5 à 11 % entre voisines de la ligne 1, là où le RAW développé de façon neutre était plat.
    Complète mesurer_gain_paires.py, qui arrondit à l'unité sur 255 niveaux : trop grossier pour ce défaut.

MODE OPÉRATOIRE
    1. la géométrie du projet donne le décalage en pixels entre les deux images (comme mesurer_gain_paires.py) ;
    2. la zone commune est découpée en tuiles de PAS px ; pour chaque tuile, rapport (n+1)/n du vert et du bleu ;
    3. on retient la MÉDIANE des tuiles (robuste au paysage et aux petits défauts de recalage) et l'écart absolu médian
       des tuiles (« bruit »), qui dit si la mesure est fiable ;
    4. sur la ligne, une paire « sort du lot » si son écart dépasse 3 fois l'écart absolu médian de la ligne (et 0,8 %).
    Lecture : G et B égaux = écart de luminosité ; B−G différent de 0 = écart de teinte. Les paires dont le bruit dépasse
    3 à 4 % (arbres, textures) sont à prendre avec prudence.

ENTRÉES
    projet.pto  projet optimisé (positions et champ des images) ; ses chemins d'images ne servent pas
    DOSSIER     dossier des images L_C_E0
    LIGNE       ligne de la grille
    COL_DEBUT COL_FIN  première et dernière paire (n -> n+1) à comparer ; défaut : toute la ligne
    Variable d'environnement VIPS : chemin de vips (sinon vips doit être dans le PATH)
    Constantes en tête de script : COLS = 37, MARGE, PAS, SEUIL_MIN.

SORTIES
    Console : une ligne par paire (nombre de tuiles, médianes G, B et B−G, bruit), puis les paires hors lot.

EXEMPLE
    python ecart_paires.py "$P\\6_pleine_res\\complet\\complet.pto" "$T\\Export-TIFF-H" 1 14 34

Dépendance : libvips (vips).

Usage : python ecart_paires.py projet.pto DOSSIER LIGNE [COL_DEBUT COL_FIN]
"""
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

COLS = 37
MARGE = 150        # px écartés au bord de la zone commune
PAS = 100          # côté des tuiles, en px
SEUIL_MIN = 0.8    # écart minimal (en %) pour sortir du lot
NUM = r"(-?[\d.]+(?:[eE][+-]?\d+)?)"


def lire_projet(texte):
    """(positions (y, p, r) par image, champ en degrés, largeur, hauteur) d'après les lignes « i » d'un .pto."""
    pos, fov, taille = [], None, None
    for ligne in texte.splitlines():
        if not ligne.startswith("i "):
            continue
        pos.append(tuple(float(re.search(rf" {c}{NUM}", ligne).group(1)) for c in "ypr"))
        if fov is None:
            fov = float(re.search(rf" v{NUM}", ligne).group(1))
            taille = tuple(int(v) for v in re.search(r" w(\d+) h(\d+)", ligne).groups())
    if not pos:
        raise ValueError("aucune image dans le projet")
    return pos, fov, taille[0], taille[1]


def zone_commune(a, b, ppd, w, h, marge=MARGE, pas=PAS):
    """Zone vue par les deux images, dans le repère de l'image n : (x, y, largeur, hauteur, dx, dy), ou None.

    Un point à x dans l'image n est à x + dx dans l'image n+1 ; largeur et hauteur sont des multiples de `pas`.
    """
    dx, dy = round((a[0] - b[0]) * ppd), round((a[1] - b[1]) * ppd)
    x0, x1 = max(0, -dx) + marge, min(w, w - dx) - marge
    y0, y1 = max(0, -dy) + marge, min(h, h - dy) - marge
    lg, ht = ((x1 - x0) // pas) * pas, ((y1 - y0) // pas) * pas
    if lg < 2 * pas or ht < 2 * pas:
        return None
    return x0, y0, lg, ht, dx, dy


def rapports_tuiles(ga, gb, ba, bb, plancher=4000, plafond=60000):
    """Rapports (n+1)/n en %, tuile par tuile, pour le vert et le bleu ; tuiles sombres ou saturées écartées."""
    rg, rb = [], []
    for i in range(len(ga)):
        if min(ga[i], gb[i], ba[i], bb[i]) > plancher and max(ga[i], gb[i]) < plafond:
            rg.append(100 * (gb[i] / ga[i] - 1))
            rb.append(100 * (bb[i] / ba[i] - 1))
    return rg, rb


def mediane_et_bruit(rapports):
    """(médiane, écart absolu médian) d'une liste de rapports."""
    m = statistics.median(rapports)
    return m, statistics.median(abs(v - m) for v in rapports)


def hors_lot(valeurs, seuil_min=SEUIL_MIN, k=3):
    """Indices des valeurs à plus de k écarts absolus médians (échelle normale) de la médiane, et de plus de seuil_min."""
    med = statistics.median(valeurs)
    mad = statistics.median(abs(v - med) for v in valeurs) or 0.05
    return [i for i, v in enumerate(valeurs) if abs(v - med) > k * 1.4826 * mad and abs(v - med) > seuil_min]


def _vips():
    v = os.environ.get("VIPS") or shutil.which("vips")
    if not v:
        raise SystemExit("vips introuvable : l'ajouter au PATH ou renseigner la variable d'environnement VIPS")
    return v


def tuiles(vips, img, x, y, lg, ht, tmp):
    """Moyennes du vert et du bleu par tuile de PAS x PAS (listes à plat, même ordre pour deux appels de même taille)."""
    res = []
    for bande in (1, 2):
        subprocess.run([vips, "extract_area", str(img), str(tmp / "a.v"), str(x), str(y), str(lg), str(ht)], check=True)
        subprocess.run([vips, "extract_band", str(tmp / "a.v"), str(tmp / "b.v"), str(bande)], check=True)
        subprocess.run([vips, "shrink", str(tmp / "b.v"), str(tmp / "s.v"), str(PAS), str(PAS)], check=True)
        subprocess.run([vips, "csvsave", str(tmp / "s.v"), str(tmp / "t.csv")], check=True)
        res.append([float(t) for t in (tmp / "t.csv").read_text().replace(",", ".").split()])
    return res


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) not in (3, 5):
        raise SystemExit(__doc__.split("Usage : ")[1])
    projet, dossier, ligne = argv[0], Path(argv[1]), int(argv[2])
    c0, c1 = (int(argv[3]), int(argv[4])) if len(argv) == 5 else (0, COLS - 2)
    pos, fov, w, h = lire_projet(Path(projet).read_text(encoding="utf-8"))
    ppd = w / fov
    vips = _vips()

    sorties = []
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for c in range(c0, c1 + 1):
            a, b = pos[ligne * COLS + c], pos[ligne * COLS + c + 1]
            z = zone_commune(a, b, ppd, w, h)
            if z is None:
                continue
            x, y, lg, ht, dx, dy = z
            ga, ba = tuiles(vips, dossier / f"L{ligne}_C{c:02d}_E0.tif", x, y, lg, ht, tmp)
            gb, bb = tuiles(vips, dossier / f"L{ligne}_C{c + 1:02d}_E0.tif", x + dx, y + dy, lg, ht, tmp)
            rg, rb = rapports_tuiles(ga, gb, ba, bb)
            if len(rg) < 8:
                continue
            mg, bruit = mediane_et_bruit(rg)
            mb, _ = mediane_et_bruit(rb)
            sorties.append((c, len(rg), mg, mb, mb - mg, bruit))

    print(f"ligne {ligne} : médiane des tuiles de {PAS} px, rapport (n+1)/n en % ; bruit = écart absolu médian sur G")
    for c, n, mg, mb, d, bruit in sorties:
        print(f"C{c:02d}-C{c + 1:02d}  {n:4d} tuiles   G {mg:+5.1f}   B {mb:+5.1f}   B-G {d:+5.1f}   bruit {bruit:.1f}")
    if len(sorties) > 4:
        for nom, i in (("G", 2), ("B", 3), ("B-G", 4)):
            v = [s[i] for s in sorties]
            med = statistics.median(v)
            sort = [f"C{sorties[j][0]:02d}-C{sorties[j][0] + 1:02d} ({v[j]:+.1f})" for j in hors_lot(v)]
            print(f"  {nom} : médiane {med:+.2f} %, hors lot : {', '.join(sort) if sort else 'aucune'}")


if __name__ == "__main__":
    main()
