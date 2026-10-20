"""Reporte sur la pleine résolution le recadrage décidé dans Lightroom sur le HDR (20 000 px).

CONTEXTE
    Phase 7 (diffuser), cadrage facultatif des deux sources. Le cadrage est un choix de composition, fait à l'œil
    sur la vue d'ensemble dans Lightroom. Lightroom le range en fractions de l'image (CropLeft, CropTop,
    CropRight, CropBottom, entre 0 et 1) : indépendantes de l'échelle, elles valent pour le HDR comme pour la
    pleine résolution.

MODE OPÉRATOIRE
    1. lit le recadrage (voir « Deux sources ») ;
    2. le convertit en pixels HDR entiers, puis en pixels de la toile pleine résolution, puis en pixels du TIFF
       de multiblend (rogné à sa zone utile) ;
    3. vérifie que le cadre tient dans la zone utile de la pleine résolution (sinon : arrêt, aucune commande) ;
    4. imprime les commandes PowerShell `vips extract_area` qui recadrent les deux sources sur le même rectangle,
       et la valeur `&box=` à donner à la visionneuse.

    Deux sources pour lire le recadrage :
      1. le CATALOGUE Lightroom (.lrcat), sans export ni sidecar : le script demande l'emplacement du catalogue
         et le nom du fichier (DNG de la fusion HDR) ; il ouvre le catalogue en lecture seule ;
      2. un DNG (ou un .xmp) exporté temporairement, lu avec exiftool : --dng FICHIER.

ENTRÉES
    --catalogue  catalogue Lightroom (demandé si absent)
    --fichier    nom (ou partie du nom) de l'image : « pano_20000_E0-HDR » ou « pano_20000_E0-HDR.dng »
                 (demandé si absent ; si plusieurs images correspondent, le script les numérote)
    --dng        lire le recadrage dans ce DNG / .xmp (exiftool dans le PATH) au lieu du catalogue
    --pleine     toile de la pleine résolution                         (défaut 90112x22528)
    --zone       zone utile du TIFF de multiblend dans la toile, x,y,largeur x hauteur
                                                                        (défaut 1454,1111,88658x20312)
    --hdr        taille de la toile HDR, si elle ne se lit pas (fichier .xmp seul)
  --origine-hdr  X,Y : position du HDR dans la toile HDR, quand le HDR vient de calques de multiblend (boite englobante
               de la toile, pas la toile entiere ; defaut 0,0). Origine = le "x y" de `vips find_trim` sur un calque.
  --toile-hdr  LxH : taille de la toile HDR (defaut : celle du HDR lu) ; a donner avec --origine-hdr (ex. 20000x5000)
    --controle   (facultatif, indicatif) mesure le vide laissé aux bords par un cadrage déjà fait : lit le canal
                 alpha de la pleine résolution recadrée (4 bandes) réduit 64 fois ; nécessite vips et Pillow.
                 Ne change rien et ne juge pas : un peu de noir dans les coins peut être un choix de composition.
    --vips       chemin de vips.exe pour --controle (défaut D:\\Outils\\libvips\\vips-dev-8.18\\bin\\vips.exe)
    Constantes en tête de script : PLEINE_DEFAUT, ZONE_DEFAUT.

SORTIES
    Sur la console seulement (le script ne modifie rien) : fractions Lightroom, rectangle HDR, rectangle sur la
    toile pleine résolution et dans le TIFF multiblend, commandes `vips extract_area`, valeur `&box=`.
    Avec --controle : surface vide et vide maximal à chaque coin.

À SAVOIR
    Prendre le DNG de la fusion HDR (celui dont la taille est 20 000 x 5 000, la toile entière), pas un TIFF
    déjà exporté recadré : il ne porte plus de recadrage. Fermer Lightroom avant, si possible : le catalogue
    est lu tel qu'il est sur le disque. Un recadrage avec rotation n'est pas pris en charge.

Usage : python cadrage_lightroom.py [--catalogue CAT.lrcat] [--fichier NOM] [--dng FICHIER]
                                    [--pleine LxH] [--zone X,Y,LxH] [--hdr LxH]
                                    [--origine-hdr X,Y --toile-hdr LxH]
        python cadrage_lightroom.py --controle COMPLET_CADRE.tif [--vips vips.exe]
"""
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

