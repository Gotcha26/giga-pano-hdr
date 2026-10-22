"""Catalogue déclaratif des tâches de la chaîne : une Tache par repère du guide, lue par le lanceur console
(panorama.py) et, plus tard, par l'interface web.

Déclaratif pur : ce module ne connaît ni les menus, ni l'exécution des scripts. Seul Arg est importé, pour
les déclarations d'arguments propres à une tâche (une variante d'un script déjà déclaré dans ce script).

Une tâche = un script, une action du lanceur ou un geste (dans Hugin ou Lightroom). Un script cité sous
plusieurs repères a une tâche par repère ; une seule porte `groupe_console`, celle dont le sous-titre est
le texte affiché dans la console. Les autres ont `groupe_console` vide : absentes de la console.
"""

import dataclasses
import re
from dataclasses import dataclass, field

from .arguments import Arg

PHASES = (0, 1, 2, 3, 4, 5, 6, 7, "mesures")


@dataclass
class Tache:
    tete: str
    phase: object                           # 0..7 ou "mesures"
    repere: str = ""                        # repère du guide : "3C.2", "5B", ...
    script: str = ""                        # nom du script dans scripts/
    action: str = ""                        # fonction propre à la façade : "cpclean", "versions", ...
    sous_titre: str = ""                    # texte affiché après la tête dans la console
    effet: object = None                    # None = lecture seule ; sinon la cible écrite
    section: str = ""                       # section du menu console
    arguments: object = None                # déclaration propre à la tâche (sinon : celle du script)
    outils: tuple = ()                      # clés d'outils requis (outils.OUTILS)
    geste: str = ""                         # rappel d'un geste dans Hugin ou Lightroom (aucun script)
    attendu: str = ""                       # fichier que le geste doit produire, relatif à $P
    reporte: dict = field(default_factory=dict)   # clé du panorama.json -> argument ou attendu qui la remplit
    sortie: str = ""                        # nom de l'argument « dossier de sortie »
    groupe_console: str = ""                # "phase2", "phase3", "rendus", "mesures", "phase7" ; vide = hors console
    variante: str = ""                      # distingue deux tâches de même repère et même script
    ecrit: str = ""                         # ce que le menu de pilotage annonce écrire, si `arguments` est donné

    @property
    def identifiant(self):
        base = f"{self.repere or self.phase}/{self.script or self.action or 'geste'}"
        return f"{base}#{self.variante}" if self.variante else base

    @property
    def est_geste(self):
        return self.geste != ""


# ---------------------------------------------------------------- tâches de la console

S2 = "PHASE 2 — CONTRÔLER ET RENOMMER L'EXPORT"
S3A, S3B = "GRILLE ET POINTS (3A à 3D)", "OPTIMISER ET REPLACER (3E à 3H)"
S4, S5, S6 = "PHASE 4 — VUE CENTRÉE", "PHASE 5 — HDR", "PHASE 6 — PLEINE RÉSOLUTION"
SCIEL, SGEO = "CIEL ET RACCORDS", "GÉOMÉTRIE ET CHARGE"
S7 = "PHASE 7 — TUILER ET CADRER"

_TABLE = [Arg("REFERENCE", "Dossier déjà renommé L_C_E", type="dossier", config="export_l"),
          Arg("NOUVEL_EXPORT", "Fichier CSV à écrire (table raw,lce)", type="chemin", config="table"),
          Arg("--table", "Écrire la table", type="drapeau", defaut=True)]
_CONTROLE = [Arg("--controle", "Pleine résolution recadrée dont mesurer le vide par coin", type="chemin", obligatoire=True),
             Arg("--vips", "Chemin de vips.exe", type="chemin", config="outil:vips")]

