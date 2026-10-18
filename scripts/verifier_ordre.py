"""Vérifie qu'un dossier d'export Lightroom respecte l'ordre attendu : rafales d'expositions, dans l'ordre de prise.

CONTEXTE
    Étape 2E (après l'export Lightroom, avant de renommer). Le renommage par rang suppose que l'export
    est complet et dans l'ordre de prise ; ce script le contrôle d'après l'EXIF.

    Script universel : aucun motif n'est imposé.
    - le **nombre d'expositions par rafale** est détecté (période de la série) ou donné avec --expos ;
    - le **motif** (valeurs de compensation en IL, dans l'ordre de prise) est lu dans la première rafale ;
    - la **vue centrée** (0 IL) peut être en première, en dernière ou en n'importe quelle position de la rafale ;
    - le **pas** entre deux expositions voisines est quelconque (1 IL, 0,7 IL, 0,3 IL ou 1/3 IL...) mais doit être
      **constant** (ou égal à --pas s'il est donné) ; les arrondis de l'EXIF (−0,33 pour −1/3 IL) sont tolérés.

MODE OPÉRATOIRE
    Lit l'EXIF de toutes les images du dossier avec exiftool, les classe par numéro de fin de nom (Lightroom
    `<préfixe>-N.tif`) ou par nom L_C_E, puis contrôle :
    - le motif contient une vue centrée, des extrêmes (sous- et surexposition) et un pas régulier ;
    - chaque rafale du dossier reproduit ce motif (sinon : image manquante, en double, ou ordre d'export faux) ;
    - l'heure de prise de vue est croissante ;
    - le nombre d'images, si la grille est donnée ;
    - même ouverture, ISO et focale partout.
    Fonctionne avec les noms Lightroom `<préfixe>-N.tif` (ordre numérique, ex. `Pano_HDR-12.tif`) ou les noms
    renommés `L_C_E`.

ENTRÉES
    DOSSIER             dossier d'export (TIFF, JPG ou DNG ; exiftool dans le PATH)
    --grille LIGNES COLONNES   contrôle le nombre total d'images (lignes x colonnes x expositions)
    --expos N           expositions par rafale (détecté par défaut)
    --pas IL            pas attendu entre expositions voisines, en IL
    --tol IL            tolérance sur les valeurs EXIF, en IL (0,1 par défaut)
    --motif "0,-0.3,..." impose le motif (IL, dans l'ordre de prise)

SORTIES
    Console seulement : nombre d'images lues, motif d'exposition, position de la vue centrée, extrêmes, régularité
    du pas, écarts au motif (10 premiers), nombre d'heures non croissantes, valeurs d'ouverture / ISO / focale
    (« <- valeurs différentes » en cas d'écart). Rien n'est écrit ni modifié.

EXEMPLE
    python verifier_ordre.py D:\\Panoramas\\Export-TIFF-L --grille 6 37

Usage : python verifier_ordre.py DOSSIER [--grille LIGNES COLONNES] [--expos N] [--pas IL] [--tol IL]
                                  [--motif "0,-0.3,-0.7,0.3,0.7"]
"""
import argparse
import csv
import re
import subprocess
from collections import Counter
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("dossier")
ap.add_argument("--expos", type=int, default=None, help="expositions par rafale (détecté par défaut)")
ap.add_argument("--grille", type=int, nargs=2, metavar=("LIGNES", "COLONNES"))
ap.add_argument("--pas", type=float, default=None, help="pas attendu entre expositions voisines, en IL")
ap.add_argument("--tol", type=float, default=0.1, help="tolérance sur les valeurs EXIF, en IL (0,1 par défaut)")
ap.add_argument("--motif", default=None, help="impose le motif (IL, dans l'ordre de prise)")
args = ap.parse_args()
TOL = args.tol

sortie = subprocess.run(
    ["exiftool", "-csv", "-FileName", "-ExposureCompensation", "-DateTimeOriginal", "-SubSecTimeOriginal",
     "-FNumber", "-ISO", "-FocalLength", "-ext", "tif", "-ext", "tiff", "-ext", "jpg", "-ext", "dng",
     str(Path(args.dossier))],
    capture_output=True, text=True, encoding="utf-8").stdout
lignes = list(csv.DictReader(sortie.splitlines()))


def cle(l):
    nom = l["FileName"]
    m = re.search(r"-(\d+)\.\w+$", nom)
    if m:
        return (0, int(m.group(1)))
    m = re.match(r"L(\d+)_C(\d+)_E(\d)", nom)
    return (1, int(m.group(1)) * 100000 + int(m.group(2)) * 10 + int(m.group(3))) if m else (2, nom)