PLEINE_DEFAUT = (90112, 22528)
ZONE_DEFAUT = (1454, 1111, 88658, 20312)
EXTENSIONS = {".dng", ".tif", ".tiff", ".jpg", ".jpeg", ".psd", ".png"}
CLES = ("Left", "Top", "Right", "Bottom", "Angle")


def lire_options(argv):
    opts, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if not a.startswith("--") or i + 1 >= len(argv) or a[2:] not in (
                "catalogue", "fichier", "dng", "pleine", "zone", "hdr", "origine-hdr", "toile-hdr", "controle", "vips"):
            sys.exit(__doc__)
        opts[a[2:]] = argv[i + 1].strip('"')
        i += 2
    return opts


def demander(question, defaut=None):
    reponse = input(f"{question}" + (f" [{defaut}] " if defaut else " ")).strip().strip('"')
    return reponse or defaut or sys.exit("Réponse vide : arrêt.")


def entiers(texte, n, nom):
    nombres = [int(x) for x in re.split(r"[x,X; ]+", texte.strip()) if x]
    if len(nombres) != n:
        sys.exit(f"--{nom} : {n} nombres attendus, reçu « {texte} ».")
    return tuple(nombres)


def recadrage_depuis_lua(texte):
    """{Left, Top, Right, Bottom, Angle} lus dans le texte Lua des réglages de développement (vide si aucun)."""
    trouve = dict(re.findall(r"\bCrop(Left|Top|Right|Bottom|Angle) = (-?[\d.]+(?:[eE][-+]?\d+)?)", texte or ""))
    return {k: float(v) for k, v in trouve.items()}


