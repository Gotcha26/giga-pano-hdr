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

DOSSIERS_PHASE = ["3_grille", "3_optimisation", "4_vue_centree", "5_hdr", "6_pleine_res", "7_tuiles", "7_galerie",
                  "_a_supprimer"]
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
    hdr_pto: str = ""                    # chemins reportés d'une phase à la suivante (relatifs à P s'ils sont dessous)
    rendu_hdr: str = ""
    calques_hdr: str = ""
    pleine_res: str = ""
    reglages: dict = field(default_factory=dict)   # identifiant de tâche -> {nom d'argument: valeur mémorisée}


CLES_CHEMIN_P = ("maitre", "hdr_pto", "rendu_hdr", "calques_hdr", "pleine_res")


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
    """Le panorama de $T, ou None si son panorama.json manque ou est illisible ; des réglages mémorisés qui ne
    sont pas un dictionnaire (fichier corrompu, « null ») sont ignorés."""
    donnees = _lire_json(Path(T) / NOM_FICHIER_PANORAMA)
    if not isinstance(donnees, dict) or "T" not in donnees or "P" not in donnees:
        return None
    p = _depuis_dict(Panorama, donnees)
    if not isinstance(p.reglages, dict):
        p.reglages = {}
    return p


def enregistrer_panorama(p):
    _ecrire_json(Path(p.T) / NOM_FICHIER_PANORAMA, asdict(p))


def mettre_a_jour(T, /, **cles):
    """Relit le panorama.json de $T, lui applique `cles`, l'enregistre et retourne le panorama relu et modifié.

    Ce qui a changé sur disque depuis le chargement d'un objet Panorama gardé en mémoire (une autre tâche, un
    autre onglet, une modification à la main) est conservé : seules les clés données sont réécrites.
    `reglages={identifiant: {...}}` remplace les réglages de ces identifiants seulement ; `reglages={}` les
    vide tous. Une clé `T` différente déplace l'enregistrement dans le nouveau $T.
    FileNotFoundError si $T n'a pas de panorama.json lisible ; TypeError pour une clé inconnue."""
    p = charger_panorama(T)
    if p is None:
        raise FileNotFoundError(f"{NOM_FICHIER_PANORAMA} absent ou illisible dans {T}")
    connues = {f.name for f in fields(Panorama)}
    inconnues = set(cles) - connues
    if inconnues:
        raise TypeError(f"clé de panorama inconnue : {', '.join(sorted(inconnues))}")
    if "reglages" in cles:
        reglages = cles.pop("reglages")
        p.reglages = {**p.reglages, **reglages} if reglages else {}
    for cle, v in cles.items():
        setattr(p, cle, v)
    enregistrer_panorama(p)
    return p


def panorama_courant(poste):
    return charger_panorama(poste.courant) if poste.courant else None


def creer_arborescence(p):
    """Crée, dès la Phase 0, tous les dossiers du panorama : $T, les deux dossiers d'export, $P et ses dossiers de
    phase (jusqu'à 7_galerie), et, si $H est renseigné, $H et $H\\TIFF (export du HDR) ; retourne les dossiers créés."""
    voulus = [Path(p.T), Path(p.T) / p.export_l, Path(p.T) / p.export_h, Path(p.P)]
    voulus += [Path(p.P) / d for d in DOSSIERS_PHASE]
    if p.H:
        voulus += [Path(p.H), Path(p.H) / "TIFF"]
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
}


def _normaliser(chemin):
    return os.path.normcase(os.path.abspath(chemin))


def ranger_chemin(p, chemin):
    """Chemin à stocker dans panorama.json : relatif à $P s'il est dessous (casse ignorée), sinon inchangé."""
    if not chemin:
        return chemin
    racine = _normaliser(p.P)
    complet = _normaliser(chemin)
    if complet == racine or not complet.startswith(racine.rstrip(os.sep) + os.sep):
        return chemin
    return os.path.relpath(chemin, p.P)