_CONSOLE = [
    # phase 2
    Tache("Vérifier l'ordre et le motif d'exposition", 2, "2E", "verifier_ordre.py", sous_titre="verifier_ordre.py (2E)",
          section=S2, groupe_console="phase2"),
    Tache("Contrôler les réglages Lightroom des TIFF", 2, "2E", "controle_reglages_export.py",
          sous_titre="controle_reglages_export.py (2E)", section=S2, groupe_console="phase2"),
    Tache("Mesurer l'écart de rendu entre voisines", 2, "2E", "ecart_paires.py",
          sous_titre="ecart_paires.py (2E, à partir de la Phase 3)", section=S2, groupe_console="phase2"),
    Tache("Lire la taille d'un TIFF", 2, "", "tiffinfo.py", sous_titre="tiffinfo.py", section=S2, groupe_console="phase2"),
    Tache("Renommer le premier export en L_C_E", 2, "2F", "renommer_pano.py",
          sous_titre="renommer_pano.py (2F) : contrôlé par la table, ou l'écrit",
          effet="noms de fichiers du dossier et table_raw_LCE.csv si elle manque (essai à blanc sans --apply)",
          section=S2, groupe_console="phase2"),
    Tache("Écrire la table RAW → L_C_E", 2, "2F", "renommer_par_raw.py",
          sous_titre="renommer_par_raw.py --table (export déjà renommé autrement)", effet="table_raw_LCE.csv",
          section=S2, arguments=_TABLE, ecrit="la table CSV", groupe_console="phase2", variante="table"),
    Tache("Renommer un export d'après la table RAW", 2, "2D", "renommer_par_raw.py",
          sous_titre="renommer_par_raw.py (2D, 6A.2)",
          effet="noms de fichiers du nouvel export (essai à blanc sans --apply)", section=S2, groupe_console="phase2"),
    # phase 3
    Tache("Générer le projet de grille", 3, "3A", "generer_pto.py", sous_titre="generer_pto.py (3A)",
          effet="3_grille\\pano_grille.pto", section=S3A, groupe_console="phase3"),
    Tache("3B — Points de contrôle", 3, "3B",
          geste="dans Hugin : Photos → CPFind (prealigned) → Créer des points → Enregistrer sous 3_grille\\pano_grille_cp.pto",
          section=S3A, groupe_console="phase3"),
    Tache("Nettoyer les points", 3, "3C.1", action="cpclean", sous_titre="cpclean -p -n 2 (3C.1)",
          effet="3_optimisation\\…_clean.pto", section=S3A, outils=("hugin",), groupe_console="phase3"),
    Tache("Remettre les chemins d'images en relatifs", 3, "3C.1", "deplacer_projet.py",
          sous_titre="deplacer_projet.py (3C.1, après cpclean)", effet="le projet, en place", section=S3A,
          groupe_console="phase3"),
    Tache("Vérifier la grille", 3, "3C.2", "diagnostic_cp.py", sous_titre="diagnostic_cp.py (3C.2)", section=S3A,
          groupe_console="phase3"),
    Tache("Chercher le pas vertical réel", 3, "3C.3", "diagnostic_pas_v.py", sous_titre="diagnostic_pas_v.py (3C.3)",
          section=S3A, groupe_console="phase3"),
    Tache("Appliquer le pas vertical", 3, "3C.3", "corriger_pas_v.py", sous_titre="corriger_pas_v.py (3C.3)",
          effet="le projet de sortie", section=S3A, groupe_console="phase3"),
    Tache("Filtrer les faux points", 3, "3D", "filtrer_cp.py", sous_titre="filtrer_cp.py (3D)",
          effet="le projet de sortie", section=S3A, groupe_console="phase3"),
    Tache("Préparer l'optimisation", 3, "3E", "preparer_optimisation.py", sous_titre="preparer_optimisation.py (3E)",
          effet="le projet de sortie", section=S3B, groupe_console="phase3"),
    Tache("3E — Optimiser", 3, "3E",
          geste="dans Hugin : ouvrir le projet préparé → Optimiser maintenant ! → Yes → Enregistrer sous",
          section=S3B, groupe_console="phase3"),
    Tache("Replacer les images du ciel", 3, "3G", "placer_isoles.py", sous_titre="placer_isoles.py (3G)",
          effet="le projet de sortie", section=S3B, groupe_console="phase3"),
    Tache("Affiner les images faibles", 3, "3G", "affiner_images_faibles.py", sous_titre="affiner_images_faibles.py (3G)",
          effet="le projet de sortie", section=S3B, groupe_console="phase3"),
    Tache("Détecter les trous", 3, "3H", "detecter_trous.py", sous_titre="detecter_trous.py (3H)", section=S3B,
          groupe_console="phase3"),
    Tache("Compter les points d'une paire", 3, "3H", "compter_cp_paire.py", sous_titre="compter_cp_paire.py (3H)",
          section=S3B, groupe_console="phase3"),
    # rendus (phases 4 à 6)
    Tache("Régler la taille du projet", 4, "4A", "redimensionner_projet.py",
          sous_titre="redimensionner_projet.py (4A, 6C.1)", effet="le projet de sortie", section=S4,
          groupe_console="rendus"),
    Tache("Rendre un projet (nona puis fusion)", 4, "4A", "rendre_projet.ps1",
          sous_titre="rendre_projet.ps1 (4A, 6B, 6C.4)", effet="le dossier de rendu", section=S4,
          outils=("hugin", "multiblend"), sortie="-Sortie", groupe_console="rendus"),
    Tache("Ranger les images intermédiaires", 4, "4B", "ranger_intermediaires.py",
          sous_titre="ranger_intermediaires.py (4B)", effet="_a_supprimer\\ (essai à blanc sans --apply)", section=S4,
          groupe_console="rendus"),
    Tache("Reporter la géométrie sur les expositions", 5, "5A", "propager_geometrie.py",
          sous_titre="propager_geometrie.py (5A)", effet="le projet HDR dérivé", section=S5,
          reporte={"hdr_pto": "sortie.pto"}, groupe_console="rendus"),
    Tache("Reprojeter les images une à une", 5, "5B", "nona_images.ps1", sous_titre="nona_images.ps1 (5B, 6B, 6C.2)",
          effet="le dossier de rendu (f_NNNN.tif)", section=S5, outils=("hugin",),
          reporte={"rendu_hdr": "-Sortie"}, sortie="-Sortie", groupe_console="rendus"),
    Tache("Fusionner un calque par exposition", 5, "5B", "fusionner_par_exposition.ps1",
          sous_titre="fusionner_par_exposition.ps1 (5B)", effet="les calques pano_HDR_E*.tif", section=S5,
          outils=("multiblend",), reporte={"calques_hdr": "-Sortie"}, sortie="-Sortie", groupe_console="rendus"),
    Tache("5C — Fusion HDR", 5, "5C",
          geste="dans Lightroom : déplacer les calques dans $H, Synchroniser le dossier, Photo → Fusion de photos → HDR",
          section=S5, groupe_console="rendus"),
    Tache("6A — Export H", 6, "6A",
          geste="dans Lightroom : préréglage PANO TIFF (H) E0 depuis les copies virtuelles, puis renommer d'après la table RAW",
          section=S6, groupe_console="rendus"),
    Tache("Extraire un sous-projet", 6, "6B", "extraire_sous_projet.py", sous_titre="extraire_sous_projet.py (6B, 6C.1)",
          effet="le projet de sortie", section=S6, groupe_console="rendus"),
    Tache("Rattacher un projet à un dossier d'images", 6, "6B", "deplacer_projet.py",
          sous_titre="deplacer_projet.py --images (6B, 6C.1)", effet="le projet de sortie", section=S6,
          groupe_console="rendus"),
    Tache("Copier un rendu en version lisible", 6, "6B", "rendre_lisible.ps1", sous_titre="rendre_lisible.ps1 (6B)",
          effet="<nom>_lisible.tif et <nom>_sRGB.jpg", section=S6, outils=("vips",), groupe_console="rendus"),
    Tache("Surveiller multiblend pendant la fusion", 6, "6C.4", "surveiller_multiblend.ps1",
          sous_titre="surveiller_multiblend.ps1 (6C.4)", effet="le fichier de relevés", section=S6,
          groupe_console="rendus"),
    # mesures
    Tache("Luminosité du ciel par image", 3, "3F", "mesurer_ciel.py", sous_titre="mesurer_ciel.py (3F)",
          section=SCIEL, groupe_console="mesures"),
    Tache("Écart d'exposition entre voisines (ciel)", 3, "3F", "mesurer_gain_paires.py",
          sous_titre="mesurer_gain_paires.py (3F)", section=SCIEL, groupe_console="mesures"),
    Tache("Ondulation périodique d'un rendu", 3, "3F", "mesurer_bandes_ciel.py",
          sous_titre="mesurer_bandes_ciel.py (3F, 6C.5)", section=SCIEL, groupe_console="mesures"),
    Tache("Localiser les sauts de luminosité", 3, "3F", "localiser_sauts_ciel.py",
          sous_titre="localiser_sauts_ciel.py (3F)", section=SCIEL, groupe_console="mesures"),
    Tache("Comparer deux rendus (luminosité)", "mesures", "", "comparer_rendus.py", sous_titre="comparer_rendus.py",
          section=SCIEL, groupe_console="mesures"),
    Tache("Comparer des rendus (couleur)", "mesures", "", "comparer_couleur.py", sous_titre="comparer_couleur.py",
          section=SCIEL, groupe_console="mesures"),
    Tache("Rehausser le ciel pour voir les raccords", 6, "6C.5", "rehausser_ciel.py",
          sous_titre="rehausser_ciel.py (6C.5)", effet="l'image de sortie", section=SCIEL, groupe_console="mesures"),
    Tache("Profil d'une jonction", 6, "6C.5", "profil_jonction.ps1", sous_titre="profil_jonction.ps1 (6C.5)",
          section=SCIEL, outils=("vips",), groupe_console="mesures"),
    Tache("Voir les corrections par image", 3, "3E", "voir_positions.py", sous_titre="voir_positions.py (3E, 3G)",
          section=SGEO, groupe_console="mesures"),
    Tache("Lister les pires points de contrôle", 3, "3G", "lister_pires_cp.py",
          sous_titre="lister_pires_cp.py (3G)", section=SGEO, groupe_console="mesures"),
    Tache("Détecter les images aberrantes", 3, "3G", "detecter_aberrantes.py",
          sous_titre="detecter_aberrantes.py (3G)", section=SGEO, groupe_console="mesures"),
    Tache("Mesurer le vide d'un cadrage", 7, "7C", "cadrage_lightroom.py",
          sous_titre="cadrage_lightroom.py --controle (7C)", section=SGEO, arguments=_CONTROLE,
          groupe_console="mesures", variante="controle"),
    Tache("Mesurer la charge CPU et mémoire d'un rendu", "mesures", "", "mesurer_charge.ps1",
          sous_titre="mesurer_charge.ps1", section=SGEO, groupe_console="mesures"),
    # phase 7
    Tache("Tuiler un panorama en pyramide Deep Zoom", 7, "7A", "tuiler.ps1", sous_titre="tuiler.ps1 (7A)",
          effet="la pyramide .dzi et _files", section=S7, outils=("vips",), groupe_console="phase7"),
    Tache("Contrôler les tuiles dans le navigateur", 7, "7B", "controler_tuiles.py", sous_titre="controler_tuiles.py (7B)",
          section=S7, groupe_console="phase7"),
    Tache("7C — Cadrer", 7, "7C",
          geste="dans Lightroom, sur le DNG HDR : outil Recadrage, angle 0 ; exporter une copie virtuelle NON recadrée",
          section=S7, groupe_console="phase7"),
    Tache("Lire le cadrage Lightroom et imprimer les commandes", 7, "7C", "cadrage_lightroom.py",
          sous_titre="cadrage_lightroom.py (7C)", section=S7, groupe_console="phase7"),
    Tache("Empaqueter pour la mise en ligne", 7, "7D", "empaqueter.py", sous_titre="empaqueter.py (7D)",
          effet="<Sortie>\\<Nom>\\ et <Nom>.zip", section=S7, groupe_console="phase7"),
]


