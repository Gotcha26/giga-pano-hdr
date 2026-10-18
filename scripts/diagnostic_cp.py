"""Diagnostic : écart angulaire des points de contrôle par type de paire (grille de départ).

CONTEXTE
    Étape 3C.2 (vérifier la grille) : juge la qualité des points de contrôle trouvés par CPFind avant
    optimisation, en les confrontant à la grille théorique. Les paires horizontales, verticales et diagonales
    se comportent différemment : cet outil les sépare.

MODE OPÉRATOIRE
    1. lit la taille, le champ et les positions des images, et les points de contrôle ;
    2. choisit les conventions de signe du lacet et du tangage (parmi 4) qui minimisent la médiane de l'écart sur
       un échantillon (un point de contrôle sur quatre) ;
    3. pour chaque point, calcule l'angle entre les deux rayons (un par image) quand les images sont à leur
       position de grille (modèle rectilinéaire, distorsion ignorée) ;
    4. regroupe par type de paire : horizontale, verticale, diagonale, autre.

ENTRÉES
    projet.pto    projet Hugin avec points de contrôle, images à leur position de grille
    Constante en tête de script : COLS = 37.

SORTIES
    Console : conventions retenues, puis par type de paire le nombre de points, la médiane, la moyenne, le 90e
    centile et le maximum de l'écart (en degrés). Rien n'est écrit.

EXEMPLE
    python diagnostic_cp.py pano_grille_cp_clean.pto

Usage : python diagnostic_cp.py projet.pto
"""
import itertools
import math
import re
import statistics
import sys
from collections import defaultdict

COLS = 37


def _taille_projet(f):
    """Taille (px) et champ horizontal (degrés) lus sur la première ligne d'image du projet."""
    for ligne in open(f, encoding="utf-8"):
        if ligne.startswith("i "):
            return (int(re.search(r" w(\d+)", ligne).group(1)), int(re.search(r" h(\d+)", ligne).group(1)),
                    float(re.search(r" v([\d.]+)", ligne).group(1)))


W, H, _FOV = _taille_projet(sys.argv[1])
F = (W / 2) / math.tan(math.radians(_FOV) / 2)

images = []   # (yaw, pitch)
cps = []      # (i, j, x1, y1, x2, y2)
for ligne in open(sys.argv[1], encoding="utf-8"):
    if ligne.startswith("i "):
        y = float(re.search(r" y(-?[\d.]+)", ligne).group(1))
        p = float(re.search(r" p(-?[\d.]+)", ligne).group(1))
        images.append((y, p))
    elif ligne.startswith("c "):
        m = re.match(r"c n(\d+) N(\d+) x(\S+) y(\S+) X(\S+) Y(\S+)", ligne)
        a = list(map(float, m.groups()))
        cps.append((int(a[0]), int(a[1]), *a[2:]))


def rayon(x, y, yaw, pitch, sy, sp):
    vx, vy, vz = x - W / 2, y - H / 2, F
    n = math.sqrt(vx * vx + vy * vy + vz * vz)
    vx, vy, vz = vx / n, vy / n, vz / n
    p, a = math.radians(sp * pitch), math.radians(sy * yaw)
    # rotation autour de X (pitch)
    vy, vz = vy * math.cos(p) - vz * math.sin(p), vy * math.sin(p) + vz * math.cos(p)
    # rotation autour de Y (yaw)
    vx, vz = vx * math.cos(a) + vz * math.sin(a), -vx * math.sin(a) + vz * math.cos(a)
    return vx, vy, vz


def ecart(sy, sp, echant):
    res = []
    for (i, j, x1, y1, x2, y2) in echant:
        r1 = rayon(x1, y1, *images[i], sy, sp)
        r2 = rayon(x2, y2, *images[j], sy, sp)
        d = sum(a * b for a, b in zip(r1, r2))
        res.append(math.degrees(math.acos(max(-1.0, min(1.0, d)))))
    return res


echantillon = cps[::4]   # toutes les paires : les paires verticales départagent le signe du pitch
sy, sp = min(itertools.product([1, -1], [1, -1]),
             key=lambda s: statistics.median(ecart(*s, echantillon)))
print(f"conventions retenues : yaw x{sy}, pitch x{sp}")

e = ecart(sy, sp, cps)
types = defaultdict(list)
for c, v in zip(cps, e):
    i, j = sorted((c[0], c[1]))
    dr, dc = j // COLS - i // COLS, abs(j % COLS - i % COLS)
    types["horizontale" if dr == 0 and dc == 1 else
          "verticale" if dr == 1 and dc == 0 else
          "diagonale" if dr == 1 and dc == 1 else "autre"].append(v)

for k, v in types.items():
    v.sort()
    print(f"{k:12s} n={len(v):6d}  médiane {statistics.median(v):6.2f}°  moyenne {statistics.fmean(v):6.2f}°  "
          f"90e perc. {v[int(len(v) * .9)]:6.2f}°  max {v[-1]:6.2f}°")
