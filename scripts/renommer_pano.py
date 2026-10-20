"""Renomme les images exportées de Lightroom en L{ligne}_C{colonne}_E{expo}.tif d'après leur ordre de prise de vue.

CONTEXTE
    Étape 2F. Lightroom exporte des fichiers dont le nom suit l'ordre de prise, pas la position dans la
    grille. Tous les scripts suivants attendent des noms L_C_E ; ce script les produit, sans toucher aux pixels.

MODE OPÉRATOIRE
    Les fichiers sont classés par leur **numéro de fin de nom** (par exemple `Pano_E0-01.tif` -> 1,
    `Pano_HDR-12.tif` -> 12), le numéro de séquence que Lightroom attribue dans l'ordre de prise. Le rang N
    (à partir de 1) donne :

        N - 1 = prise * EXPOS + expo        (EXPOS expositions entrelacées par position)
        prise = ligne * COLONNES + colonne  (ligne 0 = haut, colonne 0 = bord droit : prise de droite à gauche)

    Avant de renommer, le script contrôle le nombre de fichiers (attendu : lignes x colonnes x expositions),
    l'absence de trou dans la numérotation et l'absence de nom cible déjà existant. Tous les fichiers doivent
    porter le même préfixe (un seul export par dossier). Le préfixe des préréglages Lightroom donne le type d'export :
    - `…E0-` (export H) : vues centrées seules, lignes x colonnes fichiers, tous nommés _E0, quel que soit --expos ;
    - `…HDR-` (export L) : rafales de --expos expositions ;
    - autre préfixe : un export de lignes x colonnes fichiers est pris pour des vues centrées seules.

    Il contrôle aussi le **motif d'exposition** (compensation lue dans l'EXIF avec exiftool, tolérance 0,1 IL) ;
    la référence de chaque rang de la rafale est sa valeur la plus fréquente sur tout le lot :
    - rafales HDR : chaque rafale reproduit le même motif ; le motif compte un nombre impair d'expositions,
      toutes différentes, et la première est la référence (valeur médiane) autour de laquelle les autres sont
      décalées, puisqu'elle sera nommée _E0 ;
    - vues centrées seules : toutes les images ont la même compensation (pas forcément 0 IL).
    À la moindre anomalie, le script s'arrête sans rien renommer ; --force ne lève pas ce contrôle.
    Pour un contrôle plus complet (pas régulier, heures, ouverture, ISO) : python verifier_ordre.py DOSSIER --grille L C
    Alternative qui ne dépend pas de l'ordre de tri : renommer_par_raw.py.

ENTRÉES
    DOSSIER                dossier d'export Lightroom
    --apply                renomme réellement ; sans option : essai à blanc (affiche 5 premiers et 3 derniers)
    --undo                 restaure les noms d'origine depuis correspondance.csv
    --lignes --colonnes --expos   dimensions de la grille (défauts : 6, 37, 7)
    --force                ignore un écart de nombre de fichiers ou un trou de numérotation (pas le motif d'exposition)

Dépendance : exiftool dans le PATH.

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
import subprocess
import sys
from collections import Counter
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
TOL = 0.1                       # tolérance sur la compensation lue dans l'EXIF, en IL


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
        candidats.append((int(m.group(1)), p.name, p.stem[:m.start()]))
candidats.sort()
prefixes = sorted({prefixe for _, _, prefixe in candidats})
candidats = [(n, nom) for n, nom, _ in candidats]
if len(prefixes) > 1:
    sys.exit(f"plusieurs exports mélangés dans le dossier (préfixes {', '.join(prefixes)}) : aucun fichier modifié")
prefixe = prefixes[0] if prefixes else ""

# --- type d'export : le préfixe des préréglages Lightroom (Pano_E0-, Pano_HDR-) le dit ; sinon, le nombre de fichiers
positions = args.lignes * args.colonnes
attendu = positions * args.expos
if re.search(r"(?i)E0[-_ ]*$", prefixe):
    print(f"{len(candidats)} fichiers à renommer (attendu : {positions}) : export {prefixe}, vues centrées seules (nommées _E0)")
    args.expos, attendu = 1, positions
elif re.search(r"(?i)HDR[-_ ]*$", prefixe):
    print(f"{len(candidats)} fichiers à renommer (attendu : {attendu}) : export {prefixe}, rafales de {args.expos} expositions")
elif args.expos != 1 and len(candidats) == positions:     # export H : la vue centrée seule de chaque position
    print(f"{len(candidats)} fichiers à renommer : un par position, vues centrées seules (nommées _E0)")
    args.expos, attendu = 1, positions
else:
    print(f"{len(candidats)} fichiers à renommer (attendu : {attendu}, ou {positions} pour les vues centrées seules)")
if len(candidats) != attendu and not args.force:
    sys.exit(f"nombre de fichiers différent de l'attendu ({len(candidats) - attendu:+d}) : vérifier l'export, ou utiliser --force")
numeros = [n for n, _ in candidats]
trous = [(a, b) for a, b in zip(numeros, numeros[1:]) if b - a != 1]
if trous and not args.force:
    sys.exit(f"numérotation discontinue (par exemple {trous[0][0]} puis {trous[0][1]}) : une photo manque ou est en double ; --force pour ignorer")
if len(set(numeros)) != len(numeros):
    sys.exit("deux fichiers portent le même numéro, abandon")


# --- motif d'exposition (EXIF) : identique d'une rafale à l'autre, sinon rien n'est modifié
def il(v):
    return f"{v:+.2f}".rstrip("0").rstrip(".") + " IL"


try:
    sortie = subprocess.run(["exiftool", "-csv", "-n", "-FileName", "-ExposureCompensation",
                             "-ext", "tif", "-ext", "tiff", str(dossier)],
                            capture_output=True, text=True, encoding="utf-8").stdout
except FileNotFoundError:
    sys.exit("exiftool introuvable : le motif d'exposition ne peut pas être contrôlé, aucun fichier modifié")
lues = {l["FileName"]: l.get("ExposureCompensation", "") for l in csv.DictReader(sortie.splitlines())}
absents = [nom for _, nom in candidats if lues.get(nom, "") == ""]
if absents:
    sys.exit(f"compensation d'exposition absente de l'EXIF : {absents[0]}"
             + (f" (et {len(absents) - 1} autre(s))" if len(absents) > 1 else "") + ", aucun fichier modifié")
comp = [float(lues[nom]) for _, nom in candidats]
# la référence de chaque rang de la rafale est sa valeur la plus fréquente : une intruse en tête ne fausse pas le motif
motif = [float(Counter(round(v, 2) for v in comp[k::args.expos]).most_common(1)[0][0]) for k in range(args.expos)]
anomalies = [f"{nom} : {il(v)}, attendu {il(motif[i % args.expos])} (_E{i % args.expos})"
             for i, ((_, nom), v) in enumerate(zip(candidats, comp)) if abs(v - motif[i % args.expos]) > TOL]
if args.expos > 1:
    if args.expos % 2 == 0:
        anomalies.insert(0, f"{args.expos} expositions par rafale : un HDR en compte un nombre impair")
    if any(abs(a - b) <= TOL for i, a in enumerate(motif) for b in motif[i + 1:]):
        anomalies.insert(0, "deux expositions de la rafale ont la même compensation : ce n'est pas un motif HDR")
    elif sorted(motif)[len(motif) // 2] != motif[0]:
        anomalies.insert(0, f"la première image de la rafale ({il(motif[0])}) n'est pas la référence autour de laquelle"
                            " les autres sont décalées : elle ne peut pas être nommée _E0")
if anomalies:
    print(f"Motif d'exposition de référence : {', '.join(il(v) for v in motif)}")
    for a in anomalies[:10]:
        print(f"  {a}")
    if len(anomalies) > 10:
        print(f"  ... et {len(anomalies) - 10} autre(s)")
    sys.exit(f"{len(anomalies)} anomalie(s) du motif d'exposition : aucun fichier modifié")
if args.expos > 1:
    print(f"Motif d'exposition : {', '.join(il(v) for v in motif)}, identique sur les {len(comp) // args.expos} rafales")
else:
    print(f"Exposition identique sur les {len(comp)} vues ({il(motif[0])})")

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
    if args.expos > 1:      # export complet en rafales : le seul moment où la table RAW -> L_C_E s'écrit sans effort
        print("Étape suivante (2F) : écrire la table RAW -> L_C_E, matrice à conserver :\n"
              f'  python renommer_par_raw.py "{dossier}" "<$P>\\table_raw_LCE.csv" --table')
else:
    print("Essai à blanc : rien n'a été modifié (--apply pour appliquer)")
