"""La page du lanceur web (disposition A) : en-tête, colonne des phases, formulaire, console, aperçus, aide.

Façade NiceGUI sur les modules purs de pilotage/ et interface/. En haut du module, des fonctions pures (modèle
de la colonne, titres, état des outils, dossier des aperçus, report après exécution), testées sans serveur ; en
bas, la construction de la page, une par onglet ouvert (`construire`).

Fils d'exécution : un script lancé est lu par un fil de `execution`. Ce fil ne touche jamais la page : la sortie
s'accumule dans `Execution.lignes`, le report automatique (`apres_execution`) n'écrit que panorama.json et ajoute
ses lignes à cette même liste. Chaque onglet relit le tout depuis un `ui.timer` de 0,5 s, dans son propre contexte :
fermer l'onglet ne perd rien, le rouvrir retrouve le journal.
"""

import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pilotage import arguments as args_mod
from pilotage import catalogue, config, lancer, outils
from pilotage.catalogue import Tache

from . import aide, apercus, execution, formulaire, reglages

TITRE_MESURES = "Mesures et inspection"
PHASE0_ENTREE = "Outils, préréglages, nouveau panorama"
PHASE0_MESSAGE = "Disponible dans la page Phase 0 (tâche suivante)."
ACTION_MESSAGE = "Action propre au lanceur console : pas encore disponible dans la page (python panorama.py)."
VIPS_ABSENT = "libvips absent : voir Configuration"
LIMITE_IMAGES = 200
MESSAGE_PERIME = "Le panorama courant a changé dans un autre onglet : rien n'est lancé ni mémorisé, la page est rechargée."
MESSAGE_CHANGE = "Le panorama courant a changé dans un autre onglet : page rechargée."
DELAI_SORTIE_FORCEE = 10              # secondes entre « Quitter » et la sortie forcée du processus

VERROU_PANORAMA = threading.Lock()     # report depuis le fil de lecture, mémorisation et changement de panorama

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
        titre = TITRE_MESURES if phase == "mesures" else titres.get(phase, f"Phase {phase}")
        resultat.append((titre, list(groupes.get(phase, []))))
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


def raisons_indisponible(ctx, t):
    """Pourquoi la tâche ne peut pas être lancée (outil requis absent, PowerShell absent) ; [] si elle le peut."""
    noms = {o.cle: o.nom for o in outils.OUTILS}
    raisons = [f"{noms.get(cle, cle)} absent" for cle in t.outils if not lancer.present(ctx, cle)]
    if t.script.endswith(".ps1") and not lancer.powershell_disponible(ctx):
        raisons.append("PowerShell absent")
    return raisons


def dossier_sortie(t, liste_champs, valeurs, exclus=()):
    """Dossier montré par « Fichiers produits » : l'argument `t.sortie` s'il est renseigné, sinon le dossier du
    premier champ fichier ou dossier renseigné hors `exclus` (les chemins d'outils) ; "" faute de mieux."""
    def dossier(chemin, genre):
        if genre == "dossier" or os.path.isdir(chemin):
            return chemin
        return os.path.dirname(chemin)
    genres = {c.arg.nom: c.genre for c in liste_champs}
    if t.sortie and valeurs.get(t.sortie):
        return dossier(str(valeurs[t.sortie]), genres.get(t.sortie, "dossier"))
    for c in liste_champs:
        v = valeurs.get(c.arg.nom)
        if c.genre in ("fichier", "dossier") and c.arg.nom not in exclus and isinstance(v, str) and v:
            return dossier(v, c.genre)
    return ""


def chemin_vips(ctx):
    """vips.exe configuré sur le poste, sinon détecté ; None s'il manque."""
    configure = ctx.poste.outils.get("vips")
    if configure:
        return configure
    e = lancer.etat(ctx, "vips")
    return e.chemin if e and e.present else None


def liens_absolus(markdown):
    """Les liens internes du guide (« (#ancre) ») deviennent des liens vers le guide sur GitHub."""
    return markdown.replace("](#", "](" + aide.URL_GUIDE + "#")


