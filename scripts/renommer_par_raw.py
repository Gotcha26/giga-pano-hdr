"""Renomme un export Lightroom en L{ligne}_C{colonne}_E{expo}.tif d'après le fichier RAW d'origine.

CONTEXTE
    Étapes 2D, 2F et 6A.2 (variante de renommer_pano.py). Chaque TIFF exporté par Lightroom porte, dans ses
    métadonnées (XMP-crs:RawFileName), le nom du RAW dont il provient. Un export déjà renommé (le « référentiel »)
    donne la correspondance RAW -> L_C_E ; on l'applique à un nouvel export, quels que soient son ordre, son
    nombre de fichiers ou la taille des images.
    Avantage sur renommer_pano.py : aucune dépendance au numéro de séquence ni à l'ordre de tri de Lightroom.
    Un sous-ensemble (échantillon de 12 images, vues centrées seules...) se renomme sans astuce.

MODE OPÉRATOIRE
    1. lit avec exiftool le RAW d'origine de chaque TIFF du référentiel et du nouvel export ;
    2. associe chaque fichier du nouvel export au nom L_C_E de son RAW dans le référentiel ;
    3. refuse d'agir si deux fichiers visent le même nom, si un RAW est absent du référentiel (avec --apply) ou
       si un nom cible existe déjà ;
    4. renomme, et écrit correspondance_raw.csv.

ENTRÉES
    REFERENCE      dossier déjà renommé (L_C_E), de la même prise de vue, OU table CSV (colonnes raw,lce)
    NOUVEL_EXPORT  dossier à renommer
    (sans option)  essai à blanc
    --apply        renomme et écrit correspondance_raw.csv dans le nouvel export
    --undo         restaure les noms d'origine depuis correspondance_raw.csv
    --table        (avec un dossier REFERENCE et un fichier CSV en second argument) sauvegarde la table raw,lce
                   pour pouvoir supprimer le dossier de référence

SORTIES
    Console : nombre de RAW connus, fichiers à renommer (aperçu), avertissements (fichiers sans RAW, RAW absents).
    Avec --apply : fichiers renommés + `correspondance_raw.csv`. Avec --table : le CSV demandé.

EXEMPLE
    python renommer_par_raw.py REFERENCE NOUVEL_EXPORT
    python renommer_par_raw.py REFERENCE NOUVEL_EXPORT --apply
    python renommer_par_raw.py REFERENCE TABLE.csv --table

Nécessite exiftool dans le PATH.

Usage : python renommer_par_raw.py REFERENCE NOUVEL_EXPORT [--apply | --undo]
                                   python renommer_par_raw.py REFERENCE TABLE.csv --table
"""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

LCE = re.compile(r"L\d+_C\d+_E\d\.tif", re.IGNORECASE)


def raw_names(dossier):
    """{nom de fichier: nom du RAW d'origine} pour tous les TIFF du dossier."""
    r = subprocess.run(["exiftool", "-json", "-XMP-crs:RawFileName", "-ext", "tif", str(dossier)],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode not in (0, 1) or not r.stdout.strip():
        sys.exit(f"exiftool n'a rien lu dans {dossier} : {r.stderr.strip()[:200]}")
    res = {}
    for ligne in json.loads(r.stdout):
        res[Path(ligne["SourceFile"]).name] = ligne.get("RawFileName")
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    options = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) != 2 or options - {"--apply", "--undo", "--table"}:
        sys.exit(__doc__)
    ref, nouveau = Path(args[0]), Path(args[1])

    if "--undo" in options:
        table = nouveau / "correspondance_raw.csv"
        if not table.exists():
            sys.exit(f"{table} introuvable : rien à annuler")
        with open(table, encoding="utf-8", newline="") as f:
            lignes = list(csv.DictReader(f))
        for l in lignes:
            (nouveau / l["nouveau"]).rename(nouveau / l["ancien"])
        print(f"{len(lignes)} fichiers restaurés")
        return

    # RAW -> nom L_C_E, d'après le référentiel (dossier déjà renommé, ou table CSV « raw,lce »)
    if ref.is_file():
        with open(ref, encoding="utf-8", newline="") as f:
            par_raw = {l["raw"]: l["lce"] for l in csv.DictReader(f)}
        if "--table" in options:
            sys.exit("--table s'applique à un dossier de référence, pas à un CSV")
    else:
        ref_raw = {nom: raw for nom, raw in raw_names(ref).items() if LCE.fullmatch(nom)}
        par_raw = {}
        for nom, raw in ref_raw.items():
            if raw is None:
                continue
            # le référentiel peut contenir plusieurs expositions d'un même RAW : impossible (un RAW = une image)
            if raw in par_raw:
                sys.exit(f"RAW en double dans le référentiel : {raw} ({par_raw[raw]} et {nom})")
            par_raw[raw] = nom
        if "--table" in options:
            sortie = Path(args[1])
            with open(sortie, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["raw", "lce"])
                w.writerows(sorted(par_raw.items(), key=lambda kv: kv[1]))
            print(f"{len(par_raw)} RAW -> table écrite dans {sortie}")
            return
    print(f"référentiel : {len(par_raw)} RAW connus")

    exports = raw_names(nouveau)
    plan, inconnus, sans_raw = [], [], []
    for nom, raw in sorted(exports.items()):
        if LCE.fullmatch(nom):
            continue                              # déjà renommé
        if raw is None:
            sans_raw.append(nom)
        elif raw not in par_raw:
            inconnus.append((nom, raw))
        else:
            plan.append((nom, par_raw[raw]))
    cibles = [c for _, c in plan]
    if len(set(cibles)) != len(cibles):
        sys.exit("deux fichiers correspondent au même RAW (export en double ?) : abandon")
    if sans_raw or inconnus:
        print(f"{len(sans_raw)} fichiers sans RAW d'origine, {len(inconnus)} RAW absents du référentiel")
        for nom, raw in inconnus[:5]:
            print(f"   {nom} <- {raw}")
        if "--apply" in options:
            sys.exit("abandon : corriger l'export ou le référentiel")
    print(f"{len(plan)} fichiers à renommer")
    for ancien, nouv in plan[:3] + (plan[-2:] if len(plan) > 5 else []):
        print(f"   {ancien}  ->  {nouv}")
    if "--apply" not in options:
        print("Essai à blanc : rien n'a été modifié (--apply pour appliquer)")
        return
    for ancien, nouv in plan:
        if (nouveau / nouv).exists():
            sys.exit(f"{nouv} existe déjà dans {nouveau} : abandon (rien n'a été renommé)")
    for ancien, nouv in plan:
        (nouveau / ancien).rename(nouveau / nouv)
    with open(nouveau / "correspondance_raw.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ancien", "nouveau"])
        w.writerows(plan)
    print(f"Fait. Correspondance écrite dans {nouveau / 'correspondance_raw.csv'}")


main()
