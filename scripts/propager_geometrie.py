"""Construit le projet à 7 expositions (piles) à partir du projet optimisé de l'exposition centrale.

CONTEXTE
    Étape 5A (HDR). La géométrie a été optimisée une fois, sur les images E0 (vue centrée). Ce script la reporte
    sur les 7 expositions de chaque position : on n'a ainsi qu'un seul « maître », et le HDR est assemblé sur
    exactement la même géométrie. La géométrie est exprimée en angles : elle ne dépend pas de la taille des images.

MODE OPÉRATOIRE
    - positions (yaw, pitch, roll) : reprises de chaque image E0 du projet optimisé ;
    - objectif (champ de vue, a, b, c, d, e, g, t, vignettage) : repris de l'image 0, partagé par les 1554 images ;
    - chaque pile = E0 (porte la position) + E1..E6 liées à E0, avec leur propre Eev (table EV) ;
    - noms d'images : `_E0` remplacé par `_E1`... `_E6` ; chemins recalculés relativement au projet de sortie ;
    - taille du panorama : réduite à LARGEUR pixels (hauteur au même rapport).

ENTRÉES
    optimise_E0.pto   projet optimisé de la vue centrée (images nommées *_E0*)
    sortie.pto        projet à écrire
    LARGEUR           largeur du panorama en pixels (défaut 20000)
    LARG_IMAGE HAUT_IMAGE   taille en pixels des images à assembler, si elle diffère de celle du projet
                      optimisé (par exemple images réduites à l'export de Lightroom).
    Constantes en tête de script : LARGEUR_DEFAUT, EXPOS = 7, EV, EEV_E0.

SORTIES
    sortie.pto (aucune variable à optimiser) + message « N images, M piles, panorama X px ». Arrêt si un nom
    d'image n'est pas un _E0.

EXEMPLE
    python propager_geometrie.py pano_grille_opt4.pto 5_hdr\\pano_HDR_opt4.pto 20000

Usage : python propager_geometrie.py optimise_E0.pto sortie.pto [LARGEUR [LARG_IMAGE HAUT_IMAGE]]
"""
import os
import re
import sys
from pathlib import Path

LARGEUR_DEFAUT = 20000
EXPOS = 7
# compensation d'exposition (EV) par numéro d'exposition, lue dans l'EXIF
EV = {0: 0, 1: -3, 2: -2, 3: -1, 4: 1, 5: 2, 6: 3}
EEV_E0 = 13.2877        # log2(f/10 ^ 2 / (1/100 s)) à ISO 100, exposition 0

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("optimise_E0.pto", "Projet optimisé de la vue centrée", type="pto", config="maitre", phase="3_optimisation"),
    Arg("sortie.pto", "Projet à écrire (toutes les expositions)", type="pto"),
    Arg("LARGEUR", "Largeur du panorama en pixels", type="entier", config="largeur_hdr", defaut=20000),
    Arg("LARG_IMAGE", "Largeur des images à assembler, si différente du projet", type="entier"),
    Arg("HAUT_IMAGE", "Hauteur des images à assembler", type="entier"),
]
piloter(__doc__, ARGUMENTS, ecrit='le projet de sortie', globals_=globals())

entree, sortie = sys.argv[1], sys.argv[2]
largeur = int(sys.argv[3]) if len(sys.argv) > 3 else LARGEUR_DEFAUT

lignes = open(entree, encoding="utf-8").read().splitlines()
images = [l for l in lignes if l.startswith("i ")]
ligne_p = next(l for l in lignes if l.startswith("p "))


def champ(ligne, cle):
    m = re.search(rf" {cle}(\S+)", ligne)
    return m.group(1) if m else None


# --- objectif : valeurs explicites de l'image 0, reprises telles quelles
ref = images[0]
objectif = {k: champ(ref, k) for k in ("v", "a", "b", "c", "d", "e", "g", "t",
                                       "Va", "Vb", "Vc", "Vd", "Vx", "Vy")}
w, h = champ(ref, "w"), champ(ref, "h")
if len(sys.argv) > 5:
    w, h = sys.argv[4], sys.argv[5]
if None in objectif.values():
    sys.exit(f"paramètre d'objectif introuvable dans la première image : {objectif}")

# --- ligne p : même projection et champ, nouvelle taille
pw, ph = int(champ(ligne_p, "w")), int(champ(ligne_p, "h"))
nouvelle_p = re.sub(r" w\d+", f" w{largeur}", ligne_p, count=1)
nouvelle_p = re.sub(r" h\d+", f" h{round(largeur * ph / pw)}", nouvelle_p, count=1)

sortie_l = ["# hugin project file", "#hugin_ptoversion 2", nouvelle_p, "m i0", ""]
for k, src in enumerate(images):
    nom = champ(src, "n").strip('"')
    if "_E0" not in nom:
        sys.exit(f"nom inattendu (pas _E0) : {nom}")
    # chemin relatif au projet source -> relatif au projet de sortie (sans effet s'ils sont dans le même dossier)
    img = Path(entree).resolve().parent / nom
    try:
        nom = os.path.relpath(img, Path(sortie).resolve().parent)
    except ValueError:                   # lecteurs différents : chemin absolu
        nom = str(img)
    y, p, r = champ(src, "y"), champ(src, "p"), champ(src, "r")
    pile = k * EXPOS                     # indice de E0 dans le nouveau projet
    for expo in range(EXPOS):
        idx = pile + expo
        nom_e = nom.replace("_E0", f"_E{expo}")
        eev = EEV_E0 - EV[expo]
        if idx == 0:
            lentille = (f"v{objectif['v']} Ra0 Rb0 Rc0 Rd0 Re0 ")
            dist = (f"j0 a{objectif['a']} b{objectif['b']} c{objectif['c']} d{objectif['d']} "
                    f"e{objectif['e']} g{objectif['g']} t{objectif['t']} "
                    f"Va{objectif['Va']} Vb{objectif['Vb']} Vc{objectif['Vc']} Vd{objectif['Vd']} "
                    f"Vx{objectif['Vx']} Vy{objectif['Vy']} Vm5 ")
        else:
            lentille = "v=0 Ra=0 Rb=0 Rc=0 Rd=0 Re=0 "
            dist = "j0 a=0 b=0 c=0 d=0 e=0 g=0 t=0 Va=0 Vb=0 Vc=0 Vd=0 Vx=0 Vy=0 Vm5 "
        if expo == 0:
            pos = f"r{r} p{p} y{y} TrX0 TrY0 TrZ0 "
        else:
            pos = f"r={pile} p={pile} y={pile} TrX={pile} TrY={pile} TrZ={pile} "
        sortie_l.append(f"i w{w} h{h} f0 {lentille}Eev{eev:.4f} Er1 Eb1 {pos}{dist}n\"{nom_e}\"")

sortie_l += ["", "# specify variables that should be optimized", "v", ""]
open(sortie, "w", encoding="utf-8", newline="\n").write("\n".join(sortie_l))
print(f"{len(images) * EXPOS} images, {len(images)} piles, panorama {largeur} px -> {sortie}")
print(f"objectif repris : v={objectif['v']} a={objectif['a']} b={objectif['b']} c={objectif['c']}")
