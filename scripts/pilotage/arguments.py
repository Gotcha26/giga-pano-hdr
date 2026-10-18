"""Menu de pilotage des arguments d'un script : déclaration (Arg), menu, construction de la ligne de commande.

Un script déclare ses arguments une fois (ARGUMENTS = [Arg(...)]) et appelle piloter() avant sa première
lecture de sys.argv. Lancé sans argument dans un terminal, il affiche la liste numérotée de ses arguments
(préremplie d'après le panorama courant), laisse l'utilisateur les régler, puis complète sys.argv comme si
la ligne de commande avait été tapée. Avec des arguments, ou sans terminal, rien ne change.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from . import config
from .couleurs import Couleurs, effacer_ecran, preparer_console
from .menu import confirmer, demander, pause

TYPES = ("texte", "chemin", "dossier", "pto", "nombre", "entier", "drapeau", "plage", "liste")

CONSTANTES = ("COLS", "ROWS", "FOCALE", "LARGEUR_MM", "PAS_H", "PAS_V", "EXPOS", "FOV_H", "FOV_V")
CORRESPONDANCE = {"COLS": "colonnes", "ROWS": "lignes", "PAS_H": "pas_h", "PAS_V": "pas_v",
                  "FOCALE": "focale", "LARGEUR_MM": "largeur_mm", "EXPOS": "expos"}

A_SAISIR = "à saisir"


@dataclass
class Arg:
    nom: str
    aide: str
    type: str = "texte"
    defaut: Any = None
    config: Optional[str] = None      # clé pour config.valeur (préremplissage)
    phase: Optional[str] = None       # dossier de phase où lister les .pto existants
    obligatoire: Optional[bool] = None
    nargs: int = 1

    def __post_init__(self):
        if self.type not in TYPES:
            raise ValueError(f"type d'argument inconnu : {self.type}")
        if self.obligatoire is None:
            self.obligatoire = not self.option and self.defaut is None and self.type != "drapeau"

    @property
    def option(self):
        return self.nom.startswith("-")


def construire_argv(arguments, valeurs):
    """Positionnels dans l'ordre (arrêt au premier vide), puis options (drapeaux vrais, options renseignées)."""
    argv = []
    for a in arguments:
        if a.option:
            continue
        v = valeurs.get(a.nom)
        if v in (None, "", False):
            break
        argv += str(v).split() if a.type == "liste" else [str(v)]
    for a in arguments:
        if not a.option:
            continue
        v = valeurs.get(a.nom)
        if a.type == "drapeau":
            if v is True:
                argv.append(a.nom)
        elif v not in (None, "", False):
            argv.append(a.nom)
            argv += str(v).split() if a.nargs > 1 or a.type == "liste" else [str(v)]
    return argv


def constantes_du_script(globals_):
    return {k: globals_[k] for k in CONSTANTES if k in globals_}


def ecarts(constantes, panorama):
    """(nom, valeur du script, valeur du panorama) pour chaque constante qui contredit le panorama courant."""
    resultat = []
    if panorama is None:
        return resultat
    for nom, valeur_script in constantes.items():
        cle = CORRESPONDANCE.get(nom)
        if not cle:
            continue
        valeur_pano = getattr(panorama, cle, None)
        if valeur_pano is None:
            continue
        try:
            if float(valeur_script) != float(valeur_pano):
                resultat.append((nom, valeur_script, valeur_pano))
        except (TypeError, ValueError):
            continue
    return resultat


def _valeurs_initiales(arguments, panorama):
    valeurs = {}
    for a in arguments:
        if a.type == "drapeau":
            valeurs[a.nom] = bool(a.defaut)
            continue
        v = config.valeur(panorama, a.config) if a.config else None
        if v is None and a.defaut is not None:
            v = str(a.defaut)
        valeurs[a.nom] = v or ""
    return valeurs


def _choisir_pto(a, panorama, c, lire, ecrire):
    """Liste les .pto du dossier de phase ; retourne le chemin choisi, une saisie manuelle, ou None (annulé)."""
    dossier = config.dossier_phase(panorama, a.phase) if a.phase else None
    fichiers = sorted(dossier.glob("*.pto")) if dossier and dossier.is_dir() else []
    if not fichiers:
        return demander(a.aide, c, lire=lire)
    ecrire("")
    ecrire(c.titre(f"Projets dans {dossier}"))
    for i, f in enumerate(fichiers, 1):
        ecrire(f"  {c.JAUNE}{str(i).rjust(len(str(len(fichiers))))}{c.RESET}. {f.name}")
    ecrire(f"  {c.JAUNE}M{c.RESET}. Saisir un autre chemin")
    choix = lire(c.prompt("  Votre choix (numéro, M, x pour annuler) : ")).strip()
    if choix.lower() == "x":
        return None
    if choix.lower() == "m":
        return demander(a.aide, c, lire=lire)
    if choix.isdigit() and 1 <= int(choix) <= len(fichiers):
        return str(fichiers[int(choix) - 1])
    ecrire(c.erreur(f'Choix invalide : "{choix}"'))
    pause(c, lire)
    return None


