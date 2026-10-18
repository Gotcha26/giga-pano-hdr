"""Copie un projet Hugin (.pto) vers un autre dossier en réécrivant les chemins d'images.

CONTEXTE
    Sert à ranger un projet existant dans le dossier de son étape (voir le guide, « Organisation cible »),
    à rendre relatifs les chemins qu'un outil comme cpclean a écrits en absolu, ou à rattacher un projet à un
    autre dossier d'images (mêmes noms de fichiers) : par exemple, passer de l'export L à l'export H en phase 6.

MODE OPÉRATOIRE
    Parcourt les noms d'images du projet (n"...tif/jpg/png"), calcule le nouveau chemin relatif au projet de
    sortie, vérifie que chaque image existe, puis écrit le projet. Si une image manque, rien n'est écrit.

ENTRÉES
    entree.pto            projet d'origine
    sortie.pto            projet à écrire (le dossier est créé si besoin) ; peut être le même fichier que l'entrée
    --images DOSSIER      (facultatif) dossier où chercher chaque image, par son nom de fichier

    Sans --images : les images restent là où le projet d'entrée les désigne ; seuls les chemins sont recalculés
    relativement au projet de sortie.
    Avec --images : chaque image est cherchée, par son nom de fichier, dans DOSSIER_IMAGES (échec si l'une manque).

SORTIES
    sortie.pto + message « N chemins d'images réécrits ». En cas d'image introuvable : arrêt, avec le nombre
    d'images manquantes et un exemple.

EXEMPLE
    python deplacer_projet.py complet.pto complet.pto --images D:\\Panoramas\\Export-TIFF-H

Usage : python deplacer_projet.py entree.pto sortie.pto [--images DOSSIER_IMAGES]
"""
import os
import re
import sys
from pathlib import Path

args = sys.argv[1:]
if len(args) not in (2, 4) or (len(args) == 4 and args[2] != "--images"):
    sys.exit(__doc__)
entree, sortie = Path(args[0]).resolve(), Path(args[1]).resolve()
dossier_images = Path(args[3]).resolve() if len(args) == 4 else None

motif = re.compile(r'(\bn)"([^"]+\.(?:tif|tiff|jpg|jpeg|png))"', re.IGNORECASE)
manquantes = []


def reecrire(m):
    nom = m.group(2)
    if dossier_images is not None:
        img = dossier_images / Path(nom).name
    else:
        img = (entree.parent / nom).resolve()
    if not img.exists():
        manquantes.append(str(img))
    try:
        rel = os.path.relpath(img, sortie.parent)
    except ValueError:                   # lecteurs différents : chemin absolu
        rel = str(img)
    return f'{m.group(1)}"{rel}"'


texte = entree.read_text(encoding="utf-8")
nouveau, n = motif.subn(reecrire, texte)
if manquantes:
    sys.exit(f"{len(manquantes)} image(s) introuvable(s), projet non écrit. Exemple : {manquantes[0]}")
sortie.parent.mkdir(parents=True, exist_ok=True)
sortie.write_text(nouveau, encoding="utf-8", newline="\n")
print(f"{n} chemins d'images réécrits -> {sortie}")
