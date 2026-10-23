"""Zone centrale de la page web : la tâche choisie (titre, formulaire ou geste), ses boutons Lancer, Mémoriser et
Arrêter, et le report dans panorama.json après une exécution.

Fonctions pures en haut (testées sans serveur), construction NiceGUI en bas. `apres_execution` tourne dans le fil
de lecture d'`execution` : elle ne touche jamais la page, seulement panorama.json et `Execution.lignes`.
"""

from pilotage import arguments as args_mod
from pilotage import catalogue, cheminement, config, lancer, outils

from . import aide, colonne, execution, formulaire, pages_poste, reglages

ACTION_MESSAGE = "Action propre au lanceur console : pas encore disponible dans la page (python panorama.py)."
MESSAGE_PERIME = "Le panorama courant a changé dans un autre onglet : rien n'est lancé ni mémorisé, la page est rechargée."
DEJA_EN_COURS = "Cette tâche tourne déjà"


# ---------------------------------------------------------------- fonctions pures

def raisons_indisponible(ctx, t):
    """Pourquoi la tâche ne peut pas être lancée (outil requis absent, PowerShell absent) ; [] si elle le peut."""
    noms = {o.cle: o.nom for o in outils.OUTILS}
    raisons = [f"{noms.get(cle, cle)} absent" for cle in t.outils if not lancer.present(ctx, cle)]
    if t.script.endswith(".ps1") and not lancer.powershell_disponible(ctx):
        raisons.append("PowerShell absent")
    return raisons


def ligne_report(cle, valeur):
    return f"→ panorama.json : {cle} = {valeur}"


def valeurs_lues(t, p):
    """[(libellé, chemin)] des clés de panorama.json que le geste `t` rappelle (`t.lit`), renseignées seulement."""
    resultat = []
    for libelle_lu, cle in t.lit.items():
        v = config.valeur(p, cle)
        if v:
            resultat.append((libelle_lu, v))
    return resultat


def cle_attendu(t):
    return next((cle for cle, source in t.reporte.items() if source == "attendu"), None)


def reporter_gestes(phase, p, taches=None, mettre_a_jour=config.mettre_a_jour):
    """Report des gestes de `phase` dont le fichier attendu existe ; retourne [(clé, valeur stockée)]."""
    changes = []
    for g in (catalogue.TACHES if taches is None else taches):
        if g.est_geste and g.phase == phase and g.attendu:
            v = reglages.reporter_geste(g, p, mettre_a_jour=mettre_a_jour)
            if v is not None:
                changes.append((cle_attendu(g), v))
    return changes


def enregistrer_cheminement(p, depart, serpentin, mettre_a_jour=config.mettre_a_jour):
    """Écrit le coin de départ et le serpentin dans panorama.json (et dans `p`, gardé en mémoire) ; retourne
    [(clé, valeur)]. ValueError, sans rien écrire, si `depart` n'est pas un des quatre coins."""
    depart = cheminement.verifier_depart(depart)
    serpentin = bool(serpentin)
    mettre_a_jour(p.T, depart=depart, serpentin=serpentin)
    p.depart, p.serpentin = depart, serpentin
    return [("depart", depart), ("serpentin", serpentin)]


def apres_execution(t, valeurs, p, ex, verrou=reglages.VERROU_PANORAMA, mettre_a_jour=config.mettre_a_jour, ctx=None):
    """Fin d'une exécution, dans le fil de lecture : message d'interruption, puis, si le code est 0, report des
    valeurs de la tâche et des gestes de sa phase dans panorama.json. Les lignes vont dans `ex.lignes`.

    `p` est le panorama du lancement ; si le panorama courant de `ctx` est le même $T sous un autre objet (on a
    changé de panorama puis on y est revenu pendant l'exécution), les valeurs reportées y sont recopiées aussi."""
    lignes = []
    if ex.etat == "interrompue":
        lignes.append("Interrompu.")
        if t.script in lancer.MESSAGES_INTERRUPTION:
            lignes.append(lancer.MESSAGES_INTERRUPTION[t.script])
    elif ex.code != 0:
        lignes.append(f"Échec (code {ex.code}).")
    elif p is not None:
        with verrou:
            changes = reglages.reporter_apres_execution(t, valeurs, p, mettre_a_jour=mettre_a_jour)
            changes += reporter_gestes(t.phase, p, mettre_a_jour=mettre_a_jour)
            courant = getattr(ctx, "panorama", None)
            if courant is not None and courant is not p and courant.T == p.T:
                for cle, v in changes:
                    setattr(courant, cle, v)
        lignes += [ligne_report(cle, v) for cle, v in changes]
    ex.lignes.extend(lignes)
    return lignes


def etat_execution(ex):
    """État lisible d'une exécution : « en cours », « terminée (code 0) », « échec (code 2) », « interrompue »."""
    if ex is None:
        return ""
    if ex.etat in ("terminée", "échec"):
        return f"{ex.etat} (code {ex.code})"
    return ex.etat


