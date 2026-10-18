"""Renomme les images exportées de Lightroom en L{ligne}_C{colonne}_E{expo}.tif d'après leur ordre de prise de vue.

CONTEXTE
    Étape 2F. Lightroom exporte des fichiers dont le nom suit l'ordre de prise, pas la position dans la
    grille. Tous les scripts suivants attendent des noms L_C_E ; ce script les produit, sans toucher aux pixels.

MODE OPÉRATOIRE
    Les fichiers sont classés par leur **numéro de fin de nom** (par exemple `20260619-091335-0000765.tif` -> 765,
    `Pano_HDR-12.tif` -> 12), qui suit l'ordre de prise. Le rang N (à partir de 1) donne :

        N - 1 = prise * EXPOS + expo        (EXPOS expositions entrelacées par position)
        prise = ligne * COLONNES + colonne  (ligne 0 = haut, colonne 0 = bord droit : prise de droite à gauche)

    Avant de renommer, le script contrôle le nombre de fichiers (attendu : lignes x colonnes x expositions),
    l'absence de trou dans la numérotation et l'absence de nom cible déjà existant.
    Pour vérifier en plus l'ordre d'exposition d'après l'EXIF : python verifier_ordre.py DOSSIER --grille L C
    Alternative qui ne dépend pas de l'ordre de tri : renommer_par_raw.py.

ENTRÉES
    DOSSIER                dossier d'export Lightroom
    --apply                renomme réellement ; sans option : essai à blanc (affiche 5 premiers et 3 derniers)
    --undo                 restaure les noms d'origine depuis correspondance.csv
    --lignes --colonnes --expos   dimensions de la grille (défauts : 6, 37, 7)
    --force                ignore un écart de nombre de fichiers ou un trou de numérotation

SORTIES
    Avec --apply : fichiers renommés en L{ligne}_C{colonne}_E{expo}.tif et `correspondance.csv` (ancien, nouveau)
    écrit dans DOSSIER. Sans option : rien n'est modifié.

EXEMPLE
    python renommer_pano.py DOSSIER                      # essai à blanc
    python renommer_pano.py DOSSIER --apply              # renomme + écrit correspondance.csv
    python renommer_pano.py DOSSIER --undo               # restaure depuis correspondance.csv

Usage : python renommer_pano.py DOSSIER [--apply | --undo] [--lignes 6 --colonnes 37 --expos 7] [--force]
"""
import argparse
import csv
import re
import sys
from pathlib import Path

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("DOSSIER", "Dossier d'export Lightroom", type="dossier", config="export_l"),
    Arg("--apply", "Renomme réellement (sinon essai à blanc)", type="drapeau"),
    Arg("--undo", "Restaure les noms d'origine depuis correspondance.csv", type="drapeau"),
    Arg("--lignes", "Lignes de la grille", type="entier", config="lignes"),
    Arg("--colonnes", "Colonnes de la grille", type="entier", config="colonnes"),
    Arg("--expos", "Expositions par position", type="entier", config="expos"),
    Arg("--force", "Ignore un écart de nombre ou un trou de numérotation", type="drapeau"),
]
piloter(__doc__, ARGUMENTS, ecrit='les noms de fichiers du dossier (essai à blanc sans --apply)', globals_=globals())

ap = argparse.ArgumentParser()
ap.add_argument("dossier")
ap.add_argument("--apply", action="store_true")
ap.add_argument("--undo", action="store_true")
ap.add_argument("--lignes", type=int, default=6)
ap.add_argument("--colonnes", type=int, default=37)
ap.add_argument("--expos", type=int, default=7)
ap.add_argument("--force", action="store_true")
args = ap.parse_args()

dossier = Path(args.dossier)
mapfile = dossier / "correspondance.csv"


def nouveau_nom(rang):          # rang à partir de 1
    prise, expo = divmod(rang - 1, args.expos)
    ligne, col = divmod(prise, args.colonnes)
    return f"L{ligne}_C{col:02d}_E{expo}.tif"


if args.undo:
    with open(mapfile, newline="", encoding="utf-8") as f:
        paires = [(r["ancien"], r["nouveau"]) for r in csv.DictReader(f)]
    for ancien, nouveau in paires:
        (dossier / nouveau).rename(dossier / ancien)
    print(f"{len(paires)} fichiers restaurés")
    sys.exit(0)

# --- fichiers candidats : tous les TIFF dont le nom se termine par un numéro, hors fichiers déjà renommés
candidats = []
for p in dossier.iterdir():
    if p.suffix.lower() not in (".tif", ".tiff") or re.fullmatch(r"L\d+_C\d+_E\d", p.stem):
        continue
    m = re.search(r"(\d+)$", p.stem)
    if m:
        candidats.append((int(m.group(1)), p.name))
candidats.sort()

attendu = args.lignes * args.colonnes * args.expos
print(f"{len(candidats)} fichiers à renommer (attendu : {attendu})")
if len(candidats) != attendu and not args.force:
    sys.exit(f"nombre de fichiers différent de l'attendu ({len(candidats) - attendu:+d}) : vérifier l'export, ou utiliser --force")
numeros = [n for n, _ in candidats]
trous = [(a, b) for a, b in zip(numeros, numeros[1:]) if b - a != 1]
if trous and not args.force:
    sys.exit(f"numérotation discontinue (par exemple {trous[0][0]} puis {trous[0][1]}) : une photo manque ou est en double ; --force pour ignorer")
if len(set(numeros)) != len(numeros):
    sys.exit("deux fichiers portent le même numéro, abandon")

plan = [(nom, nouveau_nom(i + 1)) for i, (_, nom) in enumerate(candidats)]
if any((dossier / n).exists() for _, n in plan):
    sys.exit("un nom cible existe déjà, abandon")

for a, n in plan[:5] + plan[-3:]:
    print(f"{a}  ->  {n}")

if args.apply:
    for a, n in plan:
        (dossier / a).rename(dossier / n)
    with open(mapfile, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ancien", "nouveau"])
        w.writerows(plan)
    print(f"Fait. Correspondance écrite dans {mapfile}")
else:
    print("Essai à blanc : rien n'a été modifié (--apply pour appliquer)")
