"""Affine la position des images « faibles » (peu de points de contrôle) qui ont pourtant quelques points valides.

CONTEXTE
    Étape 3G (géométrie) : suite de placer_isoles.py. Ce dernier remplace par interpolation sur la ligne
    toute image qui a moins de N points, même si ses quelques points sont bons. L'interpolation peut se tromper
    de quelques dixièmes de degré, ce qui floute les crêtes et les lisières à ces endroits.

MODE OPÉRATOIRE
    1. reprend le projet de base (objectif et images solides déjà optimisés) ;
    2. repère les images faibles : moins de 30 points de contrôle dans le projet de base (image 0 exclue) ;
    3. récupère dans le projet source les points de contrôle qui touchent une image faible ;
    4. ne garde que ceux qui concordent avec la position actuelle à moins de SEUIL degrés (faux points écartés) ;
    5. déclare à optimiser le lacet, le tangage et le roulis des seules images faibles qui ont au moins MIN_CP
       points valides (objectif et images solides restent fixes) ;
    6. écrit un projet à ouvrir dans Hugin : onglet Optimisation, « Optimiser maintenant ! ».

ENTRÉES
    base.pto       projet optimisé, images faibles déjà replacées (par ex. pano_grille_opt2_ciel.pto)
    source_cp.pto  projet contenant tous les points de contrôle d'origine (par ex. pano_grille_opt1.pto)
    sortie.pto     projet à écrire
    SEUIL_DEG      écart maximal toléré entre un point et son homologue, en degrés (défaut 1.0)
    MIN_CP         nombre minimal de points valides pour affiner une image (défaut 8)
    --rapport      affiche seulement l'analyse, n'écrit rien
    Constante en tête de script : COLS = 37 (colonnes de la grille).

SORTIES
    - console : tableau par image faible (position L/C, points valides, écart médian, décision « À AFFINER »
      ou « reste à la position interpolée ») puis le total ;
    - sortie.pto : points solides du projet de base + points récupérés touchant une image faible, variables à
      optimiser limitées aux images à affiner. Rien n'est écrit avec --rapport.

EXEMPLE
    python affiner_images_faibles.py opt2_ciel.pto pano_grille_cp.pto opt3_in.pto 1.5 5
    python affiner_images_faibles.py opt2_ciel.pto pano_grille_cp.pto x.pto --rapport

Usage : python affiner_images_faibles.py base.pto source_cp.pto sortie.pto [SEUIL_DEG=1.0] [MIN_CP=8] [--rapport]
"""
import math
import re
import statistics
import sys
from collections import defaultdict

COLS = 37

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("base.pto", "Projet optimisé, images faibles déjà replacées", type="pto", phase="3_optimisation"),
    Arg("source_cp.pto", "Projet contenant tous les points de contrôle d'origine", type="pto", config="cp_pto"),
    Arg("sortie.pto", "Projet à écrire", type="pto"),
    Arg("SEUIL_DEG", "Écart maximal toléré entre un point et son homologue, en degrés", type="nombre", defaut=1.5),
    Arg("MIN_CP", "Nombre minimal de points valides pour affiner une image", type="entier", defaut=5),
    Arg("--rapport", "Affiche seulement l'analyse, n'écrit rien", type="drapeau"),
]
piloter(__doc__, ARGUMENTS, ecrit='le projet de sortie', globals_=globals())

args = [a for a in sys.argv[1:] if not a.startswith("--")]
base, source, sortie = args[:3]
seuil = float(args[3]) if len(args) > 3 else 1.0
min_cp = int(args[4]) if len(args) > 4 else 8
rapport = "--rapport" in sys.argv
NUM = r"(-?[\d.]+(?:[eE][+-]?\d+)?)"

lignes = open(base, encoding="utf-8").read().splitlines()
images = []
for l in lignes:
    if l.startswith("i "):
        images.append((float(re.search(rf" y{NUM}", l).group(1)), float(re.search(rf" p{NUM}", l).group(1))))
        if len(images) == 1:
            w, h = int(re.search(r" w(\d+)", l).group(1)), int(re.search(r" h(\d+)", l).group(1))
            fov = float(re.search(rf" v{NUM}", l).group(1))
