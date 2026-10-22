"""Colonne de gauche de la page web : l'arborescence des phases du guide et de leurs tâches.

Fonctions pures en haut (modèle de la colonne, libellés et titres des tâches), construction NiceGUI en bas.
"""

import re
from pathlib import Path

from pilotage import catalogue

from . import aide, pages_poste

TITRE_MESURES = "Mesures et inspection"
PHASE0_ENTREE = "Outils, préréglages, nouveau panorama"

RE_TITRE_PHASE = re.compile(r"^##\s+.*?(Phase (\d) — .+?)\s*$")


# ---------------------------------------------------------------- fonctions pures

def titres_phases(guide=aide.GUIDE):
    """{numéro de phase: « Phase N — titre du guide »}, lu dans les titres ## du guide ; vide s'il est illisible."""
    try:
        lignes = Path(guide).read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    titres = {}
    for ligne in lignes:
        m = RE_TITRE_PHASE.match(ligne)
        if m:
            titres.setdefault(int(m.group(2)), m.group(1))
    return titres


def arborescence(groupes=None, titres=None):
    """Modèle de la colonne : [(titre, [Tache])] pour les phases 0 à 7, puis « Mesures et inspection »."""
    groupes = catalogue.par_phase() if groupes is None else groupes
    titres = titres_phases() if titres is None else titres
    resultat = []
    for phase in catalogue.PHASES:
        titre_phase = TITRE_MESURES if phase == "mesures" else titres.get(phase, f"Phase {phase}")
        resultat.append((titre_phase, list(groupes.get(phase, []))))
    return resultat


def _tete_sans_repere(t):
    for prefixe in (t.repere + " — ", t.repere + " "):
        if t.repere and t.tete.startswith(prefixe):
            return t.tete[len(prefixe):]
    return t.tete


def libelle(t):
    """Libellé dans la colonne : le repère en préfixe (« 4A Rendre un projet… »)."""
    return f"{t.repere} {_tete_sans_repere(t)}" if t.repere else t.tete


def titre(t):
    """Titre de la zone centrale : « 4A — Rendre un projet… »."""
    return f"{t.repere} — {_tete_sans_repere(t)}" if t.repere else t.tete


# ---------------------------------------------------------------- partie NiceGUI

def construire(etat, arbre):
    """Pose la fonction rafraîchissable de la colonne dans `etat.colonne` et `ouvrir(tache)` dans `etat.ouvrir`."""
    from nicegui import ui

    def ouvrir(t, vue="tache"):
        etat.tache, etat.vue = t, vue
        etat.dossier_apercus = None
        etat.ex_vue, etat.lus, etat.etat_vu = None, 0, ""
        colonne.refresh()
        etat.centre.refresh()
        etat.aide.refresh()

    def suivre_depliage(titre_phase, ouvert):
        (etat.ouvertes.add if ouvert else etat.ouvertes.discard)(titre_phase)

    @ui.refreshable
    def colonne():
        with ui.list().props("dense").classes("w-full"):
            for titre_phase, taches in arbre:
                with ui.expansion(titre_phase, value=titre_phase in etat.ouvertes,
                                  on_value_change=lambda e, tp=titre_phase: suivre_depliage(tp, e.value)
                                  ).classes("w-full").props("dense"):
                    if titre_phase == arbre[0][0] and not taches:
                        ui.item(PHASE0_ENTREE, on_click=lambda: pages_poste.phase0(etat))
                    for t in taches:
                        item = ui.item(libelle(t), on_click=lambda t=t: ouvrir(t))
                        if t.est_geste:
                            item.classes("italic text-gray-500")
                        if etat.tache is t:
                            item.classes("bg-blue-100")

    etat.colonne, etat.ouvrir = colonne, ouvrir
    return colonne
