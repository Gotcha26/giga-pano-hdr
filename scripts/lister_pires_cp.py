"""Liste les points de contrôle les plus éloignés de leur homologue, avec les images concernées.

CONTEXTE
    Étape 3H : repère les faux points qui restent après optimisation, et les images qu'ils tirent.
    L'écart est l'angle entre les deux rayons (un par image) quand les images sont à leur position actuelle
    (modèle rectilinéaire, distorsion ignorée : l'ordre de grandeur suffit pour repérer les points faux).

MODE OPÉRATOIRE
    Calcule l'écart de chaque point de contrôle, les trie par écart décroissant et affiche les N premiers ; avec
    --par-image, résume aussi par image le nombre de points et l'écart maximal (10 images les plus touchées).

ENTRÉES
    projet.pto    projet Hugin avec points de contrôle (optimisé de préférence)
    N             nombre de points à lister (défaut 15)
    --par-image   ajoute le résumé par image
    Constante en tête de script : COLS = 37.

SORTIES
    Console : taille de l'image et champ lus dans le projet, tableau « écart, images, (ligne, colonne), position
    dans chaque image (px) » ; avec --par-image, les 10 images dont l'écart maximal est le plus grand. Rien n'est écrit.

EXEMPLE
    python lister_pires_cp.py pano_grille_opt2.pto 12 --par-image

Usage : python lister_pires_cp.py projet.pto [N=15] [--par-image]
"""
import math
import re
import sys

COLS = 37
from collections import defaultdict

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("projet.pto", "Projet avec points de contrôle (optimisé de préférence)", type="pto", phase="3_optimisation"),
    Arg("N", "Nombre de points à lister", type="entier", defaut=15),
    Arg("--par-image", "Ajoute le résumé par image", type="drapeau"),
]
piloter(__doc__, ARGUMENTS, ecrit=None, globals_=globals())

fichier = sys.argv[1]
n_pires = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 15
par_image = "--par-image" in sys.argv

images, cps = [], []
for l in open(fichier, encoding="utf-8"):
    if l.startswith("i "):
        w, h = int(re.search(r" w(\d+)", l).group(1)), int(re.search(r" h(\d+)", l).group(1))
        v = re.search(r" v([\d.]+)", l)
        if v and not images:
            fov = float(v.group(1))
        images.append((float(re.search(r" y(-?[\d.]+)", l).group(1)), float(re.search(r" p(-?[\d.]+)", l).group(1))))
    elif l.startswith("c "):
        m = re.match(r"c n(\d+) N(\d+) x(\S+) y(\S+) X(\S+) Y(\S+)", l)
        a = list(map(float, m.groups()))
        cps.append((int(a[0]), int(a[1]), *a[2:]))
F = (w / 2) / math.tan(math.radians(fov) / 2)


def rayon(x, y, yaw, pitch):
    vx, vy, vz = x - w / 2, y - h / 2, F
    n = math.sqrt(vx * vx + vy * vy + vz * vz)
    vx, vy, vz = vx / n, vy / n, vz / n
    p, a = math.radians(pitch), math.radians(yaw)
    vy, vz = vy * math.cos(p) - vz * math.sin(p), vy * math.sin(p) + vz * math.cos(p)
    vx, vz = vx * math.cos(a) + vz * math.sin(a), -vx * math.sin(a) + vz * math.cos(a)
    return vx, vy, vz


res = []
for (i, j, x1, y1, x2, y2) in cps:
    d = sum(p * q for p, q in zip(rayon(x1, y1, *images[i]), rayon(x2, y2, *images[j])))
    res.append((math.degrees(math.acos(max(-1.0, min(1.0, d)))), i, j, x1, y1, x2, y2))
res.sort(reverse=True)

print(f"{len(cps)} points ; champ {fov:.3f}° ; image {w} x {h} px")
print("écart°   images        (ligne, colonne)              position dans chaque image (px)")
for e, i, j, x1, y1, x2, y2 in res[:n_pires]:
    print(f"{e:6.2f}   {i:3d}-{j:3d}   (L{i // COLS} C{i % COLS:02d})-(L{j // COLS} C{j % COLS:02d})   "
          f"({x1:.0f},{y1:.0f}) / ({x2:.0f},{y2:.0f})")

if par_image:
    stats = defaultdict(lambda: [0, 0.0])
    for e, i, j, *_ in res:
        for k in (i, j):
            stats[k][0] += 1
            stats[k][1] = max(stats[k][1], e)
    print("\nimages dont l'écart maximal est le plus grand :")
    for k, (n, mx) in sorted(stats.items(), key=lambda kv: -kv[1][1])[:10]:
        print(f"  image {k:3d} (L{k // COLS} C{k % COLS:02d}) : {n:4d} points, écart max {mx:.2f}°")
