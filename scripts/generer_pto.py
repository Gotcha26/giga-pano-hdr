"""Génère un projet Hugin (.pto) avec les images placées en grille.

CONTEXTE
    Étape 3A : point de départ de la géométrie. Les images ne sont pas encore alignées : elles sont posées
    sur la grille théorique de la prise de vue (focale 200 mm, 6 lignes x 37 colonnes, pas 5° x 5,8°). Hugin
    cherchera ensuite les points de contrôle et optimisera. Une seule exposition (E0) par position.

MODE OPÉRATOIRE
    1. cherche dans DOSSIER les fichiers L{ligne}_C{colonne}_E0.tif (voir renommer_pano.py) et vérifie qu'il y
       en a 222 ;
    2. lit la taille réelle de la première image dans son en-tête TIFF ;
    3. écrit une ligne `i` par image avec son lacet et son tangage de grille (ligne 0 = haut, colonne 0 = bord
       droit : prise de vue de droite à gauche) ; l'objectif est porté par l'image 0, les autres s'y lient ;
    4. écrit le panorama de sortie en équirectangulaire 12000 x 3000, champ 185°.

ENTRÉES
    DOSSIER       dossier des images. Si sortie.pto est dans un autre dossier, les noms d'images du projet sont
                  écrits en chemins relatifs à ce dossier (ex. ..\\Export-TIFF-L\\L0_C00_E0.tif).
    sortie.pto    (facultatif) défaut : DOSSIER/pano_grille.pto
    Constantes en tête de script : COLS, ROWS, FOCALE = 200 mm, LARGEUR_MM = 24 (portrait), PAS_H = 5.0,
    PAS_V = 5.8 (mesuré avec diagnostic_pas_v.py) ; LENS_W / LENS_H ne sont que des valeurs par défaut.

SORTIES
    sortie.pto (aucune variable à optimiser) + message « N images, champ horizontal X° ». Arrêt si le nombre de
    fichiers n'est pas 222.

EXEMPLE
    python generer_pto.py D:\\Panoramas\\Export-TIFF-L D:\\Panoramas\\Assemblage-Hugin\\3_grille\\pano_grille.pto

Usage : python generer_pto.py DOSSIER [sortie.pto]
"""
import math
import os
import re
import sys
from pathlib import Path

COLS, ROWS = 37, 6
FOCALE = 200.0          # mm, plein format
LARGEUR_MM = 24.0       # portrait : le petit côté est horizontal
PAS_H = 5.0             # degrés entre colonnes
PAS_V = 5.8             # degrés entre lignes (mesuré avec diagnostic_pas_v.py)
LENS_W, LENS_H = 3456, 5184     # remplacé par la taille réelle de la 1re image (lue dans l'en-tête TIFF)

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


def main():
    global LENS_W, LENS_H
    dossier = Path(sys.argv[1])
    sortie = Path(sys.argv[2]) if len(sys.argv) > 2 else dossier / "pano_grille.pto"

    fichiers = []
    for p in dossier.glob("L*_C*_E0.tif"):
        m = re.fullmatch(r"L(\d+)_C(\d+)_E0", p.stem)
        if m:
            fichiers.append((int(m.group(1)), int(m.group(2)), p.name))
    fichiers.sort()
    if len(fichiers) != COLS * ROWS:
        sys.exit(f"{len(fichiers)} fichiers trouvés, {COLS * ROWS} attendus")
    LENS_W, LENS_H = taille_tiff(dossier / fichiers[0][2])
    print(f"taille des images lue dans les fichiers : {LENS_W} x {LENS_H} px")

    out = [
        "# hugin project file",
        "#hugin_ptoversion 2",
        'p f1 w12000 h3000 v185 k0 E0 R0 S0,12000,0,3000 n"TIFF_m c:LZW"',
        "m i0",
        "",
    ]
    for k, (ligne, col, nom) in enumerate(fichiers):
        yaw = ((COLS - 1) / 2 - col) * PAS_H     # col 0 (droite) -> yaw positif
        pitch = ((ROWS - 1) / 2 - ligne) * PAS_V  # ligne 0 (haut) -> pitch positif
        if k == 0:
            lens = (f"f0 w{LENS_W} h{LENS_H} v{hfov:.4f} Ra0 Rb0 Rc0 Rd0 Re0 "
                    "Eev0 Er1 Eb1 ")
            dist = "j0 a0 b0 c0 d0 e0 g0 t0 Va1 Vb0 Vc0 Vd0 Vx0 Vy0 Vm5 "
        else:
            lens = (f"f0 w{LENS_W} h{LENS_H} v=0 Ra=0 Rb=0 Rc=0 Rd=0 Re=0 "
                    "Eev0 Er1 Eb1 ")
            dist = "j0 a=0 b=0 c=0 d=0 e=0 g=0 t=0 Va=0 Vb=0 Vc=0 Vd=0 Vx=0 Vy=0 Vm5 "
        nom_pto = chemin_image(dossier, nom, sortie)
        out.append(f"i {lens}r0 p{pitch:.4f} y{yaw:.4f} TrX0 TrY0 TrZ0 {dist}n\"{nom_pto}\"")

    out += [
        "",
        "# specify variables that should be optimized",
        "v",
        "",
    ]
    sortie.write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"{sortie} écrit ({len(fichiers)} images, champ horizontal {hfov:.2f}°)")


main()
