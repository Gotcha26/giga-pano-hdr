"""Coche à la place de l'utilisateur les variables de l'onglet Optimisation de Hugin.

CONTEXTE
    Étapes 3E et 3G (optimisation, puis réoptimisations). Dans Hugin, choisir à la main les variables à optimiser pour 222 images est
    long et sujet à erreur. Ce script écrit directement la liste dans le projet : il n'y a plus qu'à ouvrir le
    projet dans Hugin et lancer l'optimisation.

MODE OPÉRATOIRE
    Écrit dans le projet la liste des variables à optimiser (les variables déjà présentes sont remplacées) :
    - lacet (y), tangage (p) et roulis (r) de toutes les images sauf l'ancre et les images exclues ;
    - avec --objectif : en plus le champ de vue (v) et la distorsion (a, b, c) de l'objectif.
    Ouvrir ensuite le projet dans Hugin et cliquer sur « Optimiser maintenant ! » (onglet Optimisation).

ENTRÉES
    entree.pto, sortie.pto   projet source, projet à écrire
    --objectif          optimise aussi v, a, b, c
    --ancre N           image de référence, jamais déplacée (défaut 0)
    --exclure LISTE     images à ne pas optimiser, listes et intervalles (ex. 7-17,47-51)
    --sans-cp-exclues   retire aussi les points de contrôle des images exclues (hors ancre) : évite qu'ils
                        faussent l'objectif

SORTIES
    sortie.pto + message : nombre d'images, nombre de variables, images exclues ; avec --sans-cp-exclues, le
    nombre de points retirés.

EXEMPLE
    python preparer_optimisation.py f2.5.pto f2.5_pos.pto
    python preparer_optimisation.py opt1_ciel.pto opt1_obj.pto --objectif --exclure 7-17,47-51 --sans-cp-exclues

Usage : python preparer_optimisation.py entree.pto sortie.pto [--objectif] [--ancre N] [--exclure 7-17,47-51] [--sans-cp-exclues]
"""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("entree")
ap.add_argument("sortie")
ap.add_argument("--objectif", action="store_true", help="optimise aussi v, a, b, c")
ap.add_argument("--ancre", type=int, default=0, help="image de référence, jamais déplacée (défaut : 0)")
ap.add_argument("--exclure", default="", help="images à ne pas optimiser, par exemple 7-17,47-51")
ap.add_argument("--sans-cp-exclues", action="store_true",
                help="retire aussi les points de contrôle des images exclues (hors ancre) : évite qu'ils faussent l'objectif")
args = ap.parse_args()

exclues = {args.ancre}
for morceau in filter(None, args.exclure.split(",")):
    a, _, b = morceau.partition("-")
    exclues.update(range(int(a), int(b or a) + 1))

lignes = open(args.entree, encoding="utf-8").read().splitlines()
n_images = sum(1 for l in lignes if l.startswith("i "))

variables = []
if args.objectif:
    variables += ["v v0", "v a0", "v b0", "v c0"]
for k in range(n_images):
    if k not in exclues:
        variables += [f"v r{k}", f"v p{k}", f"v y{k}"]

sortie, vu_variables, cp_retires = [], False, 0
sans_cp = exclues - {args.ancre} if args.sans_cp_exclues else set()
for l in lignes:
    if sans_cp and l.startswith("c n"):
        champs = l.split()
        if int(champs[1][1:]) in sans_cp or int(champs[2][1:]) in sans_cp:
            cp_retires += 1
            continue
    if l.startswith("v ") or l == "v":
        if not vu_variables:
            sortie += variables + ["v"]
            vu_variables = True
        continue
    sortie.append(l)
if not vu_variables:
    sortie += ["", "# specify variables that should be optimized"] + variables + ["v"]

open(args.sortie, "w", encoding="utf-8", newline="\n").write("\n".join(sortie) + "\n")
print(f"{n_images} images ; variables à optimiser : {len(variables)} "
      f"({'lacet/tangage/roulis + objectif' if args.objectif else 'lacet/tangage/roulis'}), "
      f"images exclues : {sorted(exclues)} -> {args.sortie}")
if sans_cp:
    print(f"{cp_retires} points de contrôle des images exclues retirés")
