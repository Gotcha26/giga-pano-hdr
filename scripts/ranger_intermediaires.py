"""Range les images intermédiaires d'un dossier de projets Hugin dans _a_supprimer/.

CONTEXTE
    Étape 4B, et après chaque rendu lancé depuis Hugin. Une image intermédiaire dont le travail est
    fait et vérifié n'a plus sa place dans le dossier de l'étape : elle pèse lourd (chaque image reprojetée a la
    taille de toute la toile) et ne sert qu'à relancer un calcul. Ce script ne supprime JAMAIS rien : il déplace
    dans <dossier>/_a_supprimer/ en conservant les chemins, et c'est l'utilisateur qui vide ce dossier quand il
    est sûr.

MODE OPÉRATOIRE
    Parcourt le dossier (récursivement) et range :
    - les images reprojetées par nona (f_NNNN.tif) ;
    - le fichier de réponse d'enblend qui les liste (liste_enblend.txt) ;
    - les images intermédiaires de l'assemblage par Hugin (*_exposure_layers_NNNN.tif).
    Jamais touchés : les projets .pto (légers, ils gardent l'historique des étapes), les panoramas rendus, les
    DNG, les PNG, les journaux, les tuiles, et _a_supprimer/ lui-même.

ENTRÉES
    DOSSIER       le dossier des projets ($P, ex. ...\\200mm\\Assemblage-Hugin)
    --apply       déplace réellement ; sans option, essai à blanc : liste ce qui serait rangé

SORTIES
    Console : une ligne par fichier (« à ranger » ou « rangé »), puis le nombre de fichiers et le volume en Go.
    Avec --apply : les fichiers sont déplacés dans DOSSIER/_a_supprimer/ avec leur sous-arborescence.

EXEMPLE
    python ranger_intermediaires.py D:\\Panoramas\\Assemblage-Hugin
    python ranger_intermediaires.py D:\\Panoramas\\Assemblage-Hugin --apply

Usage : python ranger_intermediaires.py DOSSIER [--apply]
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

CORBEILLE = "_a_supprimer"
INTERMEDIAIRES = (
    re.compile(r"f_\d+\.tif", re.IGNORECASE),                    # nona (rendre_projet.ps1, Hugin)
    re.compile(r"liste_enblend\.txt", re.IGNORECASE),            # fichier de réponse d'enblend
    re.compile(r".*_exposure_layers_\d+\.tif", re.IGNORECASE),   # Hugin, sortie « Calques »
)


def a_ranger(racine):
    """Liste triée des fichiers (chemins relatifs à racine) à ranger."""
    return sorted(
        f.relative_to(racine)
        for f in racine.rglob("*")
        if f.is_file()
        and f.relative_to(racine).parts[0] != CORBEILLE
        and any(m.fullmatch(f.name) for m in INTERMEDIAIRES)
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dossier")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    racine = Path(args.dossier)
    if not racine.is_dir():
        sys.exit(f"dossier introuvable : {racine}")

    fichiers = a_ranger(racine)
    octets = sum((racine / f).stat().st_size for f in fichiers)
    for f in fichiers:
        print(("rangé    " if args.apply else "à ranger ") + str(f))
        if args.apply:
            dest = racine / CORBEILLE / f
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(racine / f), str(dest))
    verbe = "rangé(s) dans " + CORBEILLE if args.apply else "à ranger (essai à blanc, ajouter --apply)"
    print(f"{len(fichiers)} fichier(s), {octets / 1024 ** 3:.2f} Go {verbe}")


if __name__ == "__main__":
    main()
