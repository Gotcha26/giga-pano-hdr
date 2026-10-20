"""Empaquète les deux pyramides de tuiles d'un panorama en un dossier autonome et un ZIP, prêts à mettre en ligne.

CONTEXTE
    Après 7B (tuiles contrôlées) et, le cas échéant, 7C (cadrage). L'hébergement reçoit un seul fichier ZIP,
    décompressé sur place (cPanel « Extraire ») dans la racine des panoramas. Format attendu par la visionneuse
    GigaPanoramaViewer : panorama.json version 1.

MODE OPÉRATOIRE
    1. lit la taille de chaque pyramide dans son .dzi et vérifie que son dossier _files existe ;
    2. copie les pyramides dans <Sortie>\\<Nom>\\hdr\\ (hdr.dzi, hdr_files\\) et <Sortie>\\<Nom>\\complet\\ ;
    3. écrit <Sortie>\\<Nom>\\panorama.json (UTF-8 sans BOM) : version, titre, chemins et tailles des deux .dzi,
       cadre (box) de la pleine résolution dans le HDR ;
    4. écrit <Sortie>\\<Nom>.zip, SANS compression (les tuiles le sont déjà), le dossier <Nom>\\ à la racine de
       l'archive : la décompression recrée <Nom>\\.
    Refuse un dossier <Nom> déjà présent : un nouveau rendu va sous un NOUVEAU nom, car les navigateurs gardent les
    tuiles en cache un an ; des tuiles remplacées sous le même nom ne seraient pas revues.

ENTRÉES
    NOM          nom du dossier en ligne : lettres, chiffres, - et _ (100 au plus), ex. pano-200mm-2026-10-20
    HDR          pyramide du HDR (.dzi)
    COMPLET      pyramide de la pleine résolution (.dzi)
    SORTIE       dossier où écrire <Nom>\\ et <Nom>.zip, ex. $P\\7_galerie
    --titre      titre affiché par la visionneuse (vide par défaut)
    --box X,Y,L  cadre de la pleine résolution dans le HDR, en largeurs du HDR (défaut 0,0,1 : sources cadrées
                 ensemble en 7C ; pour des sources non recadrées, la valeur donnée en 7C ou dans le guide)
    --sans-zip   écrit le dossier seulement

SORTIES
    <Sortie>\\<Nom>\\ (panorama.json, hdr\\, complet\\) et <Sortie>\\<Nom>.zip. Les pyramides d'origine ne sont pas
    modifiées.

EXEMPLE
    python empaqueter.py pano-200mm-2026-10-20 "$P\\7_tuiles\\hdr_cadre_webp\\hdr.dzi" "$P\\7_tuiles\\complet_cadre_webp\\complet.dzi" "$P\\7_galerie" --titre "Panorama du 200 mm"

Usage : python empaqueter.py NOM HDR.dzi COMPLET.dzi SORTIE [--titre TEXTE] [--box X,Y,L] [--sans-zip]
"""
import argparse
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("NOM", "Nom du dossier en ligne (lettres, chiffres, - et _), nouveau à chaque rendu", obligatoire=True),
    Arg("HDR", "Pyramide du HDR (.dzi)", type="chemin", obligatoire=True),
    Arg("COMPLET", "Pyramide de la pleine résolution (.dzi)", type="chemin", obligatoire=True),
    Arg("SORTIE", "Dossier où écrire <Nom>\\ et <Nom>.zip, ex. $P\\7_galerie", type="dossier", obligatoire=True),
    Arg("--titre", "Titre affiché par la visionneuse"),
    Arg("--box", "Cadre X,Y,L de la pleine résolution dans le HDR (0,0,1 : sources cadrées ensemble)", defaut="0,0,1"),
    Arg("--sans-zip", "Écrit le dossier seulement", type="drapeau"),
]

TOLERANCE_BOX = 0.01     # le cadre réel d'un panorama non recadré déborde de 0,0006


class Refus(Exception):
    pass


