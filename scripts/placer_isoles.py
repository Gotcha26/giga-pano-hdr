"""Place les images sans point de contrôle (ciel uniforme) d'après leurs voisines optimisées.

CONTEXTE
    Étape 3G. Dans le ciel uniforme, CPFind ne trouve aucun point de contrôle : l'optimisation ne peut
    pas placer ces images (« isolées »), qui partent n'importe où. Le décalage mécanique de la rotule d'une ligne
    de prise de vue variant progressivement, on les replace par interpolation entre les images solides de leur
    ligne. Suite possible : affiner_images_faibles.py.

MODE OPÉRATOIRE
    1. compte les points de contrôle de chaque image ; une image est « isolée » si elle en a moins de SEUIL_CP
       (l'image 0, ancre, n'est jamais déplacée) ;
    2. calcule la correction (position optimisée - position de grille) des images solides ;
    3. pour chaque isolée : interpolation linéaire de cette correction le long de la même ligne, entre l'image
       solide la plus proche à gauche et à droite (ou la seule disponible) ; position = grille + correction ;
    4. retire de la liste des variables à optimiser les variables y, p, r de ces images, pour qu'elles ne bougent plus.

ENTRÉES
    optimise.pto  projet optimisé par Hugin
    sortie.pto    projet à écrire
    PAS_H PAS_V   pas de la grille en degrés (défaut 5.0 et 5.8)
    SEUIL_CP      nombre minimal de points pour être « solide » (défaut 1 = seulement les images sans aucun point ;
                  le guide emploie 30). Les paramètres sont positionnels : pour fixer SEUIL_CP, donner aussi PAS_H PAS_V.
    Constante en tête de script : COLS, ROWS = 37, 6.

SORTIES
    sortie.pto + console : liste des images isolées, la correction appliquée à chacune, total. La liste des
    isolées sert ensuite à l'option --exclure de preparer_optimisation.py.

EXEMPLE
    python placer_isoles.py opt1.pto opt1_ciel.pto 5 5.8 30

Usage : python placer_isoles.py optimise.pto sortie.pto [PAS_H PAS_V [SEUIL_CP]]
"""
import re
import sys

COLS, ROWS = 37, 6
entree, sortie = sys.argv[1], sys.argv[2]
pas_h = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
pas_v = float(sys.argv[4]) if len(sys.argv) > 4 else 5.8
seuil_cp = int(sys.argv[5]) if len(sys.argv) > 5 else 1   # 1 = seulement les images sans aucun point

lignes = open(entree, encoding="utf-8").readlines()
NUM = r"(-?[\d.]+(?:[eE][+-]?\d+)?)"


def lire(l, cle):
    return float(re.search(rf" {cle}{NUM}", l).group(1))


pos = []
for l in lignes:
    if l.startswith("i "):
        pos.append([lire(l, "y"), lire(l, "p"), lire(l, "r")])

nb_cp = [0] * len(pos)
for l in lignes:
    m = re.match(r"c n(\d+) N(\d+) ", l)
    if m:
        nb_cp[int(m.group(1))] += 1
        nb_cp[int(m.group(2))] += 1
# une image avec trop peu de points est considérée comme mal contrainte
connectees = {k for k in range(len(pos)) if nb_cp[k] >= seuil_cp} | {0}   # 0 = ancre, jamais déplacée
isolees = [k for k in range(len(pos)) if k not in connectees]
print(f"{len(isolees)} images avec moins de {seuil_cp} points : {isolees}")


def grille(k):
    ligne, col = divmod(k, COLS)
    return [((COLS - 1) / 2 - col) * pas_h, ((ROWS - 1) / 2 - ligne) * pas_v, 0.0]


delta = {k: [a - b for a, b in zip(pos[k], grille(k))] for k in connectees}
nouveau = {}
for k in isolees:
    # interpolation linéaire le long de la même ligne, entre les images solides les plus proches
    # (le décalage mécanique d'une ligne de prise de vue varie progressivement d'une image à l'autre)
    ligne, col = divmod(k, COLS)
    g = next((c for c in range(col - 1, -1, -1) if ligne * COLS + c in delta), None)
    d = next((c for c in range(col + 1, COLS) if ligne * COLS + c in delta), None)
    if g is None and d is None:
        print(f"image {k} : aucune image solide sur sa ligne, laissée à la grille")
        continue
    if g is None or d is None:
        moy = delta[ligne * COLS + (d if g is None else g)]
    else:
        t = (col - g) / (d - g)
        a, b = delta[ligne * COLS + g], delta[ligne * COLS + d]
        moy = [a[i] + t * (b[i] - a[i]) for i in range(3)]
    nouveau[k] = [x + y for x, y in zip(grille(k), moy)]
    print(f"image {k:3d} (L{ligne} C{col:02d}) : entre C{g} et C{d}, "
          f"correction yaw {moy[0]:+.2f} pitch {moy[1]:+.2f} roll {moy[2]:+.2f}")

sortie_l, idx = [], 0
variables_a_retirer = {f"v {c}{k}" for k in nouveau for c in "ypr"}
for l in lignes:
    if l.startswith("i "):
        if idx in nouveau:
            y, p, r = nouveau[idx]
            l = re.sub(rf" y{NUM}", f" y{y:.4f}", l, count=1)
            l = re.sub(rf" p{NUM}", f" p{p:.4f}", l, count=1)
            l = re.sub(rf" r{NUM}", f" r{r:.4f}", l, count=1)
        idx += 1
    elif l.strip() in variables_a_retirer:
        continue
    sortie_l.append(l)
open(sortie, "w", encoding="utf-8", newline="\n").writelines(sortie_l)
print(f"{len(nouveau)} images isolées replacées -> {sortie}")