def valeur(p, cle):
    """Valeur de préremplissage (chaîne) pour une clé de configuration ; None si inconnue ou non renseignée."""
    if p is None:
        return None
    if cle in CLES_CHEMIN_P:
        v = getattr(p, cle, "")
        if not v:
            return None
        return v if os.path.isabs(v) else os.path.join(p.P, v)
    if cle in _FIXES:
        return _FIXES[cle](p)
    if cle in ("T", "P", "H"):
        return getattr(p, cle) or None
    v = getattr(p, cle, None)
    return None if v in (None, "") else str(v)


# Valeurs du guide, proposées faute de mieux
DEFAUTS_GUIDE = {"largeur_mm": 24, "largeur_hdr": 20000}
RACINE_GUIDE = r"D:\Panoramas"      # 0D : $T = <racine>\<date>\<focale>, $H = <dossier des RAW>\HDR
QUESTIONS = [   # (clé, question, entier) ; la focale est demandée avant $T, qu'elle sert à nommer
    ("lignes", "Lignes de la grille", True),
    ("colonnes", "Colonnes de la grille", True),
    ("expos", "Expositions par position", True),
    ("largeur_mm", "Côté horizontal du capteur (mm : 24 en portrait plein format)", False),
    ("pas_h", "Pas horizontal (°)", False),
    ("pas_v", "Pas vertical (°)", False),
    ("largeur_hdr", "Largeur du HDR (px)", True),
    ("largeur_pleine", "Largeur de la pleine résolution (px)", True),
]


def propositions_nouveau(courant, date, focale, T, raws):
    """Valeurs proposées pour un nouveau panorama, d'après ce qui est déjà connu (None = pas encore donné).

    Les chemins suivent le guide (0D) : $T = <racine>\\<date>\\<focale>mm (racine du panorama courant, sinon
    D:\\Panoramas), $H = <dossier des RAW>\\HDR. Une valeur de question vient du panorama.json déjà présent dans
    $T, sinon du panorama courant (même série d'objectif), sinon du guide. `existant` : ce panorama.json, ou None."""
    racine = str(Path(courant.T).parent.parent) if courant and courant.T else RACINE_GUIDE
    if not T:
        T = str(Path(racine, date, f"{focale:g}mm" if focale else ""))
    existant = charger_panorama(T)
    if raws is None:
        raws = str(Path(existant.H).parent) if existant and existant.H else ""
    H = existant.H if existant and existant.H else (str(Path(raws, "HDR")) if raws else "")
    resultat = {"date": date, "focale": focale, "T": T, "raws": raws, "H": H, "existant": existant}
    source = existant or courant
    for cle, _, _ in QUESTIONS:
        v = getattr(source, cle, None) if source else None
        resultat[cle] = v if v is not None else DEFAUTS_GUIDE.get(cle)
    return resultat


def creer_nouveau(poste, valeurs):
    """Crée le panorama décrit par `valeurs` (T, H, focale et les clés de QUESTIONS), son arborescence et son
    panorama.json, le range parmi les panoramas connus du poste et le rend courant ; retourne (panorama, dossiers
    créés). Ce que `valeurs` ne porte pas (maître, noms d'export, chemins reportés, réglages mémorisés) est
    conservé d'un panorama.json déjà présent dans $T."""
    T = valeurs["T"]
    questions = {cle: valeurs.get(cle) for cle, _, _ in QUESTIONS}
    p = Panorama(T=T, P=os.path.join(T, "Assemblage-Hugin"), H=valeurs.get("H") or "",
                 focale=valeurs.get("focale"), **questions)
    existant = charger_panorama(T)
    if existant:
        for cle in ("export_l", "export_h", "reglages", *CLES_CHEMIN_P):
            setattr(p, cle, getattr(existant, cle))
    crees = creer_arborescence(p)
    enregistrer_panorama(p)
    if T not in poste.panoramas:
        poste.panoramas.append(T)
    poste.courant = T
    enregistrer_poste(poste)
    return p, crees
