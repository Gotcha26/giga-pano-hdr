"""Contrôle un export Lightroom : réglages uniformes, RAW complets, dimensions, profil, curseurs de tonalité à 0.

CONTEXTE
    Étapes 2E et 6A.2 (vérifier l'export). Un réglage identique ne garantit pas un rendu identique (encadré de 2B) :
    ce script vérifie la moitié qui se lit, les réglages enregistrés dans chaque TIFF (XMP crs:*). L'autre moitié, le
    rendu, se juge avec ecart_paires.py et une vue d'ensemble à petite taille (6C.1). Il a repéré, sur ce panorama,
    des Point Color posés par erreur sur deux images, et les curseurs de tonalité laissés à une autre valeur que 0.

MODE OPÉRATOIRE
    1. lit avec exiftool les réglages de développement de chaque TIFF du dossier ;
    2. compare les jeux de réglages : liste les champs qui diffèrent d'une image à l'autre, avec les images en
       minorité. Le filtre Dust Removal et les retouches de taches sont exclus (ils diffèrent par nature) ;
    3. contrôle que les RAW d'origine sont tous distincts et, avec --table, qu'il n'en manque aucun ;
    4. contrôle les dimensions et le profil de couleur ;
    5. affiche les valeurs communes des curseurs clés, et signale ceux que le guide impose à 0 (Correction de la
       brume, Exposition, Contraste, Hautes lumières, Ombres, Blancs, Noirs) ou à une valeur fixe (balance des blancs).
    Code de sortie : 0 si tout est conforme, 1 sinon.

ENTRÉES
    DOSSIER      dossier des TIFF (déjà renommés L_C_E, ou sortis de Lightroom)
    --table CSV  table raw,lce (table_raw_LCE.csv) : nomme les images L_C_E même avant renommage, et contrôle qu'aucune
                 des 222 vues centrées E0 ne manque
    --ignorer P  préfixe de champ à ne pas comparer (répétable) : par exemple PointColors pour accepter des Point Color
                 voulus sur quelques images
    Constantes en tête de script : TONALITE (curseurs à 0), IGNORES, PREFIXES_IGNORES.

SORTIES
    Console : effectifs, champs divergents et images concernées, valeurs communes des curseurs clés, avertissements.

EXEMPLE
    python controle_reglages_export.py "$T\\Export-TIFF-H" --table "$P\\table_raw_LCE.csv"

Dépendance : exiftool dans le PATH.

Usage : python controle_reglages_export.py DOSSIER [--table TABLE.csv] [--ignorer PREFIXE ...]
"""
import argparse
import csv
import re
import subprocess
import sys
import zlib
from collections import Counter
from pathlib import Path

TONALITE = ("Dehaze", "Exposure2012", "Contrast2012", "Highlights2012", "Shadows2012", "Whites2012", "Blacks2012")
CLES = TONALITE + ("Clarity2012", "Texture", "Vibrance", "Saturation", "WhiteBalance", "ColorTemperature", "Tint",
                   "CameraProfile", "LensProfileEnable", "AutoLateralCA")
IGNORES = {"SourceFile", "RawFileName", "CameraProfileDigest", "ImageWidth", "ImageHeight", "ProfileDescription",
           "AllowFilters", "CompatibleVersion"}
PREFIXES_IGNORES = ("FilterList", "RetouchArea")
BALANCES_MOBILES = {"Auto", "As Shot"}
RE_LCE = re.compile(r"(L\d+_C\d+_E\d+)")


def lire_table(chemin):
    """Table raw,lce -> dict RAW -> 'L1_C06_E0' (sans extension)."""
    with open(chemin, encoding="utf-8") as f:
        return {r["raw"]: r["lce"].replace(".tif", "") for r in csv.DictReader(f)}


def lire_reglages(dossier):
    """Une ligne par TIFF : réglages XMP crs, dimensions, profil (exiftool, sortie CSV)."""
    cmd = ["exiftool", "-csv", "-XMP-crs:all", "-ImageWidth", "-ImageHeight", "-icc_profile:ProfileDescription",
           "-ext", "tif", str(dossier)]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if res.returncode not in (0, 1) or not res.stdout.strip():
        raise SystemExit(f"exiftool n'a rien lu dans {dossier} ({res.stderr.strip()[:200]})")
    return list(csv.DictReader(res.stdout.splitlines()))


def nom_image(ligne, table=None):
    """Nom lisible : L_C_E d'après le nom du fichier, sinon d'après le RAW et la table, sinon le nom du fichier."""
    fichier = Path(ligne["SourceFile"]).name
    m = RE_LCE.search(fichier)
    if m:
        return m.group(1)
    if table and ligne.get("RawFileName") in table:
        return table[ligne["RawFileName"]]
    return fichier