def lire_catalogue(chemin, nom):
    """Retourne (description, largeur, hauteur, recadrage) de l'image choisie dans le catalogue."""
    chemin = Path(chemin)
    if not chemin.is_file():
        sys.exit(f"Catalogue introuvable : {chemin}")
    if any(chemin.with_name(chemin.name + s).exists() for s in ("-wal", "-journal")):
        print("ATTENTION : Lightroom semble ouvert (journal présent) : des réglages récents peuvent manquer. "
              "Le fermer pour être sûr.")
    base, ext = nom, None
    if Path(nom).suffix.lower() in EXTENSIONS:
        base, ext = Path(nom).stem, Path(nom).suffix.lower().lstrip(".")
    sql = """select i.id_local, f.baseName, f.extension, i.fileWidth, i.fileHeight, i.orientation,
                    d.fileWidth, d.fileHeight, d.text, ro.absolutePath, fo.pathFromRoot
             from Adobe_images i
             join AgLibraryFile f on f.id_local = i.rootFile
             join AgLibraryFolder fo on fo.id_local = f.folder
             join AgLibraryRootFolder ro on ro.id_local = fo.rootFolder
             left join Adobe_imageDevelopSettings d on d.id_local = i.developSettingsIDCache
             where f.baseName like ? escape '\\' and (? is null or lower(f.extension) = ?)
             order by i.id_local desc limit 30"""
    motif = "%" + base.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    base_de_donnees = sqlite3.connect(chemin.as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        lignes = base_de_donnees.execute(sql, (motif, ext, ext)).fetchall()
    except sqlite3.Error as e:
        sys.exit(f"Lecture du catalogue impossible ({e}). Exporter un DNG temporaire et utiliser --dng.")
    finally:
        base_de_donnees.close()
    if not lignes:
        sys.exit(f"Aucune image « {nom} » dans ce catalogue.")

    candidats = []
    for (_, bn, ex, lf, hf, orient, dl, dh, texte, racine, rel) in lignes:
        crop = recadrage_depuis_lua(texte)
        candidats.append({"desc": f"{racine}{rel}{bn}.{ex}", "l": dl or lf, "h": dh or hf,
                          "crop": crop, "orient": orient})
    if len(candidats) > 1:
        print("Plusieurs images correspondent :")
        for n, c in enumerate(candidats, 1):
            etat = "recadrée" if c["crop"] else "sans recadrage"
            print(f"  {n}. {c['desc']}  ({int(c['l'])} x {int(c['h'])}, {etat})")
        premier = next((n for n, c in enumerate(candidats, 1) if c["crop"]), 1)   # par défaut : la première recadrée
        choix = demander("Numéro de l'image à lire ?", str(premier))
        if not choix.isdigit() or not 1 <= int(choix) <= len(candidats):
            sys.exit("Numéro hors liste.")
        choix = int(choix)
        c = candidats[choix - 1]
    else:
        c = candidats[0]
    if c["orient"] not in (None, "AB"):
        print(f"ATTENTION : orientation « {c['orient']} » : le script suppose une image non pivotée.")
    return c["desc"], c["l"], c["h"], c["crop"]


def lire_dng(chemin, taille_hdr):
    """Retourne (description, largeur, hauteur, recadrage) d'un DNG ou d'un .xmp via exiftool."""
    r = subprocess.run(["exiftool", "-json", "-n", "-G1", "-a", "-XMP-crs:all", "-ImageWidth", "-ImageHeight",
                        str(chemin)], capture_output=True, text=True, encoding="utf-8")
    if not r.stdout.strip():
        sys.exit(f"exiftool n'a rien lu dans {chemin} : {r.stderr.strip()[:200]}")
    meta = json.loads(r.stdout)[0]
    crop = {k: float(meta[f"XMP-crs:Crop{k}"]) for k in CLES if f"XMP-crs:Crop{k}" in meta}
    largeurs = [v for k, v in meta.items() if k.endswith(":ImageWidth") and isinstance(v, (int, float))]
    hauteurs = [v for k, v in meta.items() if k.endswith(":ImageHeight") and isinstance(v, (int, float))]
    if taille_hdr:
        largeur, hauteur = taille_hdr
    elif largeurs and hauteurs:
        largeur, hauteur = max(largeurs), max(hauteurs)   # le DNG porte aussi des vignettes : on garde la plus grande
    else:
        sys.exit("Taille de l'image illisible dans ce fichier : donner --hdr 20000x5000.")
    return str(chemin), largeur, hauteur, crop


def controler_vide(fichier, vips):
    """Indicatif : vide (alpha nul) laissé aux quatre bords d'une pleine résolution recadrée, à 1/64 de résolution."""
    import tempfile
    from PIL import Image
    facteur = 64
    if not Path(vips).is_file():
        sys.exit(f"vips introuvable : {vips} (--vips)")
    with tempfile.TemporaryDirectory() as dossier:
        petit, alpha = Path(dossier) / "petit.v", Path(dossier) / "alpha.png"
        for commande in ([vips, "shrink", str(fichier), str(petit), str(facteur), str(facteur)],
                         [vips, "extract_band", str(petit), str(alpha), "3"]):
            r = subprocess.run(commande, capture_output=True, text=True, encoding="utf-8")
            if r.returncode:
                sys.exit(f"vips a échoué ({commande[1]}) : {r.stderr.strip()[:300]} "
                         "(le fichier doit avoir 4 bandes, dont l'alpha)")
        im = Image.open(alpha)
        largeur, hauteur = im.size
        maxi = 255 if im.mode == "L" else 65535
        donnees = list(getattr(im, "get_flattened_data", im.getdata)())
    vide = [[donnees[y * largeur + x] < maxi / 2 for x in range(largeur)] for y in range(hauteur)]
    total = sum(map(sum, vide))

    def serie(cases):
        """Nombre de cases vides consécutives depuis le début de la série."""
        n = 0
        for v in cases:
            if not v:
                break
            n += 1
        return n

    # Par coin, dans son quart d'image : largeur et hauteur maximales du vide qui part du coin.
    moitie_x, moitie_y = largeur // 2, hauteur // 2
    coins = {}
    for nom, (haut, gauche) in {"haut-gauche": (True, True), "haut-droite": (True, False),
                                "bas-gauche": (False, True), "bas-droite": (False, False)}.items():
        ys = range(moitie_y) if haut else range(hauteur - 1, hauteur - 1 - moitie_y, -1)
        xs = range(moitie_x) if gauche else range(largeur - 1, largeur - 1 - moitie_x, -1)
        coins[nom] = (max(serie(vide[y][x] for x in xs) for y in ys) * facteur,
                      max(serie(vide[y][x] for y in ys) for x in xs) * facteur)
    print(f"\nVide aux bords de {fichier} (indicatif, résolution 1/{facteur}) :")
    print(f"  surface vide : {100 * total / (largeur * hauteur):.3f} % ({total * facteur * facteur / 1e6:.2f} Mpx)")
    for nom, (l, h) in coins.items():
        print(f"  coin {nom:11s}: " + (f"vide jusqu'à {l} px en largeur et {h} px en hauteur" if l or h else "aucun vide"))
    print("Ce contrôle n'impose rien : un peu de noir dans les coins peut être voulu pour garder la matière "
          "sur toute la largeur.")

from pilotage.arguments import Arg, piloter

ARGUMENTS = [
    Arg("--catalogue", "Catalogue Lightroom .lrcat (demandé si absent)", type="chemin"),
    Arg("--fichier", "Nom (ou partie du nom) de l'image HDR dans le catalogue"),
    Arg("--dng", "Lire le recadrage dans ce DNG / .xmp au lieu du catalogue", type="chemin"),
    Arg("--pleine", "Toile de la pleine résolution, LxH"),
    Arg("--zone", "Zone utile du TIFF de multiblend dans la toile : x,y,LxH"),
    Arg("--origine-hdr", "X,Y : position du HDR dans la toile HDR (calques de multiblend)"),
    Arg("--toile-hdr", "LxH : taille de la toile HDR, avec --origine-hdr"),
    Arg("--controle", "Mesure le vide par coin d'une pleine résolution recadrée", type="chemin"),
    Arg("--vips", "Chemin de vips.exe (avec --controle)", type="chemin"),
]
piloter(__doc__, ARGUMENTS, ecrit=None, globals_=globals())

def main():
    sys.stdout.reconfigure(errors="replace")
    opts = lire_options(sys.argv[1:])
    if "controle" in opts:
        controler_vide(opts["controle"], opts.get("vips") or r"D:\Outils\libvips\vips-dev-8.18\bin\vips.exe")
        return
    pleine = entiers(opts.get("pleine") or "x".join(map(str, PLEINE_DEFAUT)), 2, "pleine")
    zone = entiers(opts.get("zone") or "{},{},{}x{}".format(*ZONE_DEFAUT), 4, "zone")
    taille_hdr = entiers(opts["hdr"], 2, "hdr") if opts.get("hdr") else None

    if "dng" in opts:
        desc, W, H, crop = lire_dng(opts["dng"], taille_hdr)
    else:
        cat = opts.get("catalogue") or demander("Emplacement du catalogue Lightroom (.lrcat) ?")
        nom = opts.get("fichier") or demander("Nom du fichier (ex. pano_20000_E0-HDR) ?")
        desc, W, H, crop = lire_catalogue(cat, nom)
        if taille_hdr:
            W, H = taille_hdr
    W, H = int(round(W)), int(round(H))

    print(f"\nImage lue : {desc}\nTaille de référence (toile HDR) : {W} x {H} px")
    if not crop:
        sys.exit("Aucun recadrage enregistré pour cette image. Si c'est un TIFF exporté déjà recadré, prendre "
                 "le DNG de la fusion HDR (le TIFF réimporté porte la taille recadrée, pas le recadrage).")
    if abs(crop.get("Angle", 0)) > 1e-6:
        sys.exit(f"Le recadrage comporte une rotation ({crop['Angle']}°) : non pris en charge "
                 "(un décalage d'horizon se corrige dans Hugin, avant le rendu).")
    gauche, haut = crop.get("Left", 0.0), crop.get("Top", 0.0)
    droite, bas = crop.get("Right", 1.0), crop.get("Bottom", 1.0)
    print(f"Fractions Lightroom : gauche {gauche:.6f}  haut {haut:.6f}  droite {droite:.6f}  bas {bas:.6f}")

    # Rectangle en pixels HDR entiers : c'est ce que Lightroom arrondit lui-même à l'export.
    x0, x1 = round(gauche * W), round(droite * W)
    y0, y1 = round(haut * H), round(bas * H)
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        sys.exit("Rectangle de recadrage vide : fractions incohérentes.")
    print(f"\nHDR  : x={x0} y={y0} largeur={w} hauteur={h}   (rapport {w / h:.4f}:1)")

    # HDR fusionné à partir de calques de multiblend : le HDR est la boîte englobante de la toile HDR, pas la toile.
    # --origine-hdr donne sa position dans la toile HDR, --toile-hdr la taille de cette toile (défaut : celle du HDR).
    ox, oy = entiers(opts["origine-hdr"], 2, "origine-hdr") if opts.get("origine-hdr") else (0, 0)
    TW, TH = entiers(opts["toile-hdr"], 2, "toile-hdr") if opts.get("toile-hdr") else (W, H)
    if (ox, oy) != (0, 0):
        print(f"HDR placé en ({ox} ; {oy}) dans une toile de {TW} x {TH} px")
    sx, sy = pleine[0] / TW, pleine[1] / TH
    if abs(sx - sy) / sx > 1e-3:
        print(f"ATTENTION : échelles différentes en x ({sx:.5f}) et en y ({sy:.5f}) : la toile HDR et la toile "
              "pleine résolution n'ont pas le même rapport. Vérifier --pleine, --hdr et --toile-hdr.")
    X0, X1 = round((x0 + ox) * sx), round((x1 + ox) * sx)
    Y0, Y1 = round((y0 + oy) * sy), round((y1 + oy) * sy)
    zx, zy, zl, zh = zone
    fx, fy, fw, fh = X0 - zx, Y0 - zy, X1 - X0, Y1 - Y0
    print(f"Toile pleine résolution ({pleine[0]} x {pleine[1]}, échelle {sx:.4f}) : "
          f"x={X0} y={Y0} largeur={fw} hauteur={fh}")
    print(f"TIFF multiblend (zone utile {zl} x {zh} en {zx},{zy}) : x={fx} y={fy} largeur={fw} hauteur={fh}")

    debords = {"à gauche": -fx, "en haut": -fy, "à droite": fx + fw - zl, "en bas": fy + fh - zh}
    debords = {cote: px for cote, px in debords.items() if px > 0}
    if debords:
        sys.exit("\nATTENTION : le cadre sort de la zone utile de la pleine résolution (il y aurait du vide) : "
                 + ", ".join(f"{cote} de {px} px pleine résolution ({px / sx:.1f} px HDR)"
                             for cote, px in debords.items())
                 + ".\nResserrer le recadrage dans Lightroom (le noir du bord se voit sur le HDR). "
                   "Aucune commande n'est proposée pour un cadre qui ne tient pas.")
    print("\nOK : le cadre tient dans la zone utile de la pleine résolution (contrôle du rectangle englobant "
          "seulement : l'escalier du bord supérieur se juge à l'œil dans Lightroom).")

    ecart_x = (X0 / sx - (x0 + ox)) / w
    ecart_y = (Y0 / sy - (y0 + oy)) / h
    largeur_box = (fw / sx) / w
    print("\n--- Commandes PowerShell (variables du guide : $V = vips.exe, $P, $H ; HDR exporté NON recadré) ---")
    print('$C = "$P\\7_tuiles\\cadrage"; New-Item -ItemType Directory -Force $C | Out-Null')
    print(f'& $V extract_area "$H\\TIFF\\pano_20000_E0-HDR_non_recadre.tif" "$C\\hdr_cadre.tif" {x0} {y0} {w} {h}')
    print(f'& $V extract_area "$P\\6_pleine_res\\complet\\rendu\\complet_multiblend.tif" '
          f'"$C\\complet_cadre.tif[bigtiff,tile]" {fx} {fy} {fw} {fh}')
    print("\nTuiler ensuite hdr_cadre.tif et complet_cadre.tif (tuiler.ps1, mêmes options qu'avant : "
          "-ProfilDepuis une image de l'export H sur la pleine résolution).")
    print("Les deux sources étant au même cadre : &box=" + ",".join(f"{v:.6f}".replace("-0.000000", "0.000000")
                                                                    for v in (ecart_x, ecart_y, largeur_box)))


if __name__ == "__main__":
    main()