def ligne_report(cle, valeur):
    return f"→ panorama.json : {cle} = {valeur}"


def cle_attendu(t):
    return next((cle for cle, source in t.reporte.items() if source == "attendu"), None)


def reporter_gestes(phase, p, taches=None, enregistrer=config.enregistrer_panorama):
    """Report des gestes de `phase` dont le fichier attendu existe ; retourne les lignes à afficher."""
    lignes = []
    for g in (catalogue.TACHES if taches is None else taches):
        if g.est_geste and g.phase == phase and g.attendu:
            v = reglages.reporter_geste(g, p, enregistrer=enregistrer)
            if v is not None:
                lignes.append(ligne_report(cle_attendu(g), v))
    return lignes


def apres_execution(t, valeurs, p, ex, verrou=VERROU_PANORAMA, enregistrer=config.enregistrer_panorama):
    """Fin d'une exécution, dans le fil de lecture : message d'interruption, puis, si le code est 0, report des
    valeurs de la tâche et des gestes de sa phase dans panorama.json. Les lignes vont dans `ex.lignes`."""
    lignes = []
    if ex.etat == "interrompue":
        lignes.append("Interrompu.")
        if t.script in lancer.MESSAGES_INTERRUPTION:
            lignes.append(lancer.MESSAGES_INTERRUPTION[t.script])
    elif ex.code != 0:
        lignes.append(f"Échec (code {ex.code}).")
    elif p is not None:
        with verrou:
            changes = reglages.reporter_apres_execution(t, valeurs, p, enregistrer=enregistrer)
            lignes += [ligne_report(cle, v) for cle, v in changes]
            lignes += reporter_gestes(t.phase, p, enregistrer=enregistrer)
    ex.lignes.extend(lignes)
    return lignes


def etat_execution(ex):
    """État lisible d'une exécution : « en cours », « terminée (code 0) », « échec (code 2) », « interrompue »."""
    if ex is None:
        return ""
    if ex.etat in ("terminée", "échec"):
        return f"{ex.etat} (code {ex.code})"
    return ex.etat


def taille_lisible(octets):
    for unite in ("o", "Ko", "Mo", "Go"):
        if octets < 1024 or unite == "Go":
            return f"{octets:.0f} {unite}" if unite == "o" else f"{octets:.1f} {unite}"
        octets /= 1024


def changer_panorama(ctx, T, enregistrer=config.enregistrer_poste):
    """Rend `T` courant sur le poste, l'enregistre et recharge le panorama ; retourne le panorama (None si illisible)."""
    with VERROU_PANORAMA:
        ctx.poste.courant = T
        enregistrer(ctx.poste)
        ctx.panorama = config.panorama_courant(ctx.poste)
    return ctx.panorama


def formulaire_perime(etat, ctx):
    """Vrai si le panorama courant du poste n'est plus celui avec lequel l'onglet a rendu sa page : `ctx` est
    partagé par tous les onglets, un autre a pu changer de panorama entre-temps."""
    return etat.T_vu != ctx.poste.courant


def options_panoramas(poste):
    """{$T: libellé} des panoramas connus du poste, le courant compris même s'il n'est pas dans la liste."""
    connus = list(poste.panoramas)
    if poste.courant and poste.courant not in connus:
        connus.append(poste.courant)
    noms = [Path(T).name or T for T in connus]
    return {T: (nom if noms.count(nom) == 1 else T) for T, nom in zip(connus, noms)}


def arguments_d_outil(arguments):
    """Noms des arguments qui désignent un outil du poste (config « outil:… ») : ni note « hors du panorama »,
    ni candidats au dossier des fichiers produits."""
    return {a.nom for a in arguments if a.config and a.config.startswith("outil:")}


# ---------------------------------------------------------------- la page

