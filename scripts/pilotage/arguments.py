"""Menu de pilotage des arguments d'un script : déclaration (Arg), menu, construction de la ligne de commande.

Un script déclare ses arguments une fois (ARGUMENTS = [Arg(...)]) et appelle piloter() avant sa première
lecture de sys.argv. Lancé sans argument dans un terminal, il affiche la liste numérotée de ses arguments
(préremplie d'après le panorama courant), laisse l'utilisateur les régler, puis complète sys.argv comme si
la ligne de commande avait été tapée. Avec des arguments, ou sans terminal, rien ne change.
"""

import os
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
SANS_MENU = "GIGA_PANO_SANS_MENU"   # posée par le lanceur pour ses enfants : jamais de second menu


def terminal_interactif(stdin=None, stdout=None):
    """Vrai seulement si l'entrée ET la sortie standard sont une vraie console.

    Sous Windows, NUL est un périphérique caractère : isatty() y répond vrai pour une entrée redirigée depuis
    NUL ou subprocess.DEVNULL. GetConsoleMode, lui, n'accepte qu'une console."""
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout
    try:
        if not stdout.isatty() or not stdin.isatty():
            return False
    except (AttributeError, ValueError):
        return False
    if os.name != "nt":
        return True
    try:
        import ctypes
        import msvcrt
        handle = msvcrt.get_osfhandle(stdin.fileno())
        mode = ctypes.c_uint()
        return bool(ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)))
    except Exception:
        return False


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


def _positionnels_apres_un_vide(arguments, valeurs):
    """(vide, renseigné) pour chaque positionnel renseigné qui suit un positionnel vide : la ligne de
    commande ne saurait pas les distinguer, construire_argv s'arrêterait au vide et perdrait le suivant."""
    positionnels = [a for a in arguments if not a.option]
    premier_vide = next((a for a in positionnels if valeurs.get(a.nom) in ("", None)), None)
    if premier_vide is None:
        return []
    apres = positionnels[positionnels.index(premier_vide) + 1:]
    return [(premier_vide.nom, a.nom) for a in apres if valeurs.get(a.nom) not in ("", None)]


TYPES_CHEMIN = ("chemin", "dossier", "pto")


def _chemins_invalides(arguments, valeurs, absolus):
    """(nom, raison) pour chaque chemin renseigné qui contient « … » (abréviation recopiée telle quelle) ou, si
    `absolus`, qui est relatif : le lanceur exécute les scripts depuis scripts\\, où un chemin relatif se résout."""
    resultat = []
    for a in arguments:
        v = str(valeurs.get(a.nom) or "")
        if a.type not in TYPES_CHEMIN or not v:
            continue
        if "…" in v or "..." in v.replace("\\", "/").split("/"):
            resultat.append((a.nom, "contient « … »"))
        elif absolus and not os.path.isabs(v):
            resultat.append((a.nom, "chemin relatif"))
    return resultat


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


def valeurs_initiales(arguments, panorama, memorises=None):
    """Valeur de départ de chaque argument : réglage mémorisé, sinon configuration du panorama, sinon défaut."""
    memorises = memorises or {}
    valeurs = {}
    for a in arguments:
        if a.type == "drapeau":
            valeurs[a.nom] = bool(memorises[a.nom]) if a.nom in memorises else bool(a.defaut)
            continue
        v = memorises.get(a.nom)
        if v in (None, ""):
            v = config.valeur(panorama, a.config) if a.config else None
        if v is None and a.defaut is not None:
            v = str(a.defaut)
        valeurs[a.nom] = v or ""
    return valeurs


_valeurs_initiales = valeurs_initiales


def verifier(arguments, valeurs, chemins_absolus=True):
    """Messages d'erreur qui empêchent le lancement (liste vide si tout est en ordre) : obligatoire non renseigné,
    chemin à saisir en entier, positionnel renseigné après un positionnel vide."""
    messages = []
    manquants = [a.nom for a in arguments if a.obligatoire and valeurs[a.nom] in ("", None)]
    if manquants:
        messages.append(f"Argument obligatoire non renseigné : {', '.join(manquants)}")
    invalides = _chemins_invalides(arguments, valeurs, chemins_absolus)
    if invalides:
        messages.append("Chemin à saisir en entier (ex. D:\\Panoramas\\…) : " +
                        " ; ".join(f"{nom} : {raison}" for nom, raison in invalides))
    orphelins = _positionnels_apres_un_vide(arguments, valeurs)
    if orphelins:
        messages.append("Les arguments sont positionnels : " +
                        " ; ".join(f"{apres} exige {vide}" for vide, apres in orphelins))
    return messages


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
         construire=construire_argv, valeurs=None, chemins_absolus=False):
    """Affiche le menu de pilotage ; retourne la liste d'arguments (construite par `construire`), ou None si annulé.

    `valeurs` : dictionnaire tenu par l'appelant, rempli au premier appel puis modifié sur place ; un nouvel appel
    avec le même dictionnaire reprend les réglages (relance après un échec).
    `chemins_absolus` : refuse au lancement un chemin relatif (le lanceur, dont le dossier courant est scripts\\)."""
    c = c or Couleurs()
    effacer = effacer if effacer is not None else effacer_ecran
    if valeurs is None:
        valeurs = {}
    if not valeurs:
        valeurs.update(valeurs_initiales(arguments, panorama))
    try:
        while True:
            effacer()
            _afficher(doc, arguments, valeurs, ecrit, constantes, panorama, c, ecrire)
            choix = lire(c.prompt(f"\n  Votre choix (1-{len(arguments)}, L, 0) : ")).strip()
            if choix == "0":
                return None
            if choix.lower() == "l":
                erreurs = verifier(arguments, valeurs, chemins_absolus)
                if erreurs:
                    for message in erreurs:
                        ecrire(c.erreur(message))
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
    for noeud in ast.walk(arbre):       # piloter() au premier niveau, ou dans main()
        if isinstance(noeud, ast.Call) and getattr(noeud.func, "id", "") == "piloter":
            for k in noeud.keywords:
                if k.arg == "ecrit":
                    ecrit = ast.literal_eval(k.value)
    return arguments, ecrit, ast.get_docstring(arbre) or ""


def piloter(doc, arguments, ecrit=None, globals_=None):
    """À appeler avant la première lecture de sys.argv : sans argument et dans un terminal, ouvre le menu.

    Ne fait rien si : des arguments sont donnés ; le lanceur a posé GIGA_PANO_SANS_MENU ; le script est importé
    par un autre programme (sys.argv[0] ne le désigne pas) ; l'entrée ou la sortie n'est pas une console."""
    if len(sys.argv) != 1 or os.environ.get(SANS_MENU):
        return
    fichier = (globals_ or {}).get("__file__")
    if fichier and sys.argv and sys.argv[0]:
        try:
            if Path(sys.argv[0]).resolve() != Path(fichier).resolve():
                return
        except OSError:
            return
    if not terminal_interactif():
        return
    preparer_console()
    panorama = config.panorama_courant(config.charger_poste())
    resultat = menu(doc, arguments, ecrit, constantes=constantes_du_script(globals_ or {}), panorama=panorama)
    if resultat is None:
        sys.exit(0)
    sys.argv.extend(resultat)