def _afficher(doc, arguments, valeurs, ecrit, constantes, panorama, c, ecrire):
    titre = next((l.strip() for l in (doc or "").splitlines() if l.strip()), "Pilotage du script")
    ecrire(c.boite("PILOTAGE"))
    ecrire(f"  {c.TITRE}{titre}{c.RESET}")
    if constantes:
        rappel = ", ".join(f"{k} = {v}" for k, v in constantes.items())
        ecrire(f"  {c.DIM}Constantes du script : {rappel}{c.RESET}")
        for nom, vs, vp in ecarts(constantes, panorama):
            ecrire("  " + c.attention(f"{nom} = {vs} dans le script, {vp} dans le panorama courant"))
    ecrire("")
    largeur_nom = max(len(a.nom) for a in arguments)
    largeur_num = len(str(len(arguments)))
    for i, a in enumerate(arguments, 1):
        v = valeurs[a.nom]
        if a.type == "drapeau":
            affiche = f"{c.OK}oui{c.RESET}" if v else f"{c.DIM}non{c.RESET}"
        elif v == "":
            affiche = f"{c.ATTENTION}{A_SAISIR}{c.RESET}" if a.obligatoire else f"{c.DIM}(vide){c.RESET}"
        else:
            affiche = c.valeur(v)
        ecrire(f"  {c.JAUNE}{str(i).rjust(largeur_num)}{c.RESET}. {a.nom.ljust(largeur_nom)} : {affiche}  {c.DIM}— {a.aide}{c.RESET}")
    ecrire("")
    ecrire(f"  {c.DIM}{f'[écrit — {ecrit}]' if ecrit else '[lecture seule]'}{c.RESET}")
    ecrire(f"  {c.JAUNE}L{c.RESET}. Lancer    {c.JAUNE}0{c.RESET}. {c.DIM}Annuler{c.RESET}")


def menu(doc, arguments, ecrit, constantes=None, panorama=None, c=None, lire=input, ecrire=print, effacer=None,
         construire=construire_argv):
    """Affiche le menu de pilotage ; retourne la liste d'arguments (construite par `construire`), ou None si annulé."""
    c = c or Couleurs()
    effacer = effacer if effacer is not None else effacer_ecran
    valeurs = _valeurs_initiales(arguments, panorama)
    try:
        while True:
            effacer()
            _afficher(doc, arguments, valeurs, ecrit, constantes, panorama, c, ecrire)
            choix = lire(c.prompt(f"\n  Votre choix (1-{len(arguments)}, L, 0) : ")).strip()
            if choix == "0":
                return None
            if choix.lower() == "l":
                manquants = [a.nom for a in arguments if a.obligatoire and valeurs[a.nom] in ("", None)]
                if manquants:
                    ecrire(c.erreur(f"Argument obligatoire non renseigné : {', '.join(manquants)}"))
                    pause(c, lire)
                    continue
                if constantes and ecarts(constantes, panorama):
                    if not confirmer("Les constantes du script contredisent le panorama courant. Lancer malgré l'écart ?",
                                     c, defaut_oui=False, lire=lire):
                        continue
                return construire(arguments, valeurs)
            if choix.isdigit() and 1 <= int(choix) <= len(arguments):
                a = arguments[int(choix) - 1]
                if a.type == "drapeau":
                    valeurs[a.nom] = not valeurs[a.nom]
                elif a.type == "pto" and valeurs[a.nom] == "":
                    nouveau = _choisir_pto(a, panorama, c, lire, ecrire)
                    if nouveau is not None:
                        valeurs[a.nom] = nouveau
                else:
                    nouveau = demander(a.aide, c, defaut=valeurs[a.nom] or None, lire=lire)
                    if nouveau is not None:
                        valeurs[a.nom] = nouveau
                continue
            ecrire(c.erreur(f'Choix invalide : "{choix}"'))
            pause(c, lire)
    except StopIteration:   # fin des saisies injectées (tests)
        return None


def lire_declaration(chemin):
    """(ARGUMENTS, ecrit, docstring) d'un script, lus par analyse syntaxique : le script n'est pas exécuté
    (un import déclencherait sa lecture de sys.argv)."""
    import ast
    arbre = ast.parse(Path(chemin).read_text(encoding="utf-8"))
    arguments, ecrit = [], None
    for noeud in arbre.body:
        if isinstance(noeud, ast.Assign) and any(isinstance(c, ast.Name) and c.id == "ARGUMENTS" for c in noeud.targets):
            for appel in noeud.value.elts:
                positionnels = [ast.literal_eval(a) for a in appel.args]
                nommes = {k.arg: ast.literal_eval(k.value) for k in appel.keywords}
                arguments.append(Arg(*positionnels, **nommes))
        elif isinstance(noeud, ast.Expr) and isinstance(noeud.value, ast.Call) \
                and getattr(noeud.value.func, "id", "") == "piloter":
            for k in noeud.value.keywords:
                if k.arg == "ecrit":
                    ecrit = ast.literal_eval(k.value)
    return arguments, ecrit, ast.get_docstring(arbre) or ""


def piloter(doc, arguments, ecrit=None, globals_=None):
    """À appeler avant la première lecture de sys.argv : sans argument et dans un terminal, ouvre le menu."""
    if len(sys.argv) != 1 or not getattr(sys.stdin, "isatty", lambda: False)():
        return
    preparer_console()
    panorama = config.panorama_courant(config.charger_poste())
    resultat = menu(doc, arguments, ecrit, constantes=constantes_du_script(globals_ or {}), panorama=panorama)
    if resultat is None:
        sys.exit(0)
    sys.argv.extend(resultat)