@dataclass
class Etat:
    """État d'un onglet : la tâche affichée, ses champs, le journal et les zones rafraîchissables."""
    ctx: lancer.Contexte
    tache: Optional[Tache] = None
    vue: str = "accueil"                    # « accueil », « tache » ou « phase0 »
    elements: dict = field(default_factory=dict)
    champs: list = field(default_factory=list)
    arguments: list = field(default_factory=list)   # déclaration brute (sans préremplissage des outils)
    journal: object = None
    ex_vue: object = None                   # exécution suivie dans le journal
    lus: int = 0                            # lignes de ex_vue déjà poussées
    etat_vu: str = ""
    lancees: list = field(default_factory=list)     # exécutions lancées depuis cet onglet, pas encore notifiées
    compteur: int = -1
    dossier_apercus: Optional[str] = None   # dossier choisi à la main (sinon : celui du formulaire)
    ouvertes: set = field(default_factory=set)      # phases dépliées dans la colonne
    T_vu: Optional[str] = None              # $T courant au dernier rendu de la zone centrale
    en_tete: object = None
    colonne: object = None
    centre: object = None
    aide: object = None
    apercus: object = None
    boutons: object = None


def _a_venir(nom):
    from nicegui import ui
    ui.notify(f"{nom} : à venir (tâche suivante)")


async def _confirmer(message, oui, details=()):
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


