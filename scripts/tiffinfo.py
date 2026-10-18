"""Affiche la taille, l'orientation et la profondeur de bits d'un TIFF, sans le décoder.

CONTEXTE
    Utilitaire. Lit seulement l'en-tête (premier répertoire d'étiquettes TIFF) : instantané même sur un fichier de
    plusieurs Go. Sert à relever la taille réelle des images exportées, à passer ensuite à redimensionner_projet.py
    (--images) ou à vérifier un export.

MODE OPÉRATOIRE
    Lit l'ordre des octets, le décalage du premier répertoire, puis les étiquettes 256 (largeur), 257 (hauteur),
    274 (orientation) et 258 (bits par échantillon).

ENTRÉES
    image.tif    le fichier TIFF à interroger (TIFF classique ; pas de décodage BigTIFF)

SORTIES
    Console, une ligne : « largeur L hauteur H orientation O bits B » (« None » si l'étiquette est absente).

EXEMPLE
    python tiffinfo.py L0_C00_E0.tif

Usage : python tiffinfo.py image.tif
"""
import struct
import sys

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("image.tif", "Fichier TIFF à interroger", type="chemin"),
]
piloter(__doc__, ARGUMENTS, ecrit=None, globals_=globals())

with open(sys.argv[1], "rb") as f:
    bo = "<" if f.read(2) == b"II" else ">"
    f.read(2)
    off = struct.unpack(bo + "I", f.read(4))[0]
    f.seek(off)
    n = struct.unpack(bo + "H", f.read(2))[0]
    tags = {}
    for _ in range(n):
        tag, typ, cnt = struct.unpack(bo + "HHI", f.read(8))
        raw = f.read(4)
        val = struct.unpack(bo + ("H" if typ == 3 else "I"), raw[: 2 if typ == 3 else 4])[0]
        tags[tag] = val
print("largeur", tags.get(256), "hauteur", tags.get(257), "orientation", tags.get(274), "bits", tags.get(258))
