"""Supprime les points de contrôle trop éloignés de la grille de départ.

CONTEXTE
    Étape 3D : retirer les faux points de contrôle avant d'optimiser. Un point correct doit tomber à moins
    de SEUIL degrés de son homologue quand les images sont à leur position de grille ; au-delà, c'est un faux
    point (il tirerait l'optimisation vers une mauvaise solution). Peut être rejoué sur un projet déjà optimisé
    avec un seuil plus serré (par ex. 0,6°).

MODE OPÉRATOIRE
    Pour chaque point de contrôle, calcule l'angle entre les deux rayons (un par image) à la position actuelle
    des images (modèle rectilinéaire, distorsion ignorée) et retire le point si l'angle dépasse SEUIL.

ENTRÉES
    entree.pto      projet Hugin avec points de contrôle
    sortie.pto      projet à écrire
    SEUIL_DEGRES    écart maximal conservé, en degrés (ex. 2.5, puis 0.6 après optimisation)
    Constante en tête de script : COLS = 37.

SORTIES
    sortie.pto, et sur la console : nombre de points retirés / conservés, et liste (20 premières) des images qui
    n'ont plus que moins de 8 points.

EXEMPLE
    python filtrer_cp.py cp_clean.pto f2.5.pto 2.5

Usage : python filtrer_cp.py entree.pto sortie.pto SEUIL_DEGRES
"""
import math
import re
import sys
from collections import Counter

COLS = 37


def _taille_projet(f):
    """Taille (px) et champ horizontal (degrés) lus sur la première ligne d'image du projet."""
    for ligne in open(f, encoding="utf-8"):
        if ligne.startswith("i "):
            return (int(re.search(r" w(\d+)", ligne).group(1)), int(re.search(r" h(\d+)", ligne).group(1)),
                    float(re.search(r" v([\d.]+)", ligne).group(1)))


W, H, _FOV = _taille_projet(sys.argv[1])
F = (W / 2) / math.tan(math.radians(_FOV) / 2)
entree, sortie, seuil = sys.argv[1], sys.argv[2], float(sys.argv[3])

lignes = open(entree, encoding="utf-8").readlines()
images = []
for l in lignes:
    if l.startswith("i "):
        images.append((float(re.search(r" y(-?[\d.]+)", l).group(1)),
                       float(re.search(r" p(-?[\d.]+)", l).group(1))))


def rayon(x, y, yaw, pitch):
    vx, vy, vz = x - W / 2, y - H / 2, F
    n = math.sqrt(vx * vx + vy * vy + vz * vz)
    vx, vy, vz = vx / n, vy / n, vz / n
    p, a = math.radians(pitch), math.radians(yaw)
    vy, vz = vy * math.cos(p) - vz * math.sin(p), vy * math.sin(p) + vz * math.cos(p)
    vx, vz = vx * math.cos(a) + vz * math.sin(a), -vx * math.sin(a) + vz * math.cos(a)
    return vx, vy, vz


gardes, retires = [], 0
par_image = Counter()
for l in lignes:
    m = re.match(r"c n(\d+) N(\d+) x(\S+) y(\S+) X(\S+) Y(\S+)", l)
    if not m:
        gardes.append(l)
        continue
    i, j = int(m.group(1)), int(m.group(2))
    x1, y1, x2, y2 = map(float, m.groups()[2:])
    d = sum(p * q for p, q in zip(rayon(x1, y1, *images[i]), rayon(x2, y2, *images[j])))
    if math.degrees(math.acos(max(-1.0, min(1.0, d)))) > seuil:
        retires += 1
        continue
    gardes.append(l)
    par_image[i] += 1
    par_image[j] += 1

open(sortie, "w", encoding="utf-8", newline="\n").writelines(gardes)
total = sum(1 for l in lignes if l.startswith("c "))
print(f"{retires} points retirés sur {total} (seuil {seuil}°), {total - retires} conservés")
faibles = [k for k in range(len(images)) if par_image[k] < 8]
print(f"images avec moins de 8 points : {len(faibles)} {faibles[:20]}")
