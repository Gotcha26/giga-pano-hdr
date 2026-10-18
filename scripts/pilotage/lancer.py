"""Exécution des scripts depuis le lanceur : menu de pilotage, puis sous-processus dans la même console.

Python : la déclaration ARGUMENTS du script est lue sans l'exécuter. PowerShell : la déclaration est portée par
le lanceur (declarations_ps.py) ; la ligne de commande est construite en paramètres nommés. Ctrl+C interrompt
l'enfant et revient au lanceur.
"""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Optional

from . import arguments as args_mod
from .couleurs import Couleurs

RE_CONSTANTE = re.compile(r"^(COLS|ROWS|FOCALE|LARGEUR_MM|PAS_H|PAS_V|EXPOS|FOV_H|FOV_V)\s*=\s*([\d.]+)", re.MULTILINE)
RE_CONSTANTES_DOUBLE = re.compile(r"^(COLS|ROWS), (COLS|ROWS)\s*=\s*([\d.]+),\s*([\d.]+)", re.MULTILINE)

MESSAGES_INTERRUPTION = {
    "nona_images.ps1": "La même commande reprend là où elle s'est arrêtée (les images déjà rendues sont sautées).",
}


@dataclass
class Contexte:
    poste: Any
    panorama: Any
    etats: list
    c: Couleurs
    lire: Callable = input
    ecrire: Callable = print
    scripts: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    executer: Callable = subprocess.run


def etat(ctx, cle):
    return next((e for e in ctx.etats if e.outil.cle == cle), None)


def present(ctx, cle):
    e = etat(ctx, cle)
    return bool(e and e.present)


def constantes_du_fichier(chemin):
    texte = Path(chemin).read_text(encoding="utf-8")
    constantes = {k: float(v) if "." in v else int(v) for k, v in RE_CONSTANTE.findall(texte)}
    for a, b, va, vb in RE_CONSTANTES_DOUBLE.findall(texte):
        constantes[a], constantes[b] = int(va), int(vb)
    return constantes


def _prerempli_outils(ctx, arguments):
    """Les Arg dont config vaut « outil:<cle> » prennent pour défaut le chemin configuré sur le poste."""
    resultat = []
    for a in arguments:
        if a.config and a.config.startswith("outil:"):
            cle = a.config.split(":", 1)[1]
            chemin = ctx.poste.outils.get(cle)
            if not chemin:
                e = etat(ctx, cle)
                chemin = e.chemin if e and e.present else None
            if chemin and cle == "hugin" and os.path.isfile(chemin):
                chemin = os.path.dirname(chemin)          # les .ps1 attendent le dossier bin de Hugin
            resultat.append(replace(a, config=None, defaut=chemin if chemin else a.defaut))
        else:
            resultat.append(a)
    return resultat


def _menu(ctx, doc, arguments, ecrit, constantes=None):
    return args_mod.menu(doc, _prerempli_outils(ctx, arguments), ecrit, constantes=constantes,
                         panorama=ctx.panorama, c=ctx.c, lire=ctx.lire, ecrire=ctx.ecrire)


def _executer(ctx, commande, script=""):
    try:
        r = ctx.executer(commande, cwd=str(ctx.scripts))
        return getattr(r, "returncode", 0)
    except KeyboardInterrupt:
        ctx.ecrire("")
        ctx.ecrire(ctx.c.attention("Interrompu. Retour au lanceur."))
        if script in MESSAGES_INTERRUPTION:
            ctx.ecrire(ctx.c.info(MESSAGES_INTERRUPTION[script]))
        return 130


def python(ctx, script, arguments=None, ecrit=None):
    """Menu de pilotage puis exécution d'un script Python ; None si annulé, sinon le code de sortie."""
    chemin = ctx.scripts / script
    if arguments is None:
        arguments, ecrit, doc = args_mod.lire_declaration(chemin)
    else:
        doc = args_mod.lire_declaration(chemin)[2]
    argv = _menu(ctx, doc, arguments, ecrit, constantes=constantes_du_fichier(chemin))
    if argv is None:
        return None
    return _executer(ctx, [sys.executable, str(chemin), *argv], script)


def construire_ps(arguments, valeurs):
    """Paramètres nommés PowerShell : -Switch pour un drapeau vrai, -Nom valeur pour une valeur renseignée."""
    resultat = []
    for a in arguments:
        if not a.nom.startswith("-"):
            raise ValueError(f"paramètre PowerShell sans tiret : {a.nom}")
        v = valeurs.get(a.nom)
        if a.type == "drapeau":
            if v is True:
                resultat.append(a.nom)
        elif v not in (None, "", False):
            resultat += [a.nom, str(v)]
    return resultat


def _titre_ps(chemin):
    """Première ligne de commentaire d'un script PowerShell (son titre)."""
    try:
        for ligne in Path(chemin).read_text(encoding="utf-8").splitlines():
            if ligne.startswith("#"):
                return ligne.lstrip("# ").strip()
            if ligne.strip():
                break
    except OSError:
        pass
    return ""


def powershell_disponible(ctx):
    return present(ctx, "pwsh") or shutil.which("powershell.exe") is not None


def _executable_powershell(ctx):
    e = etat(ctx, "pwsh")
    return e.chemin if e and e.present else "powershell.exe"


def powershell(ctx, script, arguments, ecrit, doc=None):
    """Menu de pilotage puis exécution d'un script PowerShell en paramètres nommés."""
    arguments = _prerempli_outils(ctx, arguments)
    if doc is None:
        doc = _titre_ps(ctx.scripts / script) or script
    valeurs_menu = args_mod.menu(doc, arguments, ecrit, panorama=ctx.panorama, c=ctx.c,
                                 lire=ctx.lire, ecrire=ctx.ecrire, construire=lambda a, v: construire_ps(a, v))
    if valeurs_menu is None:
        return None
    commande = [_executable_powershell(ctx), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(ctx.scripts / script), *valeurs_menu]
    return _executer(ctx, commande, script)


def outil(ctx, cle, args):
    """Exécute un programme livré avec un outil détecté (ex. cpclean.exe du dossier de Hugin)."""
    e = etat(ctx, cle)
    if not (e and e.present):
        ctx.ecrire(ctx.c.erreur(f"{cle} introuvable : voir Configuration."))
        return None
    dossier = os.path.dirname(e.chemin)
    return _executer(ctx, [os.path.join(dossier, args[0]), *args[1:]])
