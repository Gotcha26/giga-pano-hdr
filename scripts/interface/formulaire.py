"""Logique des formulaires de l'interface web : de la déclaration des arguments d'une tâche à la ligne de commande.

Partie pure, sans NiceGUI : `champs()` décrit chaque argument comme un `Champ` que la page rend ; `commande()`
construit la ligne de commande à partir des valeurs saisies, exactement comme le fait le lanceur console.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pilotage import arguments as args_mod
from pilotage import config, declarations_ps, lancer

AUTRE = "Autre…"        # dernier choix d'un champ « pto » : saisir ou parcourir un autre chemin

GENRES = {"texte": "texte", "liste": "texte", "plage": "texte","nombre": "nombre", "entier": "nombre", "drapeau": "interrupteur",
          "chemin": "fichier", "dossier": "dossier", "pto": "pto"}
GENRES_CHEMIN = ("fichier", "dossier", "pto")


@dataclass
class Champ:
    arg: args_mod.Arg
    valeur: object                      # str, ou bool pour un interrupteur
    genre: str                          # "texte", "nombre", "interrupteur", "fichier", "dossier", "pto"
    choix: list = field(default_factory=list)   # pto : valeur préremplie, .pto de la phase triés, puis AUTRE
    depart: str = ""                    # dossier où s'ouvre Parcourir
    obligatoire: bool = False
    aide: str = ""
    panorama: Optional[config.Panorama] = field(default=None, repr=False)

    @property
    def hors_panorama(self):
        """Chemin renseigné, absolu, qui n'est ni sous $T, ni sous $P, ni sous $H."""
        if self.genre not in GENRES_CHEMIN or not isinstance(self.valeur, str) or not self.valeur:
            return False
        if not os.path.isabs(self.valeur):
            return False
        complet = config._normaliser(self.valeur)
        for racine in (getattr(self.panorama, cle, "") for cle in ("T", "P", "H")):
            if not racine:
                continue
            racine = config._normaliser(racine).rstrip(os.sep)
            if complet == racine or complet.startswith(racine + os.sep):
                return False
        return True


def arguments_de(tache, ctx):
    """(arguments, ecrit, doc) d'une tâche : sa déclaration propre si elle en a une, sinon celle de son script
    (en-tête Python lu par analyse syntaxique, ou déclaration PowerShell du lanceur)."""
    if not tache.script:
        raise ValueError("tâche sans script : " + tache.identifiant)
    if tache.script.endswith(".ps1"):
        arguments, ecrit = declarations_ps.PS[tache.script]
        doc = lancer._titre_ps(ctx.scripts / tache.script) or tache.script
    else:
        arguments, ecrit, doc = args_mod.lire_declaration(ctx.scripts / tache.script)
    if tache.arguments is not None:
        arguments = tache.arguments
        ecrit = tache.ecrit or tache.effet or ecrit
    return list(arguments), ecrit, doc


def _choix_pto(arg, valeur, panorama):
    dossier = config.dossier_phase(panorama, arg.phase) if arg.phase and panorama else None
    fichiers = sorted(str(f) for f in dossier.glob("*.pto")) if dossier and dossier.is_dir() else []
    def forme(chemin):
        return os.path.normcase(os.path.normpath(chemin))
    deja = {forme(f) for f in fichiers}
    choix = [valeur] if valeur and forme(valeur) not in deja else []
    return choix + fichiers + [AUTRE]


def _depart(arg, panorama):
    if panorama is None:
        return ""
    dossier = config.dossier_phase(panorama, arg.phase) if arg.phase else None
    if dossier and dossier.is_dir():
        return str(dossier)
    return panorama.P or ""


def champs(tache, arguments, panorama, ctx):
    """Un Champ par argument, préremplis : réglage mémorisé, sinon configuration du panorama, sinon défaut."""
    arguments = lancer._prerempli_outils(ctx, arguments)
    memorises = panorama.reglages.get(tache.identifiant) if panorama else None
    valeurs = args_mod.valeurs_initiales(arguments, panorama, memorises=memorises)
    resultat = []
    for a in arguments:
        if a.type not in GENRES:
            raise ValueError(f"type d'argument sans genre de champ : {a.type} ({a.nom})")
        genre = GENRES[a.type]
        valeur = valeurs[a.nom]
        resultat.append(Champ(arg=a, valeur=valeur, genre=genre,
                              choix=_choix_pto(a, valeur, panorama) if genre == "pto" else [],
                              depart=_depart(a, panorama) if genre in GENRES_CHEMIN else "",
                              obligatoire=bool(a.obligatoire), aide=a.aide, panorama=panorama))
    return resultat


def commande(tache, ctx, valeurs):
    """Ligne de commande de la tâche pour les `valeurs` saisies (nom d'argument -> valeur)."""
    arguments, _, _ = arguments_de(tache, ctx)
    arguments = lancer._prerempli_outils(ctx, arguments)
    if tache.script.endswith(".ps1"):
        return lancer.commande_powershell(ctx, tache.script, lancer.construire_ps(arguments, valeurs))
    return lancer.commande_python(ctx, tache.script, args_mod.construire_argv(arguments, valeurs))