# ---------------------------------------------------------------- repères supplémentaires d'un script

def _aussi(identifiant, repere, **champs):
    """Copie hors console de la tâche `identifiant`, rattachée à un autre repère où le guide cite le même script."""
    source = next(t for t in _CONSOLE if t.identifiant == identifiant)
    champs = {"reporte": {}, **champs}
    return dataclasses.replace(source, repere=repere, phase=int(repere[0]) if repere else source.phase, groupe_console="", **champs)


_AUTRES_REPERES = [
    _aussi("2D/renommer_par_raw.py", "6A.2"),
    _aussi("3E/voir_positions.py", "3G"),
    _aussi("3F/mesurer_bandes_ciel.py", "6C.5"),
    _aussi("4A/redimensionner_projet.py", "6C.1"),
    _aussi("4A/rendre_projet.ps1", "6B"),
    _aussi("4A/rendre_projet.ps1", "6C.4", reporte={"pleine_res": "{-Sortie}\\{-Nom}.tif"}),
    _aussi("5B/nona_images.ps1", "6B"),
    _aussi("5B/nona_images.ps1", "6C.2"),
    _aussi("6B/extraire_sous_projet.py", "6C.1"),
    _aussi("6B/deplacer_projet.py", "6C.1"),
]


# ---------------------------------------------------------------- gestes absents de la console

