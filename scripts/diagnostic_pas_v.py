"""Cherche le pas vertical qui minimise l'écart des points de contrôle (paires verticales/diagonales).

CONTEXTE
    Étape 3C.3 : le pas entre lignes de la grille théorique (5,8°) est une estimation. Ce script teste
    plusieurs valeurs et montre laquelle ramène le mieux les points de contrôle sur leurs homologues. La valeur
    trouvée est ensuite reportée dans PAS_V de generer_pto.py et generer_pto_hdr.py, ou appliquée à un projet
    existant avec corriger_pas_v.py.

MODE OPÉRATOIRE
    Pour des pas verticaux de 4,0° à 10,0° (en gardant 5,0° en horizontal), calcule la médiane de l'écart angulaire
    des points de contrôle des paires verticales et diagonales ; puis, pour des pas horizontaux de 4,6° à 5,4°
    (pas vertical fixé à 8,0°), la médiane pour les paires horizontales. Le minimum indique le pas réel.

ENTRÉES
    projet.pto    projet Hugin avec points de contrôle, grille 6 x 37, images à leur position de grille
    Constantes en tête de script : COLS, ROWS ; listes de pas testés dans les deux dernières boucles.

SORTIES
    Console : deux tables « pas -> médiane de l'écart » (verticale puis horizontale). Rien n'est écrit.

EXEMPLE
    python diagnostic_pas_v.py pano_grille_cp_clean.pto

Usage : python diagnostic_pas_v.py projet.pto
"""
import math
import re
import statistics
import sys

COLS, ROWS = 37, 6


def _taille_projet(f):
    """Taille (px) et champ horizontal (degrés) lus sur la première ligne d'image du projet."""
    for ligne in open(f, encoding="utf-8"):
        if ligne.startswith("i "):
            return (int(re.search(r" w(\d+)", ligne).group(1)), int(re.search(r" h(\d+)", ligne).group(1)),
                    float(re.search(r" v([\d.]+)", ligne).group(1)))


W, H, _FOV = _taille_projet(sys.argv[1])
F = (W / 2) / math.tan(math.radians(_FOV) / 2)

cps = []
for ligne in open(sys.argv[1], encoding="utf-8"):
    if ligne.startswith("c "):
        m = re.match(r"c n(\d+) N(\d+) x(\S+) y(\S+) X(\S+) Y(\S+)", ligne)
        a = list(map(float, m.groups()))
        cps.append((int(a[0]), int(a[1]), *a[2:]))


def rayon(x, y, yaw, pitch):
    vx, vy, vz = x - W / 2, y - H / 2, F
    n = math.sqrt(vx * vx + vy * vy + vz * vz)
    vx, vy, vz = vx / n, vy / n, vz / n
    p, a = math.radians(pitch), math.radians(yaw)
    vy, vz = vy * math.cos(p) - vz * math.sin(p), vy * math.sin(p) + vz * math.cos(p)
    vx, vz = vx * math.cos(a) + vz * math.sin(a), -vx * math.sin(a) + vz * math.cos(a)
    return vx, vy, vz


def pos(idx, pas_h, pas_v):
    ligne, col = divmod(idx, COLS)
    return ((COLS - 1) / 2 - col) * pas_h, ((ROWS - 1) / 2 - ligne) * pas_v


def mediane(pas_h, pas_v, filtre):
    res = []
    for (i, j, x1, y1, x2, y2) in cps:
        a, b = sorted((i, j))
        dr, dc = b // COLS - a // COLS, abs(b % COLS - a % COLS)
        if not filtre(dr, dc):
            continue
        r1 = rayon(x1, y1, *pos(i, pas_h, pas_v))
        r2 = rayon(x2, y2, *pos(j, pas_h, pas_v))
        d = sum(p * q for p, q in zip(r1, r2))
        res.append(math.degrees(math.acos(max(-1.0, min(1.0, d)))))
    return statistics.median(res)


print("pas vertical -> médiane écart (paires verticales + diagonales)")
for pv in [4.0, 4.5, 5.0, 5.3, 5.5, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0]:
    print(f"{pv:5.1f}°   {mediane(5.0, pv, lambda dr, dc: dr == 1 and dc <= 1):6.2f}°")
print("\npas horizontal -> médiane écart (paires horizontales)")
for ph in [4.6, 4.8, 4.9, 5.0, 5.1, 5.2, 5.4]:
    print(f"{ph:5.1f}°   {mediane(ph, 8.0, lambda dr, dc: dr == 0 and dc == 1):6.2f}°")
