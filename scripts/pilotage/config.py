"""Configuration du poste (outils, panoramas connus, panorama courant) et d'un panorama ($T\\panorama.json).

Les deux fichiers sont hors dépôt : la configuration du poste dans %LOCALAPPDATA%\\giga-pano-hdr\\config.json
(repli : ~/.giga-pano-hdr/config.json), celle d'un panorama dans son dossier de travail $T, qu'elle suit s'il
est déplacé. Les scripts et le lanceur les LISENT pour préremplir leurs menus ; seuls le lanceur (menu
Configuration, Nouveau panorama) les ÉCRIT. Un script lancé avec des arguments ne les lit pas.
"""

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Optional

DOSSIERS_PHASE = ["3_grille", "3_optimisation", "4_vue_centree", "5_hdr", "6_pleine_res", "7_tuiles", "_a_supprimer"]
NOM_FICHIER_PANORAMA = "panorama.json"


def chemin_poste():
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "giga-pano-hdr" / "config.json"
    return Path.home() / ".giga-pano-hdr" / "config.json"


@dataclass
class Poste:
    outils: dict = field(default_factory=dict)      # cle d'outil -> chemin de l'exécutable (ou dossier Hugin)
    panoramas: list = field(default_factory=list)   # les $T connus
    courant: Optional[str] = None                   # le $T courant


@dataclass
class Panorama:
    T: str
    P: str
    H: str = ""
    lignes: Optional[int] = None
    colonnes: Optional[int] = None
    expos: Optional[int] = None
    focale: Optional[float] = None
    largeur_mm: Optional[float] = None
    pas_h: Optional[float] = None
    pas_v: Optional[float] = None
    largeur_hdr: Optional[int] = None
    largeur_pleine: Optional[int] = None
    maitre: str = ""                     # relatif à P, ex. 3_optimisation\pano_grille_opt4.pto
    export_l: str = "Export-TIFF-L"
    export_h: str = "Export-TIFF-H"


def _lire_json(chemin):
    try:
        return json.loads(Path(chemin).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _ecrire_json(chemin, donnees):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _depuis_dict(classe, donnees):
    connus = {f.name for f in fields(classe)}
    return classe(**{k: v for k, v in donnees.items() if k in connus})


def charger_poste(chemin=None):
    donnees = _lire_json(chemin or chemin_poste())
    if not isinstance(donnees, dict):
        return Poste()
    return _depuis_dict(Poste, donnees)


def enregistrer_poste(poste, chemin=None):
    _ecrire_json(chemin or chemin_poste(), asdict(poste))


def charger_panorama(T):
    donnees = _lire_json(Path(T) / NOM_FICHIER_PANORAMA)
    if not isinstance(donnees, dict) or "T" not in donnees or "P" not in donnees:
        return None
    return _depuis_dict(Panorama, donnees)


def enregistrer_panorama(p):
    _ecrire_json(Path(p.T) / NOM_FICHIER_PANORAMA, asdict(p))


def panorama_courant(poste):
    return charger_panorama(poste.courant) if poste.courant else None


def creer_arborescence(p):
    """Crée $T, les deux dossiers d'export, $P et ses dossiers de phase ; retourne les dossiers créés."""
    voulus = [Path(p.T), Path(p.T) / p.export_l, Path(p.T) / p.export_h, Path(p.P)]
    voulus += [Path(p.P) / d for d in DOSSIERS_PHASE]
    crees = []
    for dossier in voulus:
        if not dossier.exists():
            dossier.mkdir(parents=True, exist_ok=True)
            crees.append(dossier)
    return crees


def dossier_phase(p, phase):
    return Path(p.P) / phase if p else None


_FIXES = {
    "table": lambda p: os.path.join(p.P, "table_raw_LCE.csv"),
    "grille_pto": lambda p: os.path.join(p.P, "3_grille", "pano_grille.pto"),
    "cp_pto": lambda p: os.path.join(p.P, "3_grille", "pano_grille_cp.pto"),
    "export_l": lambda p: os.path.join(p.T, p.export_l),
    "export_h": lambda p: os.path.join(p.T, p.export_h),
    "maitre": lambda p: os.path.join(p.P, p.maitre) if p.maitre else None,
}


def valeur(p, cle):
    """Valeur de préremplissage (chaîne) pour une clé de configuration ; None si inconnue ou non renseignée."""
    if p is None:
        return None
    if cle in _FIXES:
        return _FIXES[cle](p)
    if cle in ("T", "P", "H"):
        return getattr(p, cle) or None
    v = getattr(p, cle, None)
    return None if v in (None, "") else str(v)