def lire_box(texte):
    try:
        valeurs = [float(v) for v in str(texte).replace(" ", "").split(",")]
    except ValueError:
        raise Refus(f"box : nombre illisible ({texte})")
    if len(valeurs) != 3:
        raise Refus("box : trois nombres attendus (x,y,largeur)")
    x, y, largeur = valeurs
    if not (0 <= x <= 1 and 0 <= y <= 1 and largeur > 0 and x + largeur <= 1 + TOLERANCE_BOX):
        raise Refus(f"box hors du cadre du HDR : 0 <= x, y <= 1, 0 < largeur, x + largeur <= 1 (tolérance {TOLERANCE_BOX})")
    return valeurs


def lire_dzi(chemin):
    """(largeur, hauteur, dossier des tuiles) d'une pyramide Deep Zoom."""
    chemin = Path(chemin)
    if not chemin.is_file():
        raise Refus(f"pyramide introuvable : {chemin}")
    taille = next((e for e in ET.parse(chemin).getroot().iter() if e.tag.split("}")[-1] == "Size"), None)
    if taille is None:
        raise Refus(f"taille absente du .dzi : {chemin}")
    tuiles = chemin.with_name(chemin.stem + "_files")
    if not tuiles.is_dir():
        raise Refus(f"dossier de tuiles introuvable : {tuiles}")
    return int(taille.get("Width")), int(taille.get("Height")), tuiles


def empaqueter(nom, hdr, complet, sortie, titre="", box=(0, 0, 1), zipper=True):
    """Écrit <sortie>/<nom>/ et, si zipper, <sortie>/<nom>.zip ; retourne (dossier, zip ou None, manifeste)."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", nom):
        raise Refus("nom invalide : lettres, chiffres, - et _ seulement (100 au plus)")
    h_l, h_h, h_tuiles = lire_dzi(hdr)
    c_l, c_h, c_tuiles = lire_dzi(complet)
    cible = Path(sortie) / nom
    if cible.exists():
        raise Refus(f"le dossier existe déjà : {cible} (un nouveau rendu va sous un nouveau nom)")

    (cible / "hdr").mkdir(parents=True)
    (cible / "complet").mkdir()
    shutil.copy2(hdr, cible / "hdr" / "hdr.dzi")
    shutil.copytree(h_tuiles, cible / "hdr" / "hdr_files")
    shutil.copy2(complet, cible / "complet" / "complet.dzi")
    shutil.copytree(c_tuiles, cible / "complet" / "complet_files")

    manifeste = {
        "version": 1,
        "titre": titre,
        "hdr": {"dzi": "hdr/hdr.dzi", "width": h_l, "height": h_h},
        "full": {"dzi": "complet/complet.dzi", "width": c_l, "height": c_h},
        "box": list(box),
    }
    # UTF-8 sans BOM : la visionneuse refuse un JSON qu'elle ne sait pas décoder
    (cible / "panorama.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    archive = None
    if zipper:
        archive = Path(sortie) / f"{nom}.zip"
        archive.unlink(missing_ok=True)
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as z:
            for f in sorted(cible.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(cible.parent).as_posix())
    return cible, archive, manifeste


def main():
    piloter(__doc__, ARGUMENTS, ecrit="<Sortie>\\<Nom>\\ (copie des pyramides, panorama.json) et <Nom>.zip", globals_=globals())
    ap = argparse.ArgumentParser()
    ap.add_argument("nom")
    ap.add_argument("hdr")
    ap.add_argument("complet")
    ap.add_argument("sortie")
    ap.add_argument("--titre", default="")
    ap.add_argument("--box", default="0,0,1")
    ap.add_argument("--sans-zip", action="store_true")
    args = ap.parse_args()
    try:
        cible, archive, m = empaqueter(args.nom, args.hdr, args.complet, args.sortie, args.titre,
                                       lire_box(args.box), zipper=not args.sans_zip)
    except Refus as e:
        sys.exit(f"{e} ; rien n'a été écrit")
    nb = sum(1 for f in cible.rglob("*") if f.is_file())
    print(f"Dossier : {cible} ({nb} fichiers)")
    print(f"  HDR {m['hdr']['width']} x {m['hdr']['height']} px, pleine résolution {m['full']['width']} x {m['full']['height']} px,"
          f" box {','.join(f'{v:g}' for v in m['box'])}")
    if archive:
        print(f"ZIP : {archive} ({archive.stat().st_size / 1e6:,.0f} Mo), à téléverser puis « Extraire » dans la racine des panoramas")


if __name__ == "__main__":
    main()
