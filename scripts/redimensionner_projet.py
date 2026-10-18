"""Adapte un projet Hugin à d'autres tailles d'images et/ou à un autre panorama de sortie.

CONTEXTE
    Phase 6 (pleine résolution). La géométrie (positions, objectif) est exprimée en angles : elle ne dépend pas de
    la taille des images. On peut donc optimiser sur des images réduites, puis refaire le rendu sur les images
    pleine taille.

MODE OPÉRATOIRE
    - change la taille en pixels des images (lignes `i`), si --images est donné ; les coordonnées des points de
      contrôle sont mises à l'échelle en conséquence ;
    - change la largeur du panorama de sortie (ligne `p`), si --pano est donné (la hauteur garde le même rapport).

ENTRÉES
    entree.pto, sortie.pto   projet source, projet à écrire (peuvent être le même fichier)
    --images LARG HAUT       nouvelle taille des images, en pixels (lue sur l'export avec tiffinfo.py)
    --pano LARGEUR           nouvelle largeur du panorama, en pixels

SORTIES
    sortie.pto + message : nombre d'images, nouvelle taille, échelle des points, largeur du panorama.

EXEMPLE
    Repasser le projet maître (images 1365 x 2048) à des images pleine taille 3456 x 5184 et à un panorama de 90112 px
    de large (≈ 100 % des pixels d'origine) :
        python redimensionner_projet.py pano_grille_opt4.pto pano_E0_pleine.pto --images 3456 5184 --pano 90112

Usage : python redimensionner_projet.py entree.pto sortie.pto [--images LARG HAUT] [--pano LARGEUR]
"""
import argparse
import re
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("entree")
ap.add_argument("sortie")
ap.add_argument("--images", type=int, nargs=2, metavar=("LARG", "HAUT"))
ap.add_argument("--pano", type=int, metavar="LARGEUR")
args = ap.parse_args()

lignes = open(args.entree, encoding="utf-8").read().splitlines()
ancien_w = next(int(re.search(r" w(\d+)", l).group(1)) for l in lignes if l.startswith("i "))
echelle = args.images[0] / ancien_w if args.images else 1.0

sortie = []
for l in lignes:
    if l.startswith("i ") and args.images:
        l = re.sub(r" w\d+ h\d+", f" w{args.images[0]} h{args.images[1]}", l, count=1)
    elif l.startswith("c n") and args.images:
        m = re.match(r"(c n\d+ N\d+) x(\S+) y(\S+) X(\S+) Y(\S+)(.*)", l)
        if m:
            x1, y1, x2, y2 = (float(v) * echelle for v in m.groups()[1:5])
            l = f"{m.group(1)} x{x1:.6f} y{y1:.6f} X{x2:.6f} Y{y2:.6f}{m.group(6)}"
    elif l.startswith("p ") and args.pano:
        pw, ph = int(re.search(r" w(\d+)", l).group(1)), int(re.search(r" h(\d+)", l).group(1))
        l = re.sub(r" w\d+", f" w{args.pano}", l, count=1)
        l = re.sub(r" h\d+", f" h{round(args.pano * ph / pw)}", l, count=1)
    sortie.append(l)

Path(args.sortie).parent.mkdir(parents=True, exist_ok=True)
open(args.sortie, "w", encoding="utf-8", newline="\n").write("\n".join(sortie) + "\n")
n_i = sum(1 for l in lignes if l.startswith("i "))
print(f"{n_i} images" + (f" -> {args.images[0]} x {args.images[1]} px (échelle des points x{echelle:.4f})" if args.images else "")
      + (f" ; panorama {args.pano} px de large" if args.pano else "") + f" -> {args.sortie}")
