"""Les pages hors tâches du lanceur web : Panorama, Nouveau panorama, Phase 0 et Configuration.

Chaque page est un dialogue plein écran ouvert depuis l'en-tête (et, pour la Phase 0, depuis la colonne). Il est
posé à la racine de la page, hors des zones que `tout_rafraichir` reconstruit, qui l'effaceraient sinon. En haut
du module, les fonctions pures (champs du panorama, conversions, propositions du nouveau panorama, lignes du
tableau des outils), testées sans serveur ; en bas, les dialogues. NiceGUI n'est importé que dans ces derniers.

La logique est celle du lanceur console (`panorama.py`, `pilotage/config.py`, `pilotage/outils.py`) : mêmes
propositions de valeurs, même écriture de panorama.json et de la configuration du poste.
"""

import datetime
import os
import subprocess
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any, Optional

import panorama as lanceur
from pilotage import config, outils

from . import formulaire, reglages

GENRES_CHEMINS = {"T": "dossier", "P": "dossier", "H": "dossier", "export_l": "dossier", "export_h": "dossier",
                  "maitre": "pto", "hdr_pto": "pto", "rendu_hdr": "dossier", "calques_hdr": "dossier",
                  "pleine_res": "fichier"}
PHASES_PTO = {"maitre": "3_optimisation", "hdr_pto": "5_hdr"}
CLES_EXPORT = ("export_l", "export_h")
AIDES_PANORAMA = {"T": "dossier de travail $T", "P": "dossier d'assemblage $P", "H": "dossier HDR $H",
                  "focale": "focale (mm)", "export_l": "relatif à $T", "export_h": "relatif à $T",
                  **{cle: "relatif à $P s'il est dessous" for cle in config.CLES_CHEMIN_P},
                  **{cle: question for cle, question, _ in config.QUESTIONS}}

CHAMPS_NOUVEAU = [("date", "Date de la prise de vue (AAAA-MM-JJ)"), ("focale", "Focale (mm)"),
                  ("T", "Dossier de travail $T (hors catalogue Lightroom)"),
                  ("raws", "Dossier des RAW de ce panorama, dans le catalogue Lightroom (facultatif)"),
                  ("H", "Dossier HDR $H (calques et DNG HDR)"),
                  *[(cle, question) for cle, question, _ in config.QUESTIONS]]
ENTIERS_NOUVEAU = {cle for cle, _, entier in config.QUESTIONS if entier}
NOMBRES_NOUVEAU = {"focale", *(cle for cle, _, _ in config.QUESTIONS)}
DECLENCHEURS_NOUVEAU = ("date", "focale", "T", "raws")     # champs dont dépendent les propositions

GENRES_OUTILS = {cle: ("dossier" if cle == "hugin" else "fichier") for cle, _ in lanceur.OUTILS_CONFIGURABLES}

MESSAGE_PERIME = "Le panorama courant a changé depuis l'ouverture de la page : rien n'est écrit."
DELAI_RECALCUL = 0.4        # secondes de calme avant de recalculer les propositions du Nouveau panorama


# ---------------------------------------------------------------- fonctions pures

@dataclass
class ChampPanorama:
    nom: str
    genre: str                  # « dossier », « fichier », « pto », « entier », « reel » ou « texte »
    valeur: Any                 # forme stockée dans panorama.json
    phase: Optional[str] = None     # dossier de phase des .pto proposés
    aide: str = ""


def _genre(f):
    if f.name in GENRES_CHEMINS:
        return GENRES_CHEMINS[f.name]
    if f.type == Optional[int]:
        return "entier"
    if f.type == Optional[float]:
        return "reel"
    return "texte"


def champs_panorama(p):
    """Un champ par clé de panorama.json, sauf les réglages mémorisés, dans l'ordre de `config.Panorama`."""
    return [ChampPanorama(f.name, _genre(f), getattr(p, f.name), PHASES_PTO.get(f.name), AIDES_PANORAMA.get(f.name, ""))
            for f in fields(config.Panorama) if f.name != "reglages"]


def pto_de_la_phase(P, phase):
    """Les .pto du dossier de phase sous $P, en forme stockée (relative à $P), triés ; [] s'il n'existe pas."""
    if not P or not phase:
        return []
    dossier = Path(P) / phase
    if not dossier.is_dir():
        return []
    return sorted(os.path.join(phase, f.name) for f in dossier.glob("*.pto"))