_GESTES = [
    Tache("1A — Régler l'appareil", 1, "1A", geste="sur l'appareil : tout en manuel (mise au point, exposition, balance des blancs)"),
    Tache("1B — Respecter l'ordre de la séquence", 1, "1B", geste="à la prise de vue : balayer la grille dans l'ordre prévu"),
    Tache("2A — Sélectionner les photos", 2, "2A", geste="dans Lightroom : sélectionner les photos du panorama, dans l'ordre"),
    Tache("2B — Développement identique", 2, "2B", geste="dans Lightroom : appliquer le même développement à toutes les photos"),
    Tache("2C — Une retouche par finalité", 2, "2C", geste="dans Lightroom : travailler sur des copies virtuelles, pas sur les originaux"),
    Tache("2D — Exporter", 2, "2D", geste="dans Lightroom : exporter L et H avec les préréglages du guide"),
    Tache("3G — Réoptimisation", 3, "3G",
          geste="dans Hugin : ouvrir pano_grille_opt3_in.pto → Optimiser → Yes → Enregistrer sous "
                "3_optimisation\\pano_grille_opt.pto (le maître)",
          attendu=r"3_optimisation\pano_grille_opt.pto", reporte={"maitre": "attendu"}),
    Tache("5D — Finitions sur le HDR", 5, "5D", geste="dans Lightroom : finitions sur le DNG HDR (recadrage, tonalité)"),
]

TACHES = _CONSOLE + _AUTRES_REPERES + _GESTES


# ---------------------------------------------------------------- lecture

def cle_tri(repere):
    """Tri naturel d'un repère : 3C.1 avant 3C.2 avant 3D ; le repère vide en dernier."""
    m = re.fullmatch(r"(\d+)([A-Z]?)(?:\.(\d+))?", repere)
    if not m:
        return (99, repere, 0)
    return (int(m.group(1)), m.group(2), int(m.group(3) or 0))


def par_phase():
    """Les tâches regroupées par phase (0 à 7, puis « mesures »), triées par repère."""
    groupes = {phase: [] for phase in PHASES}
    for t in TACHES:
        groupes[t.phase].append(t)
    for taches in groupes.values():
        taches.sort(key=lambda t: cle_tri(t.repere))
    return groupes


def console(groupe):
    """Les tâches d'un menu de la console, dans l'ordre du catalogue."""
    return [t for t in TACHES if t.groupe_console == groupe]


def scripts_cites():
    return {t.script for t in TACHES if t.script}
