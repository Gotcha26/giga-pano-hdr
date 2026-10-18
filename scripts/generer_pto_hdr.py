"""Génère un projet Hugin HDR : grille 6 x 37, 7 expositions groupées en piles.

CONTEXTE
    Variante de generer_pto.py pour la prise de vue HDR : 222 positions x 7 expositions = 1554 images. Dans
    chaque pile, E0 (exposition de référence) porte la position ; les autres lui sont liées et ne diffèrent que
    par l'exposition. Le HDR de la phase 5 part plutôt du projet optimisé de la vue centrée
    (voir propager_geometrie.py) ; ce script sert à partir de la grille théorique.

MODE OPÉRATOIRE
    1. cherche dans DOSSIER les fichiers L{ligne}_C{colonne}_E{expo}.tif (voir renommer_pano.py) et vérifie qu'il
       y en a 1554 ;
    2. lit la taille des images dans l'en-tête TIFF ;
    3. écrit pour chaque image sa compensation d'exposition (Eev, d'après la table EV) ; E0 porte r/p/y, les
       autres exposent `r=pile p=pile y=pile` (liées à E0).

ENTRÉES
    DOSSIER       dossier des images L_C_E (1554 fichiers)
    sortie.pto    (facultatif) défaut : DOSSIER/pano_HDR_grille.pto ; chemins d'images relatifs si le .pto est
                  dans un autre dossier
    Constantes en tête de script : COLS, ROWS, FOCALE, LARGEUR_MM, PAS_H, PAS_V, EXPOS = 7,
    EV (compensation par exposition : 0, -3, -2, -1, +1, +2, +3), EEV_BASE (f/10, 1/100 s, ISO 100).

SORTIES
    sortie.pto + message « N images, 222 piles ». Arrêt si le nombre de fichiers est différent de 1554.

EXEMPLE
    python generer_pto_hdr.py D:\\Panoramas\\Export-TIFF-L hdr\\pano_HDR_grille.pto

Usage : python generer_pto_hdr.py DOSSIER [sortie.pto]
"""
import math
import os
import re
import sys
from pathlib import Path

COLS, ROWS = 37, 6
FOCALE = 200.0
LARGEUR_MM = 24.0       # portrait
PAS_H = 5.0
PAS_V = 5.8             # degrés entre lignes (mesuré avec diagnostic_pas_v.py)
LENS_W, LENS_H = 3456, 5184
EXPOS = 7

# Compensation d'exposition (EV) lue dans l'EXIF, par numéro d'exposition
EV = {0: 0, 1: -3, 2: -2, 3: -1, 4: 1, 5: 2, 6: 3}
EEV_BASE = math.log2(10.0 ** 2 * 100)   # f/10, 1/100 s, ISO 100

hfov = 2 * math.degrees(math.atan(LARGEUR_MM / 2 / FOCALE))


def chemin_image(dossier, nom, sortie):
    """Nom de l'image tel qu'écrit dans le .pto : nu si le .pto est à côté des images,
    relatif sinon, absolu si les deux sont sur des lecteurs différents."""
    img = dossier.resolve() / nom
    try:
        return os.path.relpath(img, sortie.resolve().parent)
    except ValueError:
        return str(img)


def taille_tiff(chemin):
    """Largeur et hauteur en pixels, lues dans l'en-tête TIFF."""
    import struct
    with open(chemin, "rb") as f:
        bo = "<" if f.read(2) == b"II" else ">"
        f.read(2)
        f.seek(struct.unpack(bo + "I", f.read(4))[0])
        n = struct.unpack(bo + "H", f.read(2))[0]
        tags = {}
        for _ in range(n):
            tag, typ, _cnt = struct.unpack(bo + "HHI", f.read(8))
            brut = f.read(4)
            tags[tag] = struct.unpack(bo + ("H" if typ == 3 else "I"), brut[: 2 if typ == 3 else 4])[0]
    return tags[256], tags[257]

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("DOSSIER", "Dossier des images L_C_E (toutes les expositions)", type="dossier", config="export_l"),
    Arg("sortie.pto", "Projet à écrire (défaut : DOSSIER/pano_HDR_grille.pto)", type="pto", obligatoire=False),
]
piloter(__doc__, ARGUMENTS, ecrit='le projet de sortie', globals_=globals())

def main():
    global LENS_W, LENS_H
    dossier = Path(sys.argv[1])
    sortie = Path(sys.argv[2]) if len(sys.argv) > 2 else dossier / "pano_HDR_grille.pto"

    trouves = {}
    for p in dossier.glob("L*_C*_E*.tif"):
        m = re.fullmatch(r"L(\d+)_C(\d+)_E(\d)", p.stem)
        if m:
            trouves[(int(m.group(1)), int(m.group(2)), int(m.group(3)))] = p.name
    attendu = COLS * ROWS * EXPOS
    if len(trouves) != attendu:
        sys.exit(f"{len(trouves)} fichiers trouvés, {attendu} attendus")
    LENS_W, LENS_H = taille_tiff(dossier / trouves[(0, 0, 0)])
    print(f"taille des images lue dans les fichiers : {LENS_W} x {LENS_H} px")

    out = [
        "# hugin project file",
        "#hugin_ptoversion 2",
        'p f1 w12000 h3000 v185 k0 E0 R0 S0,12000,0,3000 n"TIFF_m c:LZW"',
        "m i0",
        "",
    ]
    idx = 0
    for ligne in range(ROWS):
        for col in range(COLS):
            yaw = ((COLS - 1) / 2 - col) * PAS_H
            pitch = ((ROWS - 1) / 2 - ligne) * PAS_V
            pile = idx
            for expo in range(EXPOS):
                eev = EEV_BASE - EV[expo]
                if idx == 0:
                    lens = (f"f0 w{LENS_W} h{LENS_H} v{hfov:.4f} Ra0 Rb0 Rc0 Rd0 Re0 ")
                    dist = "j0 a0 b0 c0 d0 e0 g0 t0 Va1 Vb0 Vc0 Vd0 Vx0 Vy0 Vm5 "
                else:
                    lens = f"f0 w{LENS_W} h{LENS_H} v=0 Ra=0 Rb=0 Rc=0 Rd=0 Re=0 "
                    dist = "j0 a=0 b=0 c=0 d=0 e=0 g=0 t=0 Va=0 Vb=0 Vc=0 Vd=0 Vx=0 Vy=0 Vm5 "
                if expo == 0:
                    pos = f"r0 p{pitch:.4f} y{yaw:.4f} TrX0 TrY0 TrZ0 "
                else:
                    pos = f"r={pile} p={pile} y={pile} TrX={pile} TrY={pile} TrZ={pile} "
                nom = chemin_image(dossier, trouves[(ligne, col, expo)], sortie)
                out.append(f"i {lens}Eev{eev:.4f} Er1 Eb1 {pos}{dist}n\"{nom}\"")
                idx += 1

    out += ["", "# specify variables that should be optimized", "v", ""]
    sortie.write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"{sortie} écrit ({idx} images, {COLS * ROWS} piles)")


main()
