"""Mémorisation des réglages d'une tâche et report automatique des valeurs d'une phase à la suivante.

Logique pure, sans NiceGUI : l'interface web l'appelle, les tests la vérifient seuls. Les réglages mémorisés
vont dans panorama.json (Panorama.reglages, clé = identifiant de tâche) ; les valeurs reportées remplissent les
champs chemin du Panorama (maitre, hdr_pto, rendu_hdr, calques_hdr, pleine_res) que la tâche suivante préremplit.
"""

import os

from pilotage import config
from pilotage.catalogue import Tache  # noqa: F401  (type des paramètres)


def memorisables(arguments):
    """Les arguments dont la valeur se mémorise : ceux que le panorama ou les outils ne préremplissent pas."""
    return [a for a in arguments if a.config is None]


def memoriser(p, identifiant, arguments, valeurs, enregistrer=config.enregistrer_panorama):
    """Remplace les réglages mémorisés de `identifiant` par les valeurs renseignées des arguments mémorisables."""
    ecrit = {}
    for a in memorisables(arguments):
        v = valeurs.get(a.nom)
        if v is None or v == "":
            continue
        ecrit[a.nom] = bool(v) if a.type == "drapeau" else str(v)
    p.reglages[identifiant] = ecrit
    enregistrer(p)
    return ecrit


class _Renseignees(dict):
    """Valeurs pour format_map : une valeur absente ou vide lève KeyError, donc la source est omise."""

    def __missing__(self, cle):
        raise KeyError(cle)

    def __getitem__(self, cle):
        v = super().__getitem__(cle)
        if v is None or v == "":
            raise KeyError(cle)
        return v


def _stocker(p, cle, chemin):
    return config.ranger_chemin(p, chemin) if cle in config.CLES_CHEMIN_P else chemin


def resoudre(tache, valeurs, p):
    """Valeurs à reporter pour chaque clé de `tache.reporte` ; une source sans valeur est omise."""
    sources = _Renseignees(valeurs)
    resolu = {}
    for cle, source in tache.reporte.items():
        if source == "attendu":
            brut = os.path.join(p.P, tache.attendu) if tache.attendu else ""
        elif "{" in source:
            try:
                brut = source.format_map(sources)
            except (KeyError, IndexError, ValueError):
                continue
        else:
            brut = valeurs.get(source)
        if brut is None or brut == "":
            continue
        resolu[cle] = _stocker(p, cle, str(brut))
    return resolu


def reporter_apres_execution(tache, valeurs, p, enregistrer=config.enregistrer_panorama):
    """Affecte au panorama les valeurs reportées par `tache` ; retourne [(clé, valeur stockée)] des changements."""
    changes = []
    for cle, stocke in resoudre(tache, valeurs, p).items():
        if getattr(p, cle, None) != stocke:
            setattr(p, cle, stocke)
            changes.append((cle, stocke))
    if changes:
        enregistrer(p)
    return changes


def etat_geste(tache, p):
    """(le fichier attendu existe, son chemin absolu) ; (False, "") sans attendu ou sans panorama."""
    if p is None or not tache.attendu:
        return False, ""
    chemin = os.path.join(p.P, tache.attendu)
    return os.path.isfile(chemin), chemin


def reporter_geste(tache, p, enregistrer=config.enregistrer_panorama):
    """Reporte le fichier produit par un geste s'il existe et qu'il est plus récent que celui désigné par la clé.

    Retourne la valeur stockée, ou None si rien n'a changé."""
    existe, attendu = etat_geste(tache, p)
    if not existe:
        return None
    for cle, source in tache.reporte.items():
        if source != "attendu":
            continue
        courant = config.valeur(p, cle)
        if courant and os.path.isfile(courant) and os.stat(courant).st_mtime >= os.stat(attendu).st_mtime:
            continue
        stocke = _stocker(p, cle, attendu)
        setattr(p, cle, stocke)
        enregistrer(p)
        return stocke
    return None
