"""Logique des formulaires de l'interface web : de la déclaration des arguments d'une tâche à la ligne de commande.

Partie pure, sans NiceGUI : `champs()` décrit chaque argument comme un `Champ` que la page rend ; `commande()`
construit la ligne de commande à partir des valeurs saisies, exactement comme le fait le lanceur console.

Partie NiceGUI, en fin de module : `rendre()` pose les éléments d'un formulaire, `valeurs()` les relit,
`parcourir()` ouvre la boîte de dialogue native de Windows. NiceGUI n'y est importé qu'à l'appel, pour que la
partie pure reste utilisable (et testée) sans lui.
"""

import os
import threading
from dataclasses import dataclass, field, replace
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
    valeur: str | bool                  # bool pour un interrupteur
    genre: str                          # "texte", "nombre", "interrupteur", "fichier", "dossier", "pto"
    choix: list[str] = field(default_factory=list)   # pto : valeur préremplie, .pto de la phase triés, puis AUTRE
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
        return not any(config.sous(getattr(self.panorama, cle, ""), self.valeur, inclus=True)
                       for cle in ("T", "P", "H"))


def arguments_de(tache, ctx):
    """(arguments, ecrit, doc) d'une tâche : sa déclaration propre si elle en a une, sinon celle de son script
    (en-tête Python lu par analyse syntaxique, ou déclaration PowerShell du lanceur). Une action du lanceur
    (cpclean) a un formulaire si le catalogue déclare ses arguments et que `lancer` sait construire sa commande."""
    if not tache.script:
        if a_un_formulaire(tache):
            return lus_du_panorama(tache, tache.arguments), tache.ecrit or tache.effet, tache.sous_titre or tache.tete
        raise ValueError("tâche sans script : " + tache.identifiant)
    if tache.script.endswith(".ps1"):
        arguments, ecrit = declarations_ps.PS[tache.script]
        doc = lancer._titre_ps(ctx.scripts / tache.script) or tache.script
    else:
        arguments, ecrit, doc = args_mod.lire_declaration(ctx.scripts / tache.script)
    if tache.arguments is not None:
        arguments = tache.arguments
        ecrit = tache.ecrit or tache.effet or ecrit
    return lus_du_panorama(tache, arguments), ecrit, doc


def a_un_formulaire(tache):
    """Vrai pour une tâche à lancer depuis la page : un script, ou une action dont la commande est connue."""
    if tache.script:
        return True
    return bool(tache.action) and tache.arguments is not None and tache.action in lancer.COMMANDES_ACTIONS


def lus_du_panorama(tache, arguments):
    """Les arguments, ceux que `tache.lit` nomme reliés à leur clé de panorama.json (config) : préremplis
    d'après le panorama, donc jamais mémorisés (args_mod.appliquer_lit, partagée avec le lanceur console)."""
    try:
        return args_mod.appliquer_lit(arguments, tache.lit)
    except ValueError as e:
        raise ValueError(f"{tache.identifiant} : {e}") from None


def arguments_d_outil(arguments):
    """Noms des arguments qui désignent un outil du poste (config « outil:… ») : ni note « hors du panorama »,
    ni candidats au dossier des fichiers produits."""
    return {a.nom for a in arguments if a.config and a.config.startswith("outil:")}


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
    """Un Champ par argument, préremplis : réglage mémorisé, sinon configuration du panorama, sinon défaut.

    Un réglage mémorisé n'est repris que pour un argument sans clé de panorama : celui qu'un `lit` relie au
    panorama après coup suit le panorama, même si une valeur avait été mémorisée avant."""
    arguments = lus_du_panorama(tache, arguments)
    propres = {a.nom for a in arguments if a.config is None}
    arguments = lancer._prerempli_outils(ctx, arguments)
    memorises = panorama.reglages.get(tache.identifiant) if panorama else None
    memorises = {k: v for k, v in (memorises or {}).items() if k in propres}
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
    """Ligne de commande de la tâche pour les `valeurs` saisies (nom d'argument -> valeur) ; LookupError pour
    une action dont l'outil manque."""
    arguments, _, _ = arguments_de(tache, ctx)
    arguments = lancer._prerempli_outils(ctx, arguments)
    if not tache.script:
        return lancer.COMMANDES_ACTIONS[tache.action](ctx, args_mod.construire_argv(arguments, valeurs))
    if tache.script.endswith(".ps1"):
        return lancer.commande_powershell(ctx, tache.script, lancer.construire_ps(arguments, valeurs))
    return lancer.commande_python(ctx, tache.script, args_mod.construire_argv(arguments, valeurs))