def construire(ctx):
    """Construit la page d'un onglet."""
    from nicegui import app, run, ui

    etat = Etat(ctx=ctx)
    arbre = arborescence()
    ui.add_head_html('<base target="_blank">')     # les liens du guide s'ouvrent à côté de la page

    # ------------------------------------------------------------ en-tête

    async def quitter():
        cours = execution.en_cours()
        if cours and not await _confirmer("Des tâches tournent encore : elles seront arrêtées.", "Arrêter et quitter",
                                          [ex.identifiant for ex in cours]):
            return
        for ex in cours:
            await run.io_bound(execution.arreter, ex)
        ui.notify("Serveur arrêté : vous pouvez fermer l'onglet.")
        app.shutdown()
        # filet : une fois, le serveur a cessé d'écouter sans que le processus se termine (non reproduit) ;
        # les scripts lancés sont déjà arrêtés, rien n'est perdu à forcer la sortie quelques secondes plus tard
        filet = threading.Timer(DELAI_SORTIE_FORCEE, os._exit, (0,))
        filet.daemon = True
        filet.start()

    def choisir_panorama(e):
        if not e.value or e.value == ctx.poste.courant:
            return
        if changer_panorama(ctx, e.value) is None:
            ui.notify(f"panorama.json illisible dans {e.value}", type="warning")
        etat.dossier_apercus = None
        tout_rafraichir()

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
        for nom in ("Panorama", "Nouveau panorama", "Phase 0"):
            ui.button(nom, on_click=lambda n=nom: _a_venir(n)).props("flat dense no-caps color=white")
        ui.button("⚙ Configuration", on_click=lambda: _a_venir("Configuration")).props("flat dense no-caps color=white")
        ui.button("Aide", on_click=lambda: volet.toggle()).props("flat dense no-caps color=white")
        ui.button("Quitter", on_click=quitter).props("dense no-caps color=negative")

    # ------------------------------------------------------------ colonne

    def ouvrir(t, vue="tache"):
        etat.tache, etat.vue = t, vue
        etat.dossier_apercus = None
        etat.ex_vue, etat.lus, etat.etat_vu = None, 0, ""
        colonne.refresh()
        centre.refresh()
        volet_aide.refresh()

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
                        ui.item(PHASE0_ENTREE, on_click=lambda: ouvrir(None, "phase0")).classes(
                            "bg-blue-100" if etat.vue == "phase0" else "")
                    for t in taches:
                        item = ui.item(libelle(t), on_click=lambda t=t: ouvrir(t))
                        if t.est_geste:
                            item.classes("italic text-gray-500")
                        if etat.tache is t:
                            item.classes("bg-blue-100")

    # ------------------------------------------------------------ zone centrale

    def valeurs_saisies():
        return formulaire.valeurs(etat.elements)

    def refuser_si_perime():
        """Vrai (et page rafraîchie) si un autre onglet a changé de panorama depuis l'affichage du formulaire."""
        if not formulaire_perime(etat, ctx):
            return False
        ui.notify(MESSAGE_PERIME, type="warning", multi_line=True)
        tout_rafraichir()
        return True

    async def lancer_tache():
        if refuser_si_perime():
            return
        t, p = etat.tache, ctx.panorama
        ex = execution.derniere(t.identifiant)
        if ex is not None and ex.etat == "en cours":
            ui.notify("Cette tâche tourne déjà", type="warning")
            return
        valeurs = valeurs_saisies()
        erreurs = args_mod.verifier(etat.arguments, {a.nom: valeurs.get(a.nom, "") for a in etat.arguments})
        if erreurs:
            for m in erreurs:
                ui.notify(m, type="negative", multi_line=True)
            return
        if t.script.endswith(".py"):
            constantes = lancer.constantes_du_fichier(ctx.scripts / t.script)
            ecarts = args_mod.ecarts(constantes, p)
            if ecarts and not await _confirmer(
                    "Les constantes du script contredisent le panorama courant :", "Lancer quand même",
                    [f"{nom} = {vs} dans le script, {vp} dans le panorama" for nom, vs, vp in ecarts]):
                return
            if refuser_si_perime():         # le panorama a pu changer pendant la confirmation
                return
        try:
            nouvelle = execution.demarrer(t.identifiant, formulaire.commande(t, ctx, valeurs), cwd=str(ctx.scripts),
                                          env=lancer.environnement_enfant(),
                                          sur_fin=lambda fin: apres_execution(t, valeurs, p, fin))
        except OSError as e:
            ui.notify(f"Lancement impossible : {e}", type="negative")
            return
        etat.lancees.append(nouvelle)
        ui.notify(f"Lancé : {t.identifiant}")
        rafraichir_suivi()
        en_tete.refresh()

    async def arreter_tache():
        ex = execution.derniere(etat.tache.identifiant)
        if ex is not None and ex.etat == "en cours":
            await run.io_bound(execution.arreter, ex)

    def memoriser():
        if refuser_si_perime():
            return
        p = ctx.panorama
        if p is None:
            ui.notify("Aucun panorama courant : rien à mémoriser", type="warning")
            return
        with VERROU_PANORAMA:
            ecrit = reglages.memoriser(p, etat.tache.identifiant, etat.arguments, valeurs_saisies())
        ui.notify("Mémorisé dans panorama.json : " + (", ".join(ecrit) or "aucune valeur propre au script"))

    @ui.refreshable
    def boutons():
        t = etat.tache
        ex = execution.derniere(t.identifiant)
        with ui.row().classes("items-center gap-2"):
            raisons = raisons_indisponible(ctx, t)
            if raisons:
                ui.label("Lancement impossible : " + ", ".join(raisons)).classes("text-red-700")
                ui.button("⚙ Configuration", on_click=lambda: _a_venir("Configuration")).props("flat no-caps")
            else:
                ui.button("▶ Lancer", on_click=lancer_tache).props("no-caps color=primary")
            ui.button("Mémoriser ces réglages pour ce panorama", on_click=memoriser).props("outline no-caps")
            if ex is not None and ex.etat == "en cours":
                ui.button("■ Arrêter", on_click=arreter_tache).props("no-caps color=negative")
            if ex is not None:
                ui.label(etat_execution(ex)).classes("text-sm text-gray-600")

    def zone_geste(t):
        ui.label(t.geste).classes("text-xl")
        if not t.attendu:
            return
        p = ctx.panorama
        if p is not None:
            with VERROU_PANORAMA:
                v = reglages.reporter_geste(t, p)
            if v is not None:
                etat.journal.push(ligne_report(cle_attendu(t), v))
                en_tete.refresh()
        existe, chemin = reglages.etat_geste(t, p)
        ui.label(f"Fichier attendu : {t.attendu}").classes("text-sm text-gray-600")
        if existe:
            ui.label(f"✓ présent : {chemin}").classes("text-green-700")
        else:
            ui.label("en attente" + (f" : {chemin}" if chemin else " (aucun panorama courant)")).classes("text-amber-700")

    def zone_script(t):
        p = ctx.panorama
        try:
            arguments, ecrit, _ = formulaire.arguments_de(t, ctx)
            liste = formulaire.champs(t, arguments, p, ctx)
            constantes = lancer.constantes_du_fichier(ctx.scripts / t.script) if t.script.endswith(".py") else {}
        except (OSError, KeyError, ValueError, SyntaxError) as e:
            ui.label(f"Formulaire impossible : {e}").classes("text-red-700")
            return
        etat.arguments, etat.champs = arguments, liste
        with ui.card().classes("w-full"):
            etat.elements = formulaire.rendre(liste, sans_note=arguments_d_outil(arguments))
        ecrit = ecrit or t.effet
        ui.label(f"✎ Écrit dans {ecrit}" if ecrit else "lecture seule").classes(
            "text-sm " + ("text-amber-800" if ecrit else "text-gray-600"))
        for nom, vs, vp in args_mod.ecarts(constantes, p):
            ui.label(f"⚠ {nom} = {vs} dans le script, {vp} dans le panorama").classes("text-amber-700")
        boutons()

    @ui.refreshable
    def centre():
        t = etat.tache
        etat.elements, etat.champs, etat.arguments = {}, [], []
        etat.T_vu = ctx.poste.courant
        if etat.vue == "phase0":
            ui.label(arbre[0][0]).classes("text-xl font-bold")
            ui.label(PHASE0_MESSAGE)
            return
        if t is None:
            ui.label("Choisissez une tâche dans la colonne de gauche.").classes("text-gray-600")
            return
        ui.label(titre(t)).classes("text-2xl font-bold")
        with ui.row().classes("items-center gap-1 text-sm text-gray-600"):
            if t.script:
                ui.label(f"Script {t.script}")
            if t.repere:
                if t.script:
                    ui.label("·")
                ui.link(f"§ {t.repere} du guide", aide.lien_guide(t.repere), new_tab=True)
        journal = ui.log(max_lines=5000).classes("w-full h-64")    # posé tôt (un geste y écrit), déplacé après
        etat.journal = journal
        if t.est_geste:
            zone_geste(t)
        elif t.script:
            zone_script(t)
        else:
            ui.label(ACTION_MESSAGE).classes("text-gray-600")
        journal.move(target_index=-1)
        if t.script:
            apercus_zone()
        etat.ex_vue, etat.lus, etat.etat_vu = None, 0, ""    # journal neuf : le rejouer en entier
        rafraichir_suivi()

    # ------------------------------------------------------------ fichiers produits

    def choisir_dossier(v):
        etat.dossier_apercus = v or None
        apercus_zone.refresh()

    async def autre_dossier(depart):
        choisi = await formulaire.parcourir("dossier", depart)
        if choisi:
            choisir_dossier(choisi)

    def vider():
        n = apercus.vider_cache()
        ui.notify(f"{n} aperçu(s) supprimé(s) du cache")

    async def voir(image):
        vips = chemin_vips(ctx)
        if not vips:
            ui.notify(VIPS_ABSENT, type="warning")
            return
        attente = ui.notification(f"Aperçu de {image.chemin.name}…", spinner=True, timeout=None)
        try:
            jpeg = await run.io_bound(apercus.apercu, image.chemin, vips)
        except (RuntimeError, OSError) as e:
            ui.notify(f"Aperçu impossible : {e}", type="negative", multi_line=True)
            return
        finally:
            attente.dismiss()
        visionneuse(image.chemin.name, jpeg)

    @ui.refreshable
    def apercus_zone():
        t = etat.tache
        calcule = (dossier_sortie(t, etat.champs, valeurs_saisies(), arguments_d_outil(etat.arguments))
                   if etat.elements else "")
        dossier = etat.dossier_apercus or calcule
        with ui.card().classes("w-full"):
            ui.label("Fichiers produits").classes("font-bold")
            with ui.row().classes("w-full items-center no-wrap gap-2"):
                saisie = ui.input("Dossier", value=dossier).classes("grow")
                saisie.on("keydown.enter", lambda: choisir_dossier(saisie.value))
                ui.button("Autre dossier…", on_click=lambda: autre_dossier(saisie.value)).props("flat no-caps")
                ui.button("Actualiser", on_click=lambda: choisir_dossier(saisie.value)).props("flat no-caps")
                ui.button("Vider le cache", on_click=vider).props("flat no-caps")
            if not chemin_vips(ctx):
                ui.label(VIPS_ABSENT).classes("text-amber-700")
            images = apercus.lister_images(dossier)
            if not dossier:
                ui.label("Aucun dossier de sortie renseigné.").classes("text-gray-600")
            elif not images:
                ui.label("Aucune image (.tif, .jpg, .png) dans ce dossier.").classes("text-gray-600")
            with ui.list().props("dense separator").classes("w-full"):
                for image in images[:LIMITE_IMAGES]:
                    with ui.item(on_click=lambda i=image: voir(i)):
                        with ui.item_section():
                            ui.item_label(image.chemin.name)
                        with ui.item_section().props("side"):
                            ui.item_label(f"{taille_lisible(image.taille)} · "
                                          f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(image.modifie))}")
            if len(images) > LIMITE_IMAGES:
                ui.label(f"… et {len(images) - LIMITE_IMAGES} autres").classes("text-gray-600")

    def visionneuse(nom, jpeg):
        """Aperçu en grand ; clic : zoom ×2 centré sur le point, Maj+clic : dézoom ; défilement pour se déplacer."""
        zoom = {"niveau": 1, "largeur": 1, "hauteur": 1}
        with ui.dialog().props("maximized") as dialogue, ui.card().classes("w-full h-full p-2"):
            with ui.row().classes("w-full items-center gap-2"):
                ui.label(nom).classes("font-bold")
                ui.space()
                ui.button("−", on_click=lambda: zoomer(zoom["niveau"] / 2)).props("flat")
                ui.button("+", on_click=lambda: zoomer(zoom["niveau"] * 2)).props("flat")
                ui.button("Ajuster", on_click=lambda: zoomer(1)).props("flat no-caps")
                ui.button("Fermer", on_click=dialogue.close).props("flat no-caps")
            with ui.element("div").classes("w-full grow overflow-auto") as cadre:
                image = ui.interactive_image(jpeg, events=["click"]).style("width: 100%")

        def zoomer(niveau, fx=0.5, fy=0.5):
            zoom["niveau"] = min(max(niveau, 1), 16)
            image.style(f"width: {zoom['niveau'] * 100}%")
            ui.run_javascript(
                f"setTimeout(() => {{ const c = document.getElementById('c{cadre.id}');"
                f" c.scrollLeft = {fx} * c.scrollWidth - c.clientWidth / 2;"
                f" c.scrollTop = {fy} * c.scrollHeight - c.clientHeight / 2; }}, 50)")

        def taille(e):
            zoom["largeur"], zoom["hauteur"] = e.args.get("width") or 1, e.args.get("height") or 1

        def clic(e):
            facteur = 0.5 if e.shift else 2
            zoomer(zoom["niveau"] * facteur, e.image_x / zoom["largeur"], e.image_y / zoom["hauteur"])

        image.on("loaded", taille)
        image.on_mouse(clic)
        dialogue.on("hide", dialogue.delete)
        dialogue.open()

    # ------------------------------------------------------------ volet d'aide

    @ui.refreshable
    def volet_aide():
        t = etat.tache
        if t is None:
            ui.label("L'aide de la tâche choisie s'affiche ici.").classes("text-gray-600")
            ui.link("Le guide", aide.URL_GUIDE, new_tab=True)
            return
        section = aide.section_du_guide(t.repere) if t.repere else None
        if section:
            ui.markdown(liens_absolus(section), extras=["fenced-code-blocks", "tables", "code-friendly"]).classes(
                "text-sm w-full [&_h3]:text-lg [&_h4]:text-base [&_pre]:whitespace-pre-wrap [&_pre]:break-all "
                "[&_table]:block [&_table]:overflow-x-auto")
        else:
            ui.label("Section introuvable dans le guide.").classes("text-gray-600")
            ui.link("Ouvrir le guide", aide.lien_guide(t.repere) if t.repere else aide.URL_GUIDE, new_tab=True)
        if t.script:
            mode = aide.mode_d_emploi(ctx.scripts / t.script)
            with ui.expansion("Mode d'emploi du script").classes("w-full"):
                ui.html(f"<pre class='text-xs whitespace-pre-wrap'>{_echapper(mode)}</pre>", sanitize=False)

    # ------------------------------------------------------------ suivi des exécutions

    def rafraichir_suivi():
        """Rebranche le journal sur la dernière exécution de la tâche affichée, et pousse ce qui manque."""
        t, journal = etat.tache, etat.journal
        if journal is None or t is None or not t.script:
            return
        ex = execution.derniere(t.identifiant)
        if ex is not etat.ex_vue:
            journal.clear()
            etat.ex_vue, etat.lus, etat.etat_vu = ex, 0, ""
        if ex is None:
            return
        nouvelles = ex.lignes[etat.lus:]
        for ligne in nouvelles:
            journal.push(ligne)
        etat.lus += len(nouvelles)
        if ex.etat != etat.etat_vu:
            etat.etat_vu = ex.etat
            boutons.refresh()

    def tic():
        if formulaire_perime(etat, ctx):
            ui.notify(MESSAGE_CHANGE, multi_line=True)
            tout_rafraichir()
        rafraichir_suivi()
        n = len(execution.en_cours())
        changement = n != etat.compteur
        etat.compteur = n
        for ex in [ex for ex in etat.lancees if ex.fini.is_set()]:
            etat.lancees.remove(ex)
            ui.notify(f"{ex.identifiant} : {etat_execution(ex)}",
                      type="positive" if ex.code == 0 else "warning")
            changement = True
            if etat.tache is not None and etat.tache.script:
                apercus_zone.refresh()
            elif etat.tache is not None and etat.tache.est_geste:
                centre.refresh()
        if changement:
            en_tete.refresh()

    def tout_rafraichir():
        en_tete.refresh()
        colonne.refresh()
        centre.refresh()
        volet_aide.refresh()

    # ------------------------------------------------------------ disposition

    etat.en_tete, etat.colonne, etat.centre, etat.aide, etat.apercus, etat.boutons = (
        en_tete, colonne, centre, volet_aide, apercus_zone, boutons)
    with ui.header().classes("items-center gap-4 bg-slate-800 text-white"):
        en_tete()
    with ui.left_drawer(value=True).props("width=300 bordered").classes("p-0"):
        colonne()
    with ui.right_drawer(value=True).props("width=440 bordered") as volet:
        volet_aide()
    with ui.column().classes("w-full max-w-5xl gap-3"):
        centre()
    ui.timer(0.5, tic)
    return etat


def _echapper(texte):
    return texte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def application(ctx):
    """Fonction racine passée à ui.run : une page par onglet, sur le même contexte."""
    def racine():
        construire(ctx)
    return racine


def demarrer(ctx, port, ouvrir=True):
    """Démarre le serveur sur 127.0.0.1:`port` ; ouvre le navigateur si `ouvrir`. Bloque jusqu'à l'arrêt."""
    from nicegui import ui
    ui.run(application(ctx), host="127.0.0.1", port=port, title="giga-pano-hdr", reload=False, show=ouvrir,
           favicon="🌐")