def forme_stockee(nom, chemin, T, P):
    """Forme à stocker d'un chemin choisi : relatif à $P (clés reportées et maître) ou à $T (dossiers d'export)
    s'il est dessous ; sinon inchangé."""
    if nom in config.CLES_CHEMIN_P:
        return config.ranger_chemin(config.Panorama(T=T, P=P), chemin)
    if nom in CLES_EXPORT:
        return config.ranger_chemin(config.Panorama(T=T, P=T), chemin)
    return chemin


def chemin_absolu(nom, valeur, T, P):
    """Chemin complet d'une valeur en forme stockée (départ de « Parcourir ») ; "" si vide."""
    if not valeur:
        return os.path.join(P, PHASES_PTO[nom]) if nom in PHASES_PTO and P else ""
    if os.path.isabs(valeur):
        return valeur
    if nom in config.CLES_CHEMIN_P:
        return os.path.join(P, valeur)
    if nom in CLES_EXPORT:
        return os.path.join(T, valeur)
    return valeur


def nombre(v, entier=False):
    """Nombre saisi (chaîne, virgule décimale admise, ou nombre) ; None si vide ; ValueError s'il n'en est pas un
    ou, pour `entier`, s'il a une partie décimale."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, bool):
        raise ValueError(v)
    try:
        x = float(v) if isinstance(v, (int, float)) else float(str(v).strip().replace(",", "."))
        if not entier:
            return x
        if x != int(x):
            raise ValueError(v)
        return int(x)
    except OverflowError as e:
        raise ValueError(v) from e


def _convertir(nom, v, entier, erreurs):
    try:
        return nombre(v, entier)
    except ValueError:
        erreurs.append(f"{nom} : {'nombre entier' if entier else 'nombre'} attendu (« {v} »)")
        return None


def _texte(v):
    return "" if v is None else str(v).strip()


def lire_panorama(saisies):
    """Valeurs à écrire dans panorama.json d'après les saisies de la page Panorama : nombres convertis, chemins
    rangés sous $P (ou $T pour les exports) ; retourne (valeurs, erreurs). $T et $P sont obligatoires."""
    valeurs, erreurs = {}, []
    T, P = _texte(saisies.get("T")), _texte(saisies.get("P"))
    for c in champs_panorama(config.Panorama(T=T, P=P)):
        v = saisies.get(c.nom)
        if c.genre in ("entier", "reel"):
            valeurs[c.nom] = _convertir(c.nom, v, c.genre == "entier", erreurs)
        else:
            valeurs[c.nom] = forme_stockee(c.nom, _texte(v), T, P)
    for cle in ("T", "P"):
        if not valeurs[cle]:
            erreurs.append(f"{cle} : obligatoire")
    return valeurs, erreurs


def modifications_panorama(affichees, saisies):
    """Clés modifiées par l'utilisateur depuis l'affichage, avec leur nouvelle valeur ; retourne (modifiées,
    erreurs). Les autres ne sont pas réécrites : un report fait entre-temps par une tâche est conservé."""
    avant, _ = lire_panorama(affichees)
    apres, erreurs = lire_panorama(saisies)
    return {cle: v for cle, v in apres.items() if v != avant.get(cle)}, erreurs


def deplacement_refuse(ancien_T, nouveau_T):
    """Raison de refuser de déplacer le panorama de `ancien_T` vers `nouveau_T` (dossier introuvable, ou qui
    contient déjà un panorama.json, qu'on écraserait) ; None si le déplacement est permis ou si $T ne change pas."""
    if os.path.normcase(os.path.normpath(nouveau_T)) == os.path.normcase(os.path.normpath(ancien_T)):
        return None
    if not os.path.isdir(nouveau_T):
        return f"T : dossier introuvable ({nouveau_T})"
    if (Path(nouveau_T) / config.NOM_FICHIER_PANORAMA).exists():
        return (f"T : ce dossier contient déjà un {config.NOM_FICHIER_PANORAMA} ({nouveau_T}) : choisissez-le "
                "dans la liste des panoramas ou videz le dossier")
    return None


def p_refuse(nouveau_P):
    """Raison de refuser un nouveau $P : dossier introuvable (les phases, le maître et les chemins reportés y sont
    cherchés ; une faute de frappe les rendrait tous absents) ; None s'il existe."""
    if not os.path.isdir(nouveau_P):
        return f"P : dossier introuvable ({nouveau_P})"
    return None


def refus_enregistrement(ancien_T, modifiees):
    """Raisons de refuser d'enregistrer les clés `modifiees` de la page Panorama ($T puis $P contrôlés)."""
    raisons = []
    if "T" in modifiees:
        raisons.append(deplacement_refuse(ancien_T, modifiees["T"]))
    if "P" in modifiees:
        raisons.append(p_refuse(modifiees["P"]))
    return [r for r in raisons if r]


def page_encore_ouverte(client, element=None):
    """Vrai si l'onglet `client` est toujours connecté et `element` (le dialogue d'une page) pas supprimé : après
    une longue attente (installation), on ne touche à l'interface que dans ce cas."""
    if client is None or not getattr(client, "has_socket_connection", False) or getattr(client, "is_deleted", False):
        return False
    return not (element is not None and getattr(element, "is_deleted", False))


def bilan_installation(nom, resultat, erreur=None):
    """(message, type de notification) d'une installation : `erreur` (OSError au lancement : seul vrai « échec »),
    sinon le code de retour de `resultat` (0 = réussi ; autre = « warning » prudent : winget renvoie un code non
    nul pour « déjà installé » ou « aucune mise à jour », la détection dira si l'outil est là)."""
    if erreur is not None:
        return f"Installation impossible : {erreur}", "negative"
    if resultat.returncode == 0:
        return f"{nom} : installation terminée (code 0)", "positive"
    return (f"{nom} : commande terminée avec le code {resultat.returncode} : vérifier la détection ci-dessous",
            "warning")


def panoramas_apres_deplacement(panoramas, ancien_T, nouveau_T):
    """Liste des panoramas connus après un déplacement : `nouveau_T` à la place de `ancien_T`, sans doublon."""
    resultat = []
    for T in panoramas:
        T = nouveau_T if T == ancien_T else T
        if T not in resultat:
            resultat.append(T)
    if nouveau_T not in resultat:
        resultat.append(nouveau_T)
    return resultat


def valeurs_initiales_nouveau(courant, date):
    """Valeurs proposées à l'ouverture du formulaire Nouveau panorama (focale du panorama courant)."""
    focale = courant.focale if courant else None
    prop = config.propositions_nouveau(courant, date, focale, None, None)
    return {nom: prop.get(nom) for nom, _ in CHAMPS_NOUVEAU}


def recalculer_nouveau(courant, saisies, touches):
    """Propositions recalculées après un changement de date, focale, $T ou dossier des RAW ; retourne
    ({champ: valeur} pour les champs que l'utilisateur n'a pas modifiés, panorama.json déjà présent dans $T ou None)."""
    try:
        focale = nombre(saisies.get("focale"))
    except ValueError:
        focale = None
    T = _texte(saisies.get("T")) if "T" in touches else None
    raws = _texte(saisies.get("raws")) if "raws" in touches else None
    prop = config.propositions_nouveau(courant, _texte(saisies.get("date")), focale, T or None, raws)
    remplir = {nom: prop[nom] for nom, _ in CHAMPS_NOUVEAU if nom not in ("date", "focale") and nom not in touches}
    return remplir, prop["existant"]


def solder_recalcul(attente, recalculer):
    """Un recalcul des propositions qui attend son délai (`attente[0]`, minuteur NiceGUI) est annulé et fait tout
    de suite : « Créer » lit alors des propositions à jour. Vrai s'il y en avait un."""
    minuteur = attente[0]
    if minuteur is None:
        return False
    minuteur.cancel()
    attente[0] = None
    recalculer()
    return True


def lire_nouveau(saisies):
    """Valeurs passées à `config.creer_nouveau` (T, H, focale et les clés de QUESTIONS) ; retourne (valeurs,
    erreurs). $T est obligatoire ; les nombres entiers le sont là où QUESTIONS le dit."""
    erreurs = []
    valeurs = {"T": _texte(saisies.get("T")), "H": _texte(saisies.get("H"))}
    if not valeurs["T"]:
        erreurs.append("T : obligatoire")
    for nom in sorted(NOMBRES_NOUVEAU, key=[n for n, _ in CHAMPS_NOUVEAU].index):
        valeurs[nom] = _convertir(nom, saisies.get(nom), nom in ENTIERS_NOUVEAU, erreurs)
    return valeurs, erreurs


def lignes_outils(etats):
    """Lignes du tableau de la Phase 0 : nom, état, version, chemin, page de téléchargement, commande
    d'installation (outil absent seulement) et dossier conseillé pour une archive."""
    lignes = []
    for e in etats:
        o = e.outil
        lignes.append({"cle": o.cle, "nom": o.nom, "present": e.present, "etat": "OK" if e.present else "absent",
                       "version": (e.version or "version inconnue") if e.present else "",
                       "chemin": e.chemin or "", "url": o.url or "",
                       "commande": None if e.present else outils.commande_installation(o),
                       "dezipper": o.dezipper or ""})
    return lignes


def outils_modifies(actuels, saisies):
    """Chemins d'outils du poste après la page Configuration : une saisie vide retire la clé (détection
    automatique) ; les clés non saisies sont conservées. Retourne une copie."""
    resultat = dict(actuels)
    for cle, v in saisies.items():
        v = _texte(v)
        if v:
            resultat[cle] = v
        else:
            resultat.pop(cle, None)
    return resultat


def statut_outil(cle, configure, etats):
    """Ligne d'état d'un outil configurable : chemin détecté et version, et si le chemin configuré manque."""
    e = next((e for e in etats if e.outil.cle == cle), None)
    morceaux = []
    if configure and not os.path.exists(configure):
        morceaux.append("⚠ chemin configuré introuvable")
    if e is None or not e.present:
        morceaux.append("✗ absent")
    else:
        morceaux.append(f"✓ {e.version or 'version inconnue'} — {e.chemin}")
    return " ; ".join(morceaux)


# ---------------------------------------------------------------- partie NiceGUI

def _dialogue(titre):
    """Dialogue plein écran posé à la racine de la page ; retourne (dialogue, colonne du contenu)."""
    from nicegui import ui
    with ui.context.client.content:
        with ui.dialog().props("maximized") as dialogue, ui.card().classes("w-full h-full overflow-auto"):
            with ui.row().classes("w-full items-center"):
                ui.label(titre).classes("text-2xl font-bold")
                ui.space()
                ui.button("Fermer", on_click=dialogue.close).props("flat no-caps")
            corps = ui.column().classes("w-full max-w-4xl gap-2")
    dialogue.on("hide", dialogue.delete)
    dialogue.open()
    return dialogue, corps


def _champ_chemin(libelle, valeur, genre, depart=lambda: "", ranger=None, placeholder=""):
    """Champ texte + « Parcourir… » ; `ranger` met le chemin choisi en forme stockée."""
    from nicegui import ui
    with ui.row().classes("w-full items-center no-wrap gap-2") as ligne:
        saisie = ui.input(libelle, value=valeur or "", placeholder=placeholder).classes("grow")

        async def choisir():
            choisi = await formulaire.parcourir(genre, depart())
            if choisi:
                saisie.set_value(ranger(choisi) if ranger else choisi)
        ui.button("Parcourir…", on_click=choisir).props("flat dense no-caps")
    return saisie, ligne


def _notifier_erreurs(erreurs):
    from nicegui import ui
    for m in erreurs:
        ui.notify(m, type="negative", multi_line=True)


def panorama(etat):
    """Page Panorama : les clés de panorama.json du panorama courant (forme stockée), modifiables ; Enregistrer
    réécrit les clés modifiées ; « Oublier les réglages mémorisés » vide `reglages` après confirmation."""
    from nicegui import ui

    from . import entete       # import tardif : entete importe ce module
    ctx = etat.ctx
    p = ctx.panorama
    if p is None:
        ui.notify("Aucun panorama courant : voir Nouveau panorama", type="warning")
        return
    dialogue, corps = _dialogue("Panorama")
    elements, affichees = {}, {}

    def valeur_de(nom):
        return _texte(elements[nom].value) if nom in elements else ""

    def perime():
        if ctx.panorama is p:
            return False
        ui.notify(MESSAGE_PERIME, type="warning", multi_line=True)
        dialogue.close()
        return True

    def champ(c):
        if c.genre in ("entier", "reel"):
            el = ui.number(c.nom, value=c.valeur, precision=0 if c.genre == "entier" else None).classes("w-64")
        elif c.genre == "texte":
            el = ui.input(c.nom, value=c.valeur or "").classes("w-full")
        else:
            el, ligne = _champ_chemin(
                c.nom, c.valeur, c.genre,
                depart=lambda n=c.nom: chemin_absolu(n, valeur_de(n), valeur_de("T"), valeur_de("P")),
                ranger=lambda choisi, n=c.nom: forme_stockee(n, choisi, valeur_de("T"), valeur_de("P")))
            choix = pto_de_la_phase(p.P, c.phase) if c.genre == "pto" else []
            if choix:
                with ligne, ui.button(".pto de " + c.phase).props("flat dense no-caps icon-right=arrow_drop_down"):
                    with ui.menu():
                        for f in choix:
                            ui.menu_item(f, on_click=lambda f=f, el=el: el.set_value(f))
        if c.aide:
            ui.label(c.aide).classes("text-xs text-gray-500")
        return el

    @ui.refreshable
    def contenu():
        elements.clear()
        affichees.clear()
        ui.label(str(Path(p.T) / config.NOM_FICHIER_PANORAMA)).classes("text-sm text-gray-600")
        for c in champs_panorama(p):
            with ui.column().classes("w-full gap-0"):
                elements[c.nom] = champ(c)
            affichees[c.nom] = c.valeur
        with ui.row().classes("items-center gap-2"):
            ui.button("Enregistrer", on_click=enregistrer).props("no-caps color=primary")
            ui.button("Oublier les réglages mémorisés", on_click=oublier).props("outline no-caps color=negative")
            ui.label(f"Réglages mémorisés : {len(p.reglages)} tâche(s)" +
                     (" — " + ", ".join(sorted(p.reglages)) if p.reglages else "")).classes("text-sm text-gray-600")

    def enregistrer():
        if perime():
            return
        modifiees, erreurs = modifications_panorama(affichees, {n: el.value for n, el in elements.items()})
        if erreurs:
            _notifier_erreurs(erreurs)
            return
        if not modifiees:
            ui.notify("Rien n'a changé")
            return
        ancien_T = p.T
        raisons = refus_enregistrement(ancien_T, modifiees)
        if raisons:
            _notifier_erreurs(raisons)
            return
        try:
            with reglages.VERROU_PANORAMA:
                config.mettre_a_jour(ancien_T, **modifiees)    # relu sur disque : un report fait entre-temps reste
                for cle, v in modifiees.items():               # la mémoire ne suit qu'une écriture réussie
                    setattr(p, cle, v)
        except OSError as e:
            ui.notify(f"Écriture impossible : {e}", type="negative", multi_line=True)
            return
        ui.notify("Enregistré : " + ", ".join(modifiees), type="positive", multi_line=True)
        if p.T != ancien_T:         # panorama déplacé : le poste suit le nouveau $T
            ctx.poste.panoramas = panoramas_apres_deplacement(ctx.poste.panoramas, ancien_T, p.T)
            entete.changer_panorama(ctx, p.T)
            dialogue.close()
        else:
            contenu.refresh()
        etat.rafraichir()

    async def oublier():
        if not p.reglages:
            ui.notify("Aucun réglage mémorisé")
            return
        if not await formulaire.confirmer(f"Oublier les réglages mémorisés de {len(p.reglages)} tâche(s) ?", "Oublier",
                                     sorted(p.reglages)):
            return
        if perime():
            return
        try:
            with reglages.VERROU_PANORAMA:
                config.mettre_a_jour(p.T, reglages={})
                p.reglages = {}
        except OSError as e:
            ui.notify(f"Écriture impossible : {e}", type="negative", multi_line=True)
            return
        ui.notify("Réglages mémorisés oubliés")
        contenu.refresh()

    with corps:
        contenu()


def nouveau_panorama(etat):
    """Page Nouveau panorama : les questions du lanceur console en un formulaire ; les propositions sont
    recalculées quand la date, la focale, $T ou le dossier des RAW changent, sans toucher aux champs déjà
    modifiés à la main ; Créer écrit l'arborescence et panorama.json et rend le panorama courant."""
    from nicegui import ui

    ctx = etat.ctx
    dialogue, corps = _dialogue("Nouveau panorama")
    initiales = valeurs_initiales_nouveau(ctx.panorama, datetime.date.today().isoformat())
    elements, touches, remplissage, attente = {}, set(), [False], [None]

    def saisies():
        return {n: el.value for n, el in elements.items()}

    def recalculer_bientot():
        """Recalcul DELAI_RECALCUL s après la dernière modification d'un déclencheur, pas à chaque frappe (chaque
        recalcul relit le panorama.json du $T proposé) ; « Parcourir » passe aussi par là."""
        if attente[0] is not None:
            attente[0].cancel()
        with corps:
            attente[0] = ui.timer(DELAI_RECALCUL, recalculer, once=True)

    def recalculer():
        attente[0] = None
        remplir, existant = recalculer_nouveau(ctx.panorama, saisies(), touches)
        remplissage[0] = True
        try:
            for nom, v in remplir.items():
                elements[nom].set_value(v if nom in NOMBRES_NOUVEAU else (v or ""))
        finally:
            remplissage[0] = False
        info.set_text(f"panorama.json trouvé dans {existant.T} : ses valeurs sont proposées." if existant else "")

    def modifie(nom):
        if remplissage[0]:
            return
        touches.add(nom)
        if nom in DECLENCHEURS_NOUVEAU:
            recalculer_bientot()

    def creer():
        try:
            solder_recalcul(attente, recalculer)    # « Créer » moins de DELAI_RECALCUL s après la dernière frappe
        except (OSError, ValueError) as e:          # panorama.json illisible : on garde les saisies telles quelles
            ui.notify(f"Propositions impossibles : {e}", type="warning", multi_line=True)
        valeurs, erreurs = lire_nouveau(saisies())
        if erreurs:
            _notifier_erreurs(erreurs)
            return
        try:
            with reglages.VERROU_PANORAMA:
                p, crees = config.creer_nouveau(ctx.poste, valeurs)
                ctx.panorama = p
        except OSError as e:
            ui.notify(f"Création impossible : {e}", type="negative", multi_line=True)
            return
        etat.dossier_apercus = None
        ui.notify(f"Panorama courant : {p.T} ({len(crees)} dossier(s) créé(s))", type="positive", multi_line=True)
        etat.rafraichir()
        corps.clear()
        with corps:
            ui.label(f"panorama.json écrit dans {p.T} ; panorama courant.").classes("text-green-700")
            for d in crees:
                ui.label(f"créé : {d}").classes("text-sm")
            if not crees:
                ui.label("Tous les dossiers existaient déjà.").classes("text-sm text-gray-600")

    with corps:
        info = ui.label("").classes("text-sm text-blue-700")
        for nom, libelle in CHAMPS_NOUVEAU:
            v = initiales.get(nom)
            with ui.column().classes("w-full gap-0"):
                if nom in NOMBRES_NOUVEAU:
                    el = ui.number(libelle, value=v, precision=0 if nom in ENTIERS_NOUVEAU else None).classes("w-96")
                elif nom in ("T", "raws", "H"):
                    el, _ = _champ_chemin(libelle, v, "dossier", depart=lambda n=nom: _texte(elements[n].value))
                else:
                    el = ui.input(libelle, value=v or "").classes("w-64")
            el.on_value_change(lambda e, n=nom: modifie(n))
            elements[nom] = el
        ui.button("Créer", on_click=creer).props("no-caps color=primary")
        ui.label("Crée $T, les dossiers d'export, $P et ses dossiers de phase, $H et $H\\TIFF, puis panorama.json ; "
                 "un panorama.json déjà présent garde son maître, ses chemins reportés et ses réglages.").classes(
            "text-xs text-gray-500")
    recalculer()        # annonce, dès l'ouverture, un panorama.json déjà présent dans le $T proposé


def phase0(etat):
    """Page Phase 0 : tableau des outils détectés, installation de ce qui manque (sur confirmation), dossiers
    des préréglages Lightroom."""
    from nicegui import run, ui

    ctx = etat.ctx
    dialogue, corps = _dialogue("Phase 0 — outils et préréglages")

    async def detecter():
        ctx.etats = await run.io_bound(outils.detecter_tous, ctx.poste.outils)
        tableau.refresh()
        etat.rafraichir()

    async def installer(ligne):
        if ligne["commande"]:
            if not await formulaire.confirmer(f"Installer {ligne['nom']} ?", "Exécuter", [ligne["commande"]]):
                return
            client = ui.context.client          # l'installation peut durer : l'onglet a pu être fermé entre-temps
            attente = ui.notification(f"Installation de {ligne['nom']} (sortie dans la console du serveur)…",
                                      spinner=True, timeout=None)
            try:
                r = await run.io_bound(subprocess.run, ligne["commande"], shell=True, stdin=subprocess.DEVNULL)
            except OSError as e:
                r, erreur = None, e
            else:
                erreur = None
            if not page_encore_ouverte(client, dialogue):
                # onglet fermé ou page quittée : rien à afficher, mais la détection profite aux autres onglets
                ctx.etats = await run.io_bound(outils.detecter_tous, ctx.poste.outils)
                return
            attente.dismiss()
            message, genre = bilan_installation(ligne["nom"], r, erreur)
            ui.notify(message, type=genre, multi_line=erreur is not None)
            if erreur is not None:
                return
            await detecter()
        elif ligne["url"]:
            details = [ligne["url"]] + ([f"Dézipper dans un dossier durable, par exemple {ligne['dezipper']}"]
                                        if ligne["dezipper"] else [])
            if await formulaire.confirmer(f"Ouvrir la page de téléchargement de {ligne['nom']} ?", "Ouvrir", details):
                ui.navigate.to(ligne["url"], new_tab=True)

    @ui.refreshable
    def tableau():
        with ui.grid(columns="auto auto auto 1fr auto").classes("w-full items-center gap-x-4 gap-y-1"):
            for entete in ("Outil", "État", "Version", "Chemin", ""):
                ui.label(entete).classes("font-bold")
            for ligne in lignes_outils(ctx.etats):
                ui.label(ligne["nom"])
                ui.label(ligne["etat"]).classes("text-green-700" if ligne["present"] else "text-red-700")
                ui.label(ligne["version"])
                if ligne["present"]:
                    ui.label(ligne["chemin"]).classes("text-sm break-all")
                elif ligne["url"]:
                    ui.link(ligne["url"], ligne["url"], new_tab=True).classes("text-sm break-all")
                else:
                    ui.label("")
                if not ligne["present"] and (ligne["commande"] or ligne["url"]):
                    ui.button("Installer", on_click=lambda l=ligne: installer(l)).props("dense no-caps")
                else:
                    ui.label("")

    with corps:
        ui.label("Outils").classes("text-xl font-bold")
        tableau()
        ui.button("Détecter à nouveau", on_click=detecter).props("flat no-caps")
        ui.label("Dossiers des préréglages Lightroom (option « Stocker avec ce catalogue » décochée)").classes(
            "text-xl font-bold mt-4")
        with ui.grid(columns="auto auto 1fr").classes("w-full items-center gap-x-4 gap-y-1"):
            for libelle, chemin, existe in outils.dossiers_presets_lightroom():
                ui.label(libelle)
                ui.label("OK" if existe else "absent").classes("text-green-700" if existe else "text-gray-500")
                ui.label(str(chemin)).classes("text-sm break-all")
        ui.label("Si l'option est cochée, les préréglages sont dans « Paramètres Lightroom », à côté du catalogue. "
                 "Rien n'est copié : créer les préréglages comme le guide l'indique (0C).").classes(
            "text-sm text-gray-600")


def configuration(etat):
    """Page Configuration : chemins des quatre outils configurables, avec Parcourir ; Enregistrer écrit la
    configuration du poste (champ vide : détection automatique) puis relance la détection."""
    from nicegui import run, ui
    ctx = etat.ctx
    _, corps = _dialogue("Configuration — chemins des outils")
    elements = {}

    @ui.refreshable
    def statut(cle):
        ui.label(statut_outil(cle, ctx.poste.outils.get(cle), ctx.etats)).classes("text-xs text-gray-600 break-all")

    async def enregistrer():
        nouveaux = outils_modifies(ctx.poste.outils, {cle: el.value for cle, el in elements.items()})
        try:
            config.enregistrer_poste(replace(ctx.poste, outils=nouveaux))
        except OSError as e:
            ui.notify(f"Écriture impossible : {e}", type="negative", multi_line=True)
            return
        ctx.poste.outils = nouveaux         # la mémoire ne suit qu'une écriture réussie
        ctx.etats = await run.io_bound(outils.detecter_tous, ctx.poste.outils)
        statut.refresh()
        etat.rafraichir()
        ui.notify("Configuration du poste enregistrée ; outils détectés à nouveau", type="positive")

    with corps:
        for cle, libelle in lanceur.OUTILS_CONFIGURABLES:
            with ui.column().classes("w-full gap-0"):
                elements[cle], _ = _champ_chemin(libelle, ctx.poste.outils.get(cle, ""), GENRES_OUTILS[cle],
                                                 depart=lambda c=cle: _texte(elements[c].value),
                                                 placeholder="(détection automatique)")
                statut(cle)
        ui.button("Enregistrer", on_click=enregistrer).props("no-caps color=primary")