def formulaire_perime(etat, ctx):
    """Vrai si le panorama courant du poste n'est plus celui avec lequel l'onglet a rendu sa page : `ctx` est
    partagé par tous les onglets, un autre a pu changer de panorama entre-temps."""
    return etat.T_vu != ctx.poste.courant


# ---------------------------------------------------------------- partie NiceGUI

def construire(etat):
    """Pose la zone centrale dans `etat.centre` et ses boutons dans `etat.boutons`."""
    from nicegui import run, ui

    ctx = etat.ctx

    def valeurs_saisies():
        return formulaire.valeurs(etat.elements)

    def refuser_si_perime():
        """Vrai (et page rafraîchie) si un autre onglet a changé de panorama depuis l'affichage du formulaire."""
        if not formulaire_perime(etat, ctx):
            return False
        ui.notify(MESSAGE_PERIME, type="warning", multi_line=True)
        etat.rafraichir()
        return True

    def refuser_si_en_cours(t):
        ex = execution.derniere(t.identifiant)
        if ex is not None and ex.etat == "en cours":
            ui.notify(DEJA_EN_COURS, type="warning")
            return True
        return False

    async def lancer_tache():
        if refuser_si_perime():
            return
        t, p = etat.tache, ctx.panorama
        if refuser_si_en_cours(t):
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
            if ecarts and not await formulaire.confirmer(
                    "Les constantes du script contredisent le panorama courant :", "Lancer quand même",
                    [f"{nom} = {vs} dans le script, {vp} dans le panorama" for nom, vs, vp in ecarts]):
                return
            if refuser_si_perime() or refuser_si_en_cours(t):   # pendant la confirmation : autre panorama, ou
                return                                          # la même tâche lancée depuis un autre onglet
        try:
            nouvelle = execution.demarrer(t.identifiant, formulaire.commande(t, ctx, valeurs), cwd=str(ctx.scripts),
                                          env=lancer.environnement_enfant(),
                                          sur_fin=lambda fin: apres_execution(t, valeurs, p, fin, ctx=ctx))
        except execution.DejaEnCours:
            ui.notify(DEJA_EN_COURS, type="warning")
            return
        except (RuntimeError, OSError, LookupError) as e:   # LookupError : outil d'une action absent (cpclean sans Hugin)
            ui.notify(f"Lancement impossible : {e}", type="negative")
            return
        etat.lancees.append(nouvelle)
        ui.notify(f"Lancé : {t.identifiant}")
        etat.suivi()
        etat.en_tete.refresh()

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
        try:
            with reglages.VERROU_PANORAMA:
                ecrit = reglages.memoriser(p, etat.tache.identifiant, etat.arguments, valeurs_saisies())
        except OSError as e:
            ui.notify(f"Écriture impossible : {e}", type="negative", multi_line=True)
            return
        ui.notify("Mémorisé dans panorama.json : " + (", ".join(ecrit) or "aucune valeur propre au script"))

    @ui.refreshable
    def boutons():
        t = etat.tache
        ex = execution.derniere(t.identifiant)
        with ui.row().classes("items-center gap-2"):
            raisons = raisons_indisponible(ctx, t)
            if raisons:
                ui.label("Lancement impossible : " + ", ".join(raisons)).classes("text-red-700")
                ui.button("⚙ Configuration", on_click=lambda: pages_poste.configuration(etat)).props("flat no-caps")
            else:
                ui.button("▶ Lancer", on_click=lancer_tache).props("no-caps color=primary")
            ui.button("Mémoriser ces réglages pour ce panorama", on_click=memoriser).props("outline no-caps")
            if ex is not None and ex.etat == "en cours":
                ui.button("■ Arrêter", on_click=arreter_tache).props("no-caps color=negative")
            if ex is not None:
                ui.label(etat_execution(ex)).classes("text-sm text-gray-600")

    def zone_geste(t):
        ui.label(t.geste).classes("text-xl")
        for libelle_lu, valeur_lue in valeurs_lues(t, ctx.panorama):
            ui.label(f"{libelle_lu} : {valeur_lue}").classes("text-sm")
        if not t.attendu:
            return
        p = ctx.panorama
        if p is not None:
            try:
                with reglages.VERROU_PANORAMA:
                    v = reglages.reporter_geste(t, p)
            except OSError as e:
                v = None
                ui.label(f"Report impossible : {e}").classes("text-red-700")
            if v is not None:
                etat.journal.push(ligne_report(cle_attendu(t), v))
                etat.en_tete.refresh()
        existe, chemin = reglages.etat_geste(t, p)
        ui.label(f"Fichier attendu : {t.attendu}").classes("text-sm text-gray-600")
        if existe:
            ui.label(f"✓ présent : {chemin}").classes("text-green-700")
        else:
            ui.label("en attente" + (f" : {chemin}" if chemin else " (aucun panorama courant)")).classes("text-amber-700")

    def zone_cheminement(t):
        """1B : quatre coins (flèche vers le centre = sens de la prise de vue), serpentin, tracé 3 x 5, enregistrement."""
        p = ctx.panorama
        ui.label(t.sous_titre).classes("text-xl")
        if p is None:
            ui.label("Aucun panorama courant : le sélecteur s'essaie, mais rien ne peut être enregistré "
                     "(Phase 0, nouveau panorama).").classes("text-amber-700")
        choix = {"depart": p.depart if p and p.depart in cheminement.COINS else cheminement.DEFAUT,
                 "serpentin": bool(p.serpentin) if p else False}

        def enregistrer():
            if p is None or refuser_si_perime():
                return
            try:
                with reglages.VERROU_PANORAMA:
                    changes = enregistrer_cheminement(p, choix["depart"], choix["serpentin"])
            except (OSError, ValueError) as e:
                ui.notify(f"Écriture impossible : {e}", type="negative", multi_line=True)
                return
            for cle, v in changes:
                etat.journal.push(ligne_report(cle, v))
            ui.notify("Enregistré dans panorama.json")
            etat.en_tete.refresh()

        def choisir(coin):
            choix["depart"] = coin
            plan.refresh()

        def basculer(e):
            choix["serpentin"] = bool(e.value)
            plan.refresh()

        @ui.refreshable
        def plan():
            with ui.element("div").style("display:grid;grid-template-columns:auto minmax(0,26rem) auto;"
                                         "align-items:center;gap:0.5rem;width:max-content;max-width:100%"):
                for coin in ("hg", None, "hd"):
                    _bouton_coin(coin)
                ui.element("div")
                ui.html(cheminement.dessin_svg(choix["depart"], choix["serpentin"]), sanitize=False)
                ui.element("div")
                for coin in ("bg", None, "bd"):
                    _bouton_coin(coin)
            ui.label(cheminement.resume(choix["depart"], choix["serpentin"])).classes("text-sm")

        def _bouton_coin(coin):
            if coin is None:
                ui.element("div")
                return
            actif = choix["depart"] == coin
            b = ui.button(cheminement.FLECHES_COINS[coin], on_click=lambda c=coin: choisir(c))
            b.props("round " + ("color=primary" if actif else "outline color=grey-7"))
            b.tooltip(f"Départ {cheminement.NOMS_COINS[coin]}")

        ui.label("Cliquer un coin : la flèche indique le sens de la prise de vue. Toujours en lignes, jamais en "
                 "colonnes. Le dessin montre 3 lignes x 5 colonnes, quelle que soit la grille réelle.").classes(
            "text-sm text-gray-600")
        plan()
        ui.switch("Serpentin (sens inversé à chaque ligne)", value=choix["serpentin"], on_change=basculer)
        with ui.row().classes("items-center gap-2"):
            ui.button("Enregistrer dans panorama.json", on_click=enregistrer).props(
                "no-caps color=primary" + (" disable" if p is None else ""))
        ui.label(f"✎ Écrit dans {t.effet}").classes("text-sm text-amber-800")

    def zone_script(t):
        p = ctx.panorama
        try:
            arguments, ecrit, _ = formulaire.arguments_de(t, ctx)
            liste = formulaire.champs(t, arguments, p, ctx)
            constantes = lancer.constantes_du_fichier(ctx.scripts / t.script) if t.script.endswith(".py") else {}
        except (OSError, KeyError, ValueError, SyntaxError, AttributeError, TypeError) as e:
            ui.label(f"Formulaire impossible : {e}").classes("text-red-700")      # dont un panorama.json abîmé
            return
        etat.arguments, etat.champs = arguments, liste
        with ui.card().classes("w-full"):
            etat.elements = formulaire.rendre(liste, sans_note=formulaire.arguments_d_outil(arguments))
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
        if t is None:
            ui.label("Choisissez une tâche dans la colonne de gauche.").classes("text-gray-600")
            return
        ui.label(colonne.titre(t)).classes("text-2xl font-bold")
        with ui.row().classes("items-center gap-1 text-sm text-gray-600"):
            programme = f"Script {t.script}" if t.script else (t.sous_titre if formulaire.a_un_formulaire(t) else "")
            if programme:
                ui.label(programme)
            if t.repere:
                if programme:
                    ui.label("·")
                ui.link(f"§ {t.repere} du guide", aide.lien_guide(t.repere), new_tab=True)
        journal = ui.log(max_lines=5000).classes("w-full h-64")    # posé tôt (un geste y écrit), déplacé après
        etat.journal = journal
        if t.est_geste:
            zone_geste(t)
        elif t.action == "cheminement":
            zone_cheminement(t)
        elif formulaire.a_un_formulaire(t):
            zone_script(t)
        else:
            ui.label(ACTION_MESSAGE).classes("text-gray-600")
        journal.move(target_index=-1)
        if t.script:
            etat.apercus()
        etat.ex_vue, etat.lus, etat.etat_vu = None, 0, ""    # journal neuf : le rejouer en entier
        etat.suivi()

    etat.centre, etat.boutons = centre, boutons
    return centre