# ---------------------------------------------------------------- partie NiceGUI

NOTE_HORS_PANORAMA = "hors du panorama ($T, $P, $H) : à vérifier"


def _boite_native(genre, depart):
    """Boîte de dialogue Windows (tkinter), fenêtre racine cachée et au premier plan ; None si annulée."""
    import tkinter
    from tkinter import filedialog
    racine = tkinter.Tk()
    try:
        racine.withdraw()
        racine.attributes("-topmost", True)
        initial = depart if depart and os.path.isdir(depart) else (os.path.dirname(depart) if depart else "")
        options = {"parent": racine, "initialdir": initial or None}
        if genre == "dossier":
            choisi = filedialog.askdirectory(mustexist=True, **options)
        elif genre == "pto":
            choisi = filedialog.askopenfilename(filetypes=[("Projets Hugin", "*.pto"), ("Tous les fichiers", "*.*")],
                                                **options)
        else:
            choisi = filedialog.askopenfilename(**options)
    finally:
        racine.destroy()
    return os.path.normpath(choisi) if choisi else None


VERROU_BOITE = threading.Lock()         # une seule boîte native à la fois (Tk n'aime pas deux racines en parallèle)
BOITE_DEJA_OUVERTE = "Une boîte « Parcourir » est déjà ouverte : la fermer d'abord (elle peut être derrière le navigateur)."


def boite_exclusive(genre, depart, boite=_boite_native, verrou=VERROU_BOITE):
    """(ouverte, chemin choisi ou None) : la boîte n'est pas ouverte, et (False, None) est rendu aussitôt, si une
    autre l'est déjà (deuxième clic, autre onglet) ; on ne fait pas attendre une boîte cachée derrière la première."""
    if not verrou.acquire(blocking=False):
        return False, None
    try:
        return True, boite(genre, depart)
    finally:
        verrou.release()


async def parcourir(genre, depart):
    """Chemin choisi dans la boîte de dialogue native (fichier, .pto ou dossier selon `genre`), ou None.

    Le serveur tourne sur le poste de l'utilisateur : la boîte s'ouvre sur son écran, dans un fil à part
    (run.io_bound) pour ne pas bloquer la page. Si une boîte est déjà ouverte, rien ne s'ouvre : un avis le dit
    et None est rendu."""
    from nicegui import run, ui
    ouverte, choisi = await run.io_bound(boite_exclusive, genre, depart)
    if not ouverte:
        ui.notify(BOITE_DEJA_OUVERTE, type="warning", multi_line=True)
    return choisi


async def confirmer(message, oui, details=()):
    """Dialogue de confirmation (bouton `oui` ou Annuler) ; vrai si l'utilisateur confirme."""
    from nicegui import ui
    with ui.dialog() as dialogue, ui.card():
        ui.label(message).classes("font-bold")
        for d in details:
            ui.label(d).classes("text-sm")
        with ui.row():
            ui.button(oui, on_click=lambda: dialogue.submit(True)).props("no-caps color=negative")
            ui.button("Annuler", on_click=lambda: dialogue.submit(False)).props("flat no-caps")
    reponse = await dialogue
    dialogue.delete()
    return bool(reponse)


def _note_hors_panorama(champ, note, valeur):
    note.set_visibility(replace(champ, valeur=valeur).hors_panorama)


def _bouton_parcourir(champ, cible, genre):
    from nicegui import ui

    async def choisir():
        choisi = await parcourir(genre, cible.value or champ.depart)
        if choisi:
            cible.set_value(choisi)
    return ui.button("Parcourir…", on_click=choisir).props("flat dense no-caps")