lignes = [l for l in lignes if cle(l)[0] < 2]       # ignore les autres fichiers du dossier (rendus, tests)
lignes.sort(key=cle)
comp = [float(l["ExposureCompensation"] or 0) for l in lignes]
if not lignes:
    raise SystemExit("aucune image reconnue (noms <préfixe>-N ou L_C_E attendus)")


def ecarts(p, motif):
    return [i for i, v in enumerate(comp) if abs(v - motif[i % p]) > TOL]


# --- nombre d'expositions par rafale
motif_impose = [float(v) for v in args.motif.split(",")] if args.motif else None
if motif_impose:
    n_expos = len(motif_impose)
elif args.expos:
    n_expos = args.expos
else:
    # la première rafale se termine quand la première valeur de compensation revient
    retours = [i for i in range(1, len(comp)) if abs(comp[i] - comp[0]) <= TOL]
    n_expos = retours[0] if retours else len(comp)
    print(f"Expositions par rafale : {n_expos} (détecté : la 1re valeur revient au rang {n_expos + 1})")

attendu = args.grille[0] * args.grille[1] * n_expos if args.grille else None
print(f"{len(lignes)} images lues" + (f" (attendu : {attendu})" if attendu else ""))
if attendu and len(lignes) != attendu:
    print(f"  ATTENTION : {len(lignes) - attendu:+d} image(s) par rapport à l'attendu")

# --- motif de référence
motif = motif_impose or comp[:n_expos]
print(f"  Motif d'exposition ({'imposé' if motif_impose else 'lu dans la 1re rafale'}) : "
      + ", ".join(f"{v:+.2f}".rstrip("0").rstrip(".") for v in motif) + " IL")

# --- cohérence du motif : vue centrée, extrêmes, pas régulier
centrees = [i for i, v in enumerate(motif) if abs(v) <= TOL]
if len(centrees) != 1:
    print(f"  ATTENTION : {len(centrees)} vue(s) centrée(s) (0 IL) dans le motif, une seule est attendue")
else:
    r = centrees[0]
    place = "première" if r == 0 else "dernière" if r == len(motif) - 1 else "intermédiaire"
    print(f"  Vue centrée : rang {r + 1} sur {len(motif)} ({place} de la rafale)")
bas, haut = min(motif), max(motif)
if bas >= -TOL or haut <= TOL:
    print("  ATTENTION : le motif n'a pas à la fois une sous-exposition et une surexposition")
else:
    print(f"  Extrêmes : {bas:+.2f} IL et {haut:+.2f} IL")
tries = sorted(motif)
ecarts_pas = [b - a for a, b in zip(tries, tries[1:])]
if ecarts_pas:
    moyen = sum(ecarts_pas) / len(ecarts_pas)
    ref = args.pas if args.pas else moyen
    irreguliers = [round(p, 2) for p in ecarts_pas if abs(p - ref) > TOL]
    if irreguliers:
        print(f"  Valeurs intermédiaires : pas irréguliers {irreguliers} IL (attendu : {ref:.2f} IL)")
    else:
        print(f"  Valeurs intermédiaires : régulières, pas de {moyen:.2f} IL" + (f" (attendu {args.pas:g} IL : conforme)" if args.pas else ""))
if len({round(v / max(TOL, 1e-9)) for v in motif}) != len(motif):
    print("  ATTENTION : deux expositions pratiquement identiques dans le motif")

# --- chaque rafale reproduit le motif
mauvais = ecarts(len(motif), motif)
for i in mauvais[:10]:
    print(f"  rang {i + 1} ({lignes[i]['FileName']}) : compensation {comp[i]:+.2f}, attendue {motif[i % len(motif)]:+.2f}")
if mauvais:
    print(f"  {len(mauvais)} écart(s) au motif d'exposition : une image manque, est en double, ou l'ordre d'export est faux")
else:
    print("  Motif d'exposition respecté sur toute la série.")
if len(lignes) % len(motif):
    print(f"  ATTENTION : {len(lignes)} images ne forment pas un nombre entier de rafales de {len(motif)}")

heures = [(l["DateTimeOriginal"], l.get("SubSecTimeOriginal") or "") for l in lignes]
desordre = sum(1 for a, b in zip(heures, heures[1:]) if b < a)
print(f"  Heures de prise de vue décroissantes : {desordre}" + ("  (ordre d'export à vérifier)" if desordre else "  (ordre chronologique)"))

for champ in ("FNumber", "ISO", "FocalLength"):
    c = Counter(l[champ] for l in lignes)
    print(f"  {champ} : {dict(c)}" + ("" if len(c) == 1 else "   <- valeurs différentes"))