def champs_comparables(ligne, ignorer=()):
    return [c for c in ligne
            if c not in IGNORES and not c.startswith(PREFIXES_IGNORES + tuple(ignorer))]


def divergences(lignes, ignorer=()):
    """{champ: Counter(valeur -> effectif)} pour les champs qui prennent plus d'une valeur."""
    if not lignes:
        return {}
    res = {}
    for c in champs_comparables(lignes[0], ignorer):
        cnt = Counter(l.get(c, "") for l in lignes)
        if len(cnt) > 1:
            res[c] = cnt
    return res


def images_en_minorite(lignes, champ, table=None):
    """Noms des images dont la valeur du champ n'est pas la plus fréquente."""
    usuel = Counter(l.get(champ, "") for l in lignes).most_common(1)[0][0]
    return sorted(nom_image(l, table) for l in lignes if l.get(champ, "") != usuel)


def court(valeur, n=30):
    """Valeur abrégée ; une empreinte distingue deux valeurs longues qui commencent pareil."""
    if len(valeur) <= n + 10:
        return valeur
    return f"{valeur[:n]}…#{zlib.crc32(valeur.encode()) % 65536:04x}"


def _nul(valeur):
    try:
        return float(valeur) == 0
    except ValueError:
        return False


def avertissements(lignes):
    """Curseurs que le guide impose à 0 ou fixes, et qui ne le sont pas sur toutes les images."""
    avert = []
    for c in TONALITE:
        valeurs = Counter(l.get(c, "") for l in lignes)
        if any(not _nul(v) for v in valeurs):
            avert.append(f"{c} n'est pas à 0 : {dict(valeurs)} (le guide impose 0, voir 2B)")
    for v in Counter(l.get("WhiteBalance", "") for l in lignes):
        if v in BALANCES_MOBILES:
            avert.append(f"balance des blancs « {v} » : elle doit être fixe (voir 2B)")
    return avert


def couverture(lignes, table):
    """(manquants, en trop) : RAW des vues centrées E0 de la table absents de l'export, et RAW hors table."""
    e0 = {raw for raw, lce in table.items() if lce.endswith("_E0")}
    presents = {l.get("RawFileName", "") for l in lignes}
    return sorted(e0 - presents), sorted(presents - e0)

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("DOSSIER", "Dossier des TIFF exportés", type="dossier", config="export_h"),
    Arg("--table", "Table raw,lce (table_raw_LCE.csv)", type="chemin", config="table"),
    Arg("--ignorer", "Préfixe de champ à ne pas comparer (ex. PointColors)"),
]
piloter(__doc__, ARGUMENTS, ecrit=None, globals_=globals())

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("dossier")
    p.add_argument("--table")
    p.add_argument("--ignorer", action="append", default=[])
    a = p.parse_args(argv)

    table = lire_table(a.table) if a.table else None
    lignes = lire_reglages(a.dossier)
    ok = True
    print(f"{len(lignes)} TIFF dans {a.dossier}")

    raws = [l.get("RawFileName", "") for l in lignes]
    doublons = [r for r, n in Counter(raws).items() if n > 1 or not r]
    print(f"RAW distincts : {len(set(raws))}" + (f" ; doublons ou absents : {doublons[:5]}" if doublons else ""))
    ok &= not doublons
    if table:
        manquants, en_trop = couverture(lignes, table)
        print(f"couverture des E0 de la table : manquants {len(manquants)}, hors table {len(en_trop)}")
        if manquants or en_trop:
            ok = False
            for r in (manquants + en_trop)[:10]:
                print(f"  {r}")

    dims = Counter(f"{l.get('ImageWidth')}x{l.get('ImageHeight')}" for l in lignes)
    profils = Counter(l.get("ProfileDescription", "") for l in lignes)
    print(f"dimensions : {dict(dims)} ; profil : {dict(profils)}")
    ok &= len(dims) == 1 and len(profils) == 1

    div = divergences(lignes, a.ignorer)
    print(f"\nréglages qui diffèrent d'une image à l'autre (hors Dust Removal et retouches de taches) : {len(div)}")
    for champ, cnt in div.items():
        mino = images_en_minorite(lignes, champ, table)
        apercu = ", ".join(mino[:12]) + (f" … (+{len(mino) - 12})" if len(mino) > 12 else "")
        valeurs = ", ".join(f"{court(v)!r} x{n}" for v, n in cnt.most_common(4))
        print(f"  {champ} : {valeurs}\n    images en minorité : {apercu}")
    ok &= not div

    print("\nvaleurs des curseurs clés :")
    for c in CLES:
        if c in lignes[0]:
            print(f"  {c} : {dict(Counter(l[c] for l in lignes))}")

    avert = avertissements(lignes)
    for m in avert:
        print(f"ATTENTION : {m}")
    ok &= not avert
    print("\n" + ("conforme" if ok else "NON conforme : voir les lignes ci-dessus"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