def _libelle(champ):
    return champ.arg.nom + (" *" if champ.obligatoire else "")


def _obligatoire(champ):
    return {"Obligatoire": lambda v: bool(v)} if champ.obligatoire else None


def _champ_chemin(champ, genre):
    from nicegui import ui
    with ui.row().classes("w-full items-center no-wrap gap-2"):
        saisie = ui.input(_libelle(champ), value=champ.valeur or "", validation=_obligatoire(champ)).classes("grow")
        _bouton_parcourir(champ, saisie, genre)
    return saisie


def choix_initial(champ):
    """Choix sélectionné au départ dans la liste d'un champ « pto » : celui qui désigne la valeur préremplie
    (casse et séparateurs ignorés) ; sans valeur, aucun choix s'il y a des .pto à proposer, sinon « Autre… »."""
    if champ.valeur:
        forme = os.path.normcase(os.path.normpath(champ.valeur))
        for choix in champ.choix:
            if choix != AUTRE and os.path.normcase(os.path.normpath(choix)) == forme:
                return choix
    return None if len(champ.choix) > 1 else AUTRE


def _champ_pto(champ):
    """Liste déroulante des .pto de la phase, plus « Autre… » qui fait apparaître un champ texte + Parcourir."""
    from nicegui import ui
    depart = choix_initial(champ)
    liste = ui.select(champ.choix, value=depart, label=_libelle(champ)).classes("w-full")
    with ui.row().classes("w-full items-center no-wrap gap-2") as ligne:
        saisie = ui.input("Autre chemin", value="").classes("grow")
        _bouton_parcourir(champ, saisie, "pto")
    ligne.set_visibility(depart == AUTRE)
    liste.on_value_change(lambda e: ligne.set_visibility(e.value == AUTRE))
    liste.saisie_autre = saisie         # lu par valeurs()
    return liste


def rendre(liste_champs, sans_note=()):
    """Pose un élément par champ dans le conteneur NiceGUI courant ; retourne {nom d'argument: élément}.

    `sans_note` : arguments dont le chemin n'a pas à être sous le panorama (chemins d'outils)."""
    from nicegui import ui
    elements = {}
    for champ in liste_champs:
        with ui.column().classes("w-full gap-0"):
            if champ.genre == "interrupteur":
                element = ui.switch(champ.arg.nom, value=bool(champ.valeur))
            elif champ.genre == "pto":
                element = _champ_pto(champ)
            elif champ.genre in ("fichier", "dossier"):
                element = _champ_chemin(champ, champ.genre)
            else:
                element = ui.input(_libelle(champ), value=str(champ.valeur or ""),
                                   validation=_obligatoire(champ)).classes("w-full")
                if champ.genre == "nombre":
                    element.props("inputmode=decimal")
            aide = champ.aide + (" (séparés par des espaces)" if champ.arg.type == "liste" else "")
            if aide:
                ui.label(aide).classes("text-xs text-gray-500")
            if champ.genre in GENRES_CHEMIN and champ.arg.nom not in sans_note:
                note = ui.label(NOTE_HORS_PANORAMA).classes("text-xs text-amber-700 italic")
                _note_hors_panorama(champ, note, champ.valeur)
                source = getattr(element, "saisie_autre", None)
                element.on_value_change(lambda e, c=champ, n=note: _note_hors_panorama(c, n, e.value))
                if source is not None:
                    source.on_value_change(lambda e, c=champ, n=note: _note_hors_panorama(c, n, e.value))
        elements[champ.arg.nom] = element
    return elements


def valeurs(elements):
    """Valeurs saisies : {nom d'argument: chaîne, ou booléen pour un interrupteur}."""
    resultat = {}
    for nom, element in elements.items():
        v = element.value
        if v == AUTRE and hasattr(element, "saisie_autre"):
            v = element.saisie_autre.value
        resultat[nom] = v if isinstance(v, bool) else ("" if v is None else str(v).strip())
    return resultat
