"""En-tête de la page web : nom, sélecteur du panorama courant, résumé (grille, maître, outils, tâches en cours),
accès aux pages hors tâches, Aide et Quitter.

Fonctions pures en haut (testées sans serveur), construction NiceGUI en bas ; NiceGUI n'est importé qu'à l'appel.
"""

import os
import threading
from pathlib import Path

from pilotage import config, outils

from . import execution, formulaire, pages_poste, reglages

DELAI_SORTIE_FORCEE = 10             # secondes entre « Quitter » et la sortie forcée du processus


# ---------------------------------------------------------------- fonctions pures

def grille(p):
    """« L×C×E » du panorama ; « ? » pour une dimension inconnue ; None sans panorama."""
    if p is None:
        return None
    return "×".join("?" if v is None else str(v) for v in (p.lignes, p.colonnes, p.expos))


def maitre_present(p):
    v = config.valeur(p, "maitre")
    return bool(v and os.path.isfile(v))


def coches(etats):
    """[(nom, présent, version)] des outils résumés dans l'en-tête, dans l'ordre de outils.RESUME_CLES."""
    par_cle = {e.outil.cle: e for e in etats}
    return [(par_cle[c].outil.nom, par_cle[c].present, par_cle[c].version) for c in outils.RESUME_CLES if c in par_cle]


def changer_panorama(ctx, T, enregistrer=config.enregistrer_poste):
    """Rend `T` courant sur le poste, l'enregistre et recharge le panorama ; retourne le panorama (None si illisible)."""
    with reglages.VERROU_PANORAMA:
        ctx.poste.courant = T
        enregistrer(ctx.poste)
        ctx.panorama = config.panorama_courant(ctx.poste)
    return ctx.panorama


def options_panoramas(poste):
    """{$T: libellé} des panoramas connus du poste, le courant compris même s'il n'est pas dans la liste."""
    connus = list(poste.panoramas)
    if poste.courant and poste.courant not in connus:
        connus.append(poste.courant)
    noms = [Path(T).name or T for T in connus]
    return {T: (nom if noms.count(nom) == 1 else T) for T, nom in zip(connus, noms)}


# ---------------------------------------------------------------- partie NiceGUI

def construire(etat):
    """Pose la fonction rafraîchissable de l'en-tête dans `etat.en_tete` (la page l'appelle dans ui.header)."""
    from nicegui import app, run, ui

    ctx = etat.ctx

    async def quitter():
        cours = execution.en_cours()
        if cours and not await formulaire.confirmer("Des tâches tournent encore : elles seront arrêtées.",
                                                    "Arrêter et quitter", [ex.identifiant for ex in cours]):
            return
        for ex in cours:
            await run.io_bound(execution.arreter, ex)
        ui.notify("Serveur arrêté : vous pouvez fermer l'onglet.")
        app.shutdown()
        # filet : une fois, le serveur a cessé d'écouter sans que le processus se termine (non reproduit ; cause
        # probable : fils du pool io_bound encore occupés, boîte Parcourir ouverte ou taskkill lent, que l'arrêt
        # attend) ; les scripts lancés sont déjà arrêtés, rien n'est perdu à forcer la sortie quelques secondes après
        filet = threading.Timer(DELAI_SORTIE_FORCEE, os._exit, (0,))
        filet.daemon = True
        filet.start()

    def choisir_panorama(e):
        if not e.value or e.value == ctx.poste.courant:
            return
        if changer_panorama(ctx, e.value) is None:
            ui.notify(f"panorama.json illisible dans {e.value}", type="warning")
        etat.dossier_apercus = None
        etat.rafraichir()

    @ui.refreshable
    def en_tete():
        p = ctx.panorama
        ui.label("giga-pano-hdr").classes("text-lg font-bold")
        options = options_panoramas(ctx.poste)
        if options:
            ui.select(options, value=ctx.poste.courant if ctx.poste.courant in options else None,
                      on_change=choisir_panorama).props("dense dark options-dense").classes("min-w-64")
        else:
            ui.label("aucun panorama")
        if p is not None:
            ui.label(f"grille {grille(p)}")
            ui.label("maître OK" if maitre_present(p) else "maître absent").classes(
                "text-green-300" if maitre_present(p) else "text-amber-300")
        ui.label(" · ".join(f"{nom} {'✓' if ok else '✗'}" for nom, ok, _ in coches(ctx.etats))).classes("text-sm")
        n = len(execution.en_cours())
        ui.label(f"{n} en cours").classes("text-amber-300" if n else "text-gray-300")
        ui.space()
        for nom, vue in (("Panorama", "panorama"), ("Nouveau panorama", "nouveau"), ("Phase 0", "phase0"),
                         ("⚙ Configuration", "configuration")):
            ui.button(nom, on_click=lambda v=vue: pages_poste.ouvrir_vue(etat, v)).props("flat dense no-caps color=white")
        ui.button("Aide", on_click=lambda: etat.volet.toggle()).props("flat dense no-caps color=white")
        ui.button("Quitter", on_click=quitter).props("dense no-caps color=negative")

    etat.en_tete = en_tete
    return en_tete
