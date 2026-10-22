"""Mémorisation des réglages d'une tâche et report automatique des valeurs d'une phase à la suivante.

Logique pure, sans NiceGUI : l'interface web l'appelle, les tests la vérifient seuls. Les réglages mémorisés
vont dans panorama.json (Panorama.reglages, clé = identifiant de tâche) ; les valeurs reportées remplissent les
champs chemin du Panorama (maitre, hdr_pto, rendu_hdr, calques_hdr, pleine_res) que la tâche suivante préremplit.
"""

import os
import threading

from pilotage import config

# Sérialise, dans le serveur web, les écritures de panorama.json et les changements de panorama courant : report
# depuis le fil de lecture d'une exécution, mémorisation, page Panorama, sélecteur de l'en-tête.
VERROU_PANORAMA = threading.Lock()


def memorisables(arguments):
    """Les arguments dont la valeur se mémorise : ceux que le panorama ou les outils ne préremplissent pas."""
    return [a for a in arguments if a.config is None]


def memoriser(p, identifiant, arguments, valeurs, mettre_a_jour=config.mettre_a_jour):
    """Remplace les réglages mémorisés de `identifiant` par les valeurs renseignées des arguments mémorisables.

    L'écriture relit panorama.json (`config.mettre_a_jour`) : rien de ce qui a changé sur disque depuis le
    chargement de `p` n'est perdu ; les réglages relus sont recopiés dans `p`."""
    ecrit = {}
    for a in memorisables(arguments):
        v = valeurs.get(a.nom)
        if v is None or v == "":
            continue
        ecrit[a.nom] = bool(v) if a.type == "drapeau" else str(v)
    relu = mettre_a_jour(p.T, reglages={identifiant: ecrit})
    p.reglages = relu.reglages
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
                brut = os.path.normpath(source.format_map(sources))   # « E:\R\ » + « \nom.tif » : un seul « \ »
            except (KeyError, IndexError, ValueError):
                continue
        else:
            brut = valeurs.get(source)
        if brut is None or brut == "":
            continue
        resolu[cle] = _stocker(p, cle, str(brut))
    return resolu


def reporter_apres_execution(tache, valeurs, p, mettre_a_jour=config.mettre_a_jour):
    """Écrit dans panorama.json les valeurs reportées par `tache` (relu avant écriture : seules ces clés
    changent) et les recopie dans `p` ; retourne [(clé, valeur stockée)] des changements."""
    changes = [(cle, stocke) for cle, stocke in resoudre(tache, valeurs, p).items() if getattr(p, cle, None) != stocke]
    if changes:
        mettre_a_jour(p.T, **dict(changes))
        for cle, stocke in changes:
            setattr(p, cle, stocke)
    return changes


def etat_geste(tache, p):
    """(le fichier attendu existe, son chemin absolu) ; (False, "") sans attendu, sans panorama ou sans $P
    (un attendu relatif joint à un $P vide désignerait un fichier du dossier courant)."""
    if p is None or not p.P or not tache.attendu:
        return False, ""
    chemin = os.path.join(p.P, tache.attendu)
    return os.path.isfile(chemin), chemin


def _date(chemin):
    """Date de modification, ou None si le fichier a disparu ou est illisible."""
    try:
        return os.stat(chemin).st_mtime
    except OSError:
        return None


def reporter_geste(tache, p, mettre_a_jour=config.mettre_a_jour):
    """Reporte le fichier produit par un geste s'il existe et qu'il est plus récent que celui désigné par la clé
    (écriture par `config.mettre_a_jour`, puis recopie dans `p`).

    Seule la PREMIÈRE clé dont la source est « attendu » est traitée : un geste ne produit qu'un fichier, que le
    catalogue reporte dans une seule clé (3G -> maitre). Un fichier courant illisible compte comme absent (le
    geste le remplace) ; un attendu disparu entre le contrôle d'existence et la lecture de sa date : rien ne change.
    Retourne la valeur stockée, ou None si rien n'a changé."""
    existe, attendu = etat_geste(tache, p)
    if not existe:
        return None
    cle = next((c for c, source in tache.reporte.items() if source == "attendu"), None)
    if cle is None:
        return None
    date_attendu = _date(attendu)
    if date_attendu is None:
        return None
    courant = config.valeur(p, cle)
    date_courant = _date(courant) if courant and os.path.isfile(courant) else None
    if date_courant is not None and date_courant >= date_attendu:
        return None
    stocke = _stocker(p, cle, attendu)
    mettre_a_jour(p.T, **{cle: stocke})
    setattr(p, cle, stocke)
    return stocke
