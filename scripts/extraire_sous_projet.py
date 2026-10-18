"""Extrait d'un projet Hugin (.pto) un sous-projet contenant seulement certaines images.

CONTEXTE
    Sert à tester une zone d'un très grand panorama (ex. une fenêtre de 12 images à pleine résolution) sans
    lancer le rendu des 222 images. En phase 6, avec --images 0-221, sert aussi à repartir du projet optimisé
    sans variables à optimiser.

MODE OPÉRATOIRE
    - garde les images demandées et renumérote les points de contrôle (seuls ceux dont les deux images sont
      conservées subsistent) ;
    - reporte les paramètres d'objectif liés (`v=0`, `a=0`...) : si l'image qui les porte est retirée, la première
      image conservée qui en dépend les reçoit en valeur explicite, les autres s'y rattachent ;
    - recalcule les chemins d'images relativement au projet de sortie ;
    - ne laisse aucune variable à optimiser (le sous-projet sert au rendu, pas à l'optimisation).

ENTRÉES
    entree.pto    projet d'origine
    sortie.pto    projet à écrire (le dossier est créé si besoin)
    --images      numéros des images dans le projet d'entrée (0 = première ligne `i`), listes et intervalles
                  séparés par des virgules (ex. 133-138,170-175) ; ce sont les numéros affichés par
                  voir_positions.py et detecter_trous.py.

SORTIES
    sortie.pto + message « N images conservées sur M, K points de contrôle ». Arrêt si un numéro est hors limites.

EXEMPLE
    python extraire_sous_projet.py pano_grille_opt4.pto fenetre.pto --images 133-138,170-175

Usage : python extraire_sous_projet.py entree.pto sortie.pto --images 133-138,170-175
"""
import os
import re
import sys
from pathlib import Path


def intervalles(texte):
    res = []
    for morceau in texte.split(","):
        morceau = morceau.strip()
        if not morceau:
            continue
        if "-" in morceau:
            a, b = morceau.split("-")
            res += list(range(int(a), int(b) + 1))
        else:
            res.append(int(morceau))
    return sorted(set(res))


def decouper(ligne):
    """Ligne `i` -> (liste de (nom, valeur) dans l'ordre, chemin d'image)."""
    m = re.search(r'\bn"([^"]*)"\s*$', ligne)
    if not m:
        sys.exit(f"ligne d'image sans nom de fichier : {ligne[:80]}")
    jetons = []
    for jeton in ligne[2:m.start()].split():
        mm = re.fullmatch(r"([A-Za-z]+)(.*)", jeton)
        if not mm:
            sys.exit(f"jeton illisible : {jeton}")
        jetons.append((mm.group(1), mm.group(2)))
    return jetons, m.group(1)


def main():
    args = sys.argv[1:]
    if len(args) != 4 or args[2] != "--images":
        sys.exit(__doc__)
    entree, sortie = Path(args[0]).resolve(), Path(args[1]).resolve()
    voulues = intervalles(args[3])

    lignes = entree.read_text(encoding="utf-8").splitlines()
    idx_i = [k for k, l in enumerate(lignes) if l.startswith("i ")]
    n_img = len(idx_i)
    if not voulues or voulues[0] < 0 or voulues[-1] >= n_img:
        sys.exit(f"numéros d'images hors limites (le projet en compte {n_img})")

    images = [decouper(lignes[k]) for k in idx_i]
    ordre = [[nom for nom, _ in jetons] for jetons, _ in images]
    valeur = [dict(jetons) for jetons, _ in images]

    def racine(i, nom):
        """Image qui porte réellement la valeur de `nom` pour l'image i (suit les liens `=k`)."""
        vu = set()
        while valeur[i][nom].startswith("="):
            if i in vu:
                sys.exit(f"boucle de liens sur {nom} à l'image {i}")
            vu.add(i)
            i = int(valeur[i][nom][1:])
        return i

    nouveau = {ancien: k for k, ancien in enumerate(voulues)}
    sortie_i = []
    proprietaire = {}                          # (nom, racine d'origine) -> nouvelle image porteuse
    for ancien in voulues:
        k = nouveau[ancien]
        jetons = []
        for nom in ordre[ancien]:
            v = valeur[ancien][nom]
            if v.startswith("="):
                r = racine(ancien, nom)
                if r in nouveau and nouveau[r] != k:
                    v = f"={nouveau[r]}"            # le porteur d'origine est conservé
                elif (nom, r) in proprietaire and proprietaire[(nom, r)] != k:
                    v = f"={proprietaire[(nom, r)]}"  # un autre conservé le porte désormais
                else:
                    v = valeur[r][nom]              # valeur explicite, copiée du porteur d'origine
                    proprietaire[(nom, r)] = k
            else:
                proprietaire.setdefault((nom, ancien), k)
            jetons.append(f"{nom}{v}")
        chemin = lignes[idx_i[ancien]]
        nom_fichier = images[ancien][1]
        img = (entree.parent / nom_fichier).resolve()
        try:
            rel = os.path.relpath(img, sortie.parent)
        except ValueError:
            rel = str(img)
        sortie_i.append("i " + " ".join(jetons) + f' n"{rel}"')

    # points de contrôle
    cps = []
    for l in lignes:
        if l.startswith("c "):
            m = re.match(r"c n(\d+) N(\d+) (.*)", l)
            a, b = int(m.group(1)), int(m.group(2))
            if a in nouveau and b in nouveau:
                cps.append(f"c n{nouveau[a]} N{nouveau[b]} {m.group(3)}")

    # lignes du projet hors images, points de contrôle et variables
    # Un projet écrit par un script (propager_geometrie.py, generer_pto_hdr.py) n'a pas les commentaires
    # « # image lines » ni « # control points » : images et points sont alors écrits là où se trouvait
    # la première ligne `i` ou `c`.
    marqueur_images = "# image lines" in lignes
    marqueur_points = "# control points" in lignes
    images_ecrites = points_ecrits = False

    def ecrire_images():
        for ligne in sortie_i:
            sortie_l.append("#-hugin  cropFactor=1")
            sortie_l.append(ligne)

    sortie_l = []
    for k, l in enumerate(lignes):
        if l.startswith("i ") and not marqueur_images and not images_ecrites:
            ecrire_images()
            images_ecrites = True
        if l.startswith("c ") and not marqueur_points and not points_ecrits:
            sortie_l += cps
            points_ecrits = True
        if l.startswith(("i ", "c ", "v ")) or l == "v" or l.startswith("#-hugin"):
            continue
        if l.startswith("#hugin_optimizeReferenceImage"):
            l = "#hugin_optimizeReferenceImage 0"
        if l == "# image lines":
            sortie_l.append(l)
            ecrire_images()
            continue
        if l == "# specify variables that should be optimized":
            sortie_l += [l, "v", ""]
            continue
        if l == "# control points":
            sortie_l.append(l)
            sortie_l += cps
            continue
        sortie_l.append(l)

    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text("\n".join(sortie_l) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(voulues)} images conservées sur {n_img}, {len(cps)} points de contrôle -> {sortie}")


main()