F = (w / 2) / math.tan(math.radians(fov) / 2)


def cp(l):
    m = re.match(r"c n(\d+) N(\d+) x(\S+) y(\S+) X(\S+) Y(\S+)", l)
    a = list(map(float, m.groups()))
    return int(a[0]), int(a[1]), *a[2:]


def rayon(x, y, yaw, pitch):
    vx, vy, vz = x - w / 2, y - h / 2, F
    n = math.sqrt(vx * vx + vy * vy + vz * vz)
    vx, vy, vz = vx / n, vy / n, vz / n
    p, a = math.radians(pitch), math.radians(yaw)
    vy, vz = vy * math.cos(p) - vz * math.sin(p), vy * math.sin(p) + vz * math.cos(p)
    vx, vz = vx * math.cos(a) + vz * math.sin(a), -vx * math.sin(a) + vz * math.cos(a)
    return vx, vy, vz


def ecart(c):
    i, j, x1, y1, x2, y2 = c
    d = sum(p * q for p, q in zip(rayon(x1, y1, *images[i]), rayon(x2, y2, *images[j])))
    return math.degrees(math.acos(max(-1.0, min(1.0, d))))


# images faibles : celles qui n'ont plus (ou presque plus) de points dans le projet de base
nb_base = defaultdict(int)
cps_base = [cp(l) for l in lignes if l.startswith("c n")]
for i, j, *_ in cps_base:
    nb_base[i] += 1
    nb_base[j] += 1
faibles = {k for k in range(len(images)) if nb_base[k] < 30 and k != 0}

cps_source = [cp(l) for l in open(source, encoding="utf-8").read().splitlines() if l.startswith("c n")]
candidats = defaultdict(list)       # image faible -> écarts de ses points d'origine
gardes_source = []
for c in cps_source:
    if c[0] in faibles or c[1] in faibles:
        e = ecart(c)
        if e <= seuil:
            gardes_source.append(c)
            for k in (c[0], c[1]):
                if k in faibles:
                    candidats[k].append(e)

print(f"{len(faibles)} images faibles (moins de 30 points dans le projet de base) : {sorted(faibles)}")
print("image  pos       points valides   écart médian (position actuelle)   décision")
a_optimiser = []
for k in sorted(faibles):
    es = candidats.get(k, [])
    ok = len(es) >= min_cp
    if ok:
        a_optimiser.append(k)
    med = f"{statistics.median(es):.2f}°" if es else "   -"
    print(f"{k:4d}   L{k // COLS} C{k % COLS:02d}      {len(es):4d}          {med:>8s}                          "
          f"{'À AFFINER' if ok else 'reste à la position interpolée'}")
if rapport:
    sys.exit(0)

# --- projet de sortie : points solides du projet de base + points valides touchant une image faible
sortie_l, vu_variables = [], False
variables = [f"v {c}{k}" for k in a_optimiser for c in "ypr"]
for l in lignes:
    if l.startswith("c n"):
        c = cp(l)
        if c[0] in faibles or c[1] in faibles:
            continue
    if l.startswith("v ") or l == "v":
        if not vu_variables:
            sortie_l += variables + ["v"]
            vu_variables = True
        continue
    sortie_l.append(l)
    if l.startswith("c n") is False and l.startswith("i ") is False:
        pass
# insère les points récupérés après le dernier point de base (ou avant les variables)
pos = next((n for n, l in enumerate(sortie_l) if l.startswith("v ") or l == "v"), len(sortie_l))
nouveaux = []
for i, j, x1, y1, x2, y2 in gardes_source:
    nouveaux.append(f"c n{i} N{j} x{x1:.6f} y{y1:.6f} X{x2:.6f} Y{y2:.6f} t0")
sortie_l[pos:pos] = nouveaux
if not vu_variables:
    sortie_l += ["v"] + variables
open(sortie, "w", encoding="utf-8", newline="\n").write("\n".join(sortie_l) + "\n")
print(f"\n{len(a_optimiser)} images à affiner, {len(gardes_source)} points récupérés -> {sortie}")
