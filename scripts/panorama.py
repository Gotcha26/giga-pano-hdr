"""Lanceur de la chaîne d'assemblage : aiguille vers le bon script selon la phase du guide.

CONTEXTE
    Point d'entrée unique (python panorama.py). Le menu principal suit les phases du guide ; chaque sous-menu
    liste des tâches, nomme le script appelé et déclare ce qu'il écrit et où. Les gestes dans Hugin ou
    Lightroom apparaissent grisés avec leur rappel. Choisir une tâche ouvre le menu de pilotage du script,
    prérempli d'après le panorama courant, puis le lance dans cette console.

MODE OPÉRATOIRE
    1. lit la configuration du poste (%LOCALAPPDATA%\\giga-pano-hdr\\config.json) et le panorama courant
       ($T\\panorama.json) ;
    2. détecte les outils (Hugin, multiblend, libvips, ExifTool, Python, Pillow, PowerShell) ;
    3. affiche le menu principal ; 0 quitte.

ENTRÉES
    Aucune : tout se fait dans les menus. Phase 0 : versions des outils, installation de ce qui manque,
    dossiers des préréglages Lightroom, création d'un nouveau panorama, changement de panorama courant.

SORTIES
    Celles des scripts lancés. Le lanceur n'écrit que la configuration (menus Configuration et Nouveau
    panorama) : $T\\panorama.json et config.json du poste.

EXEMPLE
    python panorama.py
"""

import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pilotage import arguments, catalogue, config, declarations_ps, lancer, menu, outils  # noqa: E402
from pilotage import cheminement as trace  # noqa: E402  (la fonction cheminement() du lanceur porte l'autre nom)
from pilotage.config import DEFAUTS_GUIDE, QUESTIONS, RACINE_GUIDE  # noqa: E402,F401  (partagés avec l'interface web)
from pilotage.couleurs import Couleurs, effacer_ecran, preparer_console  # noqa: E402
from pilotage.menu import Entree, confirmer, demander, proposer  # noqa: E402


# ---------------------------------------------------------------- en-tête

def _abreger(chemin, largeur=50):
    if len(chemin) <= largeur:
        return chemin
    moitie = (largeur - 1) // 2
    return chemin[:moitie] + "…" + chemin[-moitie:]


def entete(ctx):
    c = ctx.c
    ctx.ecrire(c.boite("GIGA-PANO-HDR — LANCEUR"))
    p = ctx.panorama
    if p is None:
        ctx.ecrire(f"  {c.ATTENTION}Aucun panorama courant{c.RESET} : Préparer → Nouveau panorama")
    else:
        grille = "×".join(str(v) if v is not None else "?" for v in (p.lignes, p.colonnes, p.expos))
        maitre = config.valeur(p, "maitre")
        etat_maitre = f"{c.OK}OK{c.RESET}" if maitre and os.path.exists(maitre) else f"{c.DIM}absent{c.RESET}"
        ctx.ecrire(f"  Panorama : {c.VALEUR}{_abreger(p.T)}{c.RESET} · {grille} · maître {etat_maitre}")
    ctx.ecrire(f"  {outils.resume(ctx.etats, c)}")


def _sous_menu(titre, constructeur):
    def action(ctx):
        menu.boucle(titre, constructeur(ctx), ctx, ctx.c, entete=entete, lire=ctx.lire, ecrire=ctx.ecrire)
    return action


def _py(script, declares=None, ecrit=None, lit=None):
    """Action : menu de pilotage puis exécution d'un script Python (déclaration lue dans le script, sauf
    `declares`) ; `lit` (argument -> clé de panorama.json) relie ces arguments au panorama pour les préremplir."""
    def action(ctx):
        args, annonce = declares, ecrit
        if lit:
            if args is None:
                args, annonce, _ = arguments.lire_declaration(ctx.scripts / script)
            args = arguments.appliquer_lit(args, lit)
        return lancer.python(ctx, script, args, annonce)
    return menu.sans_pause(action)


def _ps(script, lit=None):
    """Action : menu de pilotage puis exécution d'un script PowerShell (déclaration de declarations_ps) ; `lit`
    comme pour _py."""
    args, ecrit = declarations_ps.PS[script]
    if lit:
        args = arguments.appliquer_lit(args, lit)
    return menu.sans_pause(lambda ctx: lancer.powershell(ctx, script, args, ecrit))


def _requiert(*cles, powershell=True):
    """Disponibilité : PowerShell (sauf `powershell=False`) et les outils nommés doivent être présents ; sinon la
    raison (_raison) dit lequel manque."""
    def disponible(ctx):
        return (not powershell or lancer.powershell_disponible(ctx)) and all(lancer.present(ctx, k) for k in cles)
    return disponible


def _raison(ctx, *cles, powershell=True):
    if powershell and not lancer.powershell_disponible(ctx):
        return "PowerShell introuvable"
    manquants = [outils.OUTILS[[o.cle for o in outils.OUTILS].index(k)].nom for k in cles if not lancer.present(ctx, k)]
    return f"{', '.join(manquants)} absent" if manquants else ""


def entree_ps(tete, script, effet, *cles, etape="", section="", sous_titre=None, lit=None):
    """Entrée d'un script PowerShell ; sous-titre « script (étape) » sauf `sous_titre` donné."""
    if sous_titre is None:
        sous_titre = f"{script} ({etape})" if etape else script
    return Entree(tete, sous_titre, effet=effet, action=_ps(script, lit), disponible=_requiert(*cles),
                  raison=lambda ctx: _raison(ctx, *cles), section=section)


def geste(tete, rappel, section=""):
    """Entrée informative : un geste dans Hugin ou Lightroom, jamais numérotée."""
    return Entree(tete, rappel, action=None, section=section)


def cpclean(ctx):
    """cpclean.exe (livré avec Hugin), puis on rappelle de remettre les chemins en relatifs. Déclaration et
    commande partagées avec l'interface web (catalogue.ARGS_CPCLEAN, lancer.commande_cpclean)."""
    argv = arguments.menu(catalogue.DOC_CPCLEAN, catalogue.ARGS_CPCLEAN, catalogue.ECRIT_CPCLEAN,
                          panorama=ctx.panorama, c=ctx.c, lire=ctx.lire, ecrire=ctx.ecrire)
    if argv is None:
        return None
    try:
        commande = lancer.commande_cpclean(ctx, argv)
    except LookupError as e:
        ctx.ecrire(ctx.c.erreur(str(e)))
        return None
    return lancer._executer(ctx, commande)


# ---------------------------------------------------------------- phase 0

def versions(ctx):
    c = ctx.c
    ctx.ecrire("")
    ctx.ecrire(c.titre("Outils détectés"))
    ctx.ecrire(c.separateur())
    for e in ctx.etats:
        if e.present:
            version = e.version or "version inconnue"
            ctx.ecrire(f"  {c.OK}{'OK':8}{c.RESET} {e.outil.nom:14} {c.VALEUR}{version:16}{c.RESET} {c.DIM}{e.chemin}{c.RESET}")
        else:
            ctx.ecrire(f"  {c.ERREUR}{'ABSENT':8}{c.RESET} {e.outil.nom:14} {c.DIM}{e.outil.url or ''}{c.RESET}")


def installer(ctx):
    c = ctx.c
    absents = [e for e in ctx.etats if not e.present]
    if not absents:
        ctx.ecrire(c.succes("Tous les outils sont présents."))
        return
    for e in absents:
        o = e.outil
        ctx.ecrire("")
        ctx.ecrire(c.titre(o.nom))
        commande = outils.commande_installation(o)
        if commande:
            ctx.ecrire(f"  Commande : {c.VALEUR}{commande}{c.RESET}")
            if confirmer("  Exécuter maintenant ?", c, defaut_oui=False, lire=ctx.lire):
                ctx.executer(commande, shell=True)
        elif o.url:
            ctx.ecrire(f"  Téléchargement : {c.VALEUR}{o.url}{c.RESET}")
            if o.dezipper:
                ctx.ecrire(f"  Dézipper dans un dossier durable, par exemple {c.VALEUR}{o.dezipper}{c.RESET}")
            if confirmer("  Ouvrir la page ?", c, defaut_oui=False, lire=ctx.lire):
                try:
                    os.startfile(o.url)
                except Exception:
                    ctx.ecrire(c.attention("Impossible d'ouvrir le navigateur : copier l'adresse ci-dessus."))
    ctx.ecrire("")
    ctx.ecrire(c.info("La détection sera à jour au prochain démarrage du lanceur."))


def presets_lightroom(ctx):
    c = ctx.c
    ctx.ecrire("")
    ctx.ecrire(c.titre("Dossiers des préréglages Lightroom (option « Stocker avec ce catalogue » décochée)"))
    for libelle, chemin, existe in outils.dossiers_presets_lightroom():
        marque = c.OK + "OK" + c.RESET if existe else c.DIM + "absent" + c.RESET
        ctx.ecrire(f"  {libelle:30} {marque:>6}  {c.VALEUR}{chemin}{c.RESET}")
    ctx.ecrire(f"  {c.DIM}Si l'option est cochée, les préréglages sont dans « Paramètres Lightroom », à côté du catalogue.{c.RESET}")
    ctx.ecrire(f"  {c.DIM}Rien n'est copié : créer les préréglages comme le guide l'indique (0C).{c.RESET}")


def _nombre(texte, entier=False):
    if texte in (None, ""):
        return None
    try:
        return int(texte) if entier else float(texte)
    except ValueError:
        return None


class _Annule(Exception):
    pass


def _texte(v):
    return "" if v is None else (f"{v:g}" if isinstance(v, float) else str(v))


def nouveau_panorama(ctx):
    """Chaque question propose une valeur : celle du panorama.json déjà présent dans $T, sinon celle du panorama
    courant (même série d'objectif), sinon celle du guide. y ou ENTRÉE valide, autre saisie remplace, x annule tout.
    Les chemins suivent le guide (0D) : $T = <racine>\\<date>\\<focale>mm (racine du panorama courant, sinon
    D:\\Panoramas), $H = <dossier des RAW>\\HDR."""
    c = ctx.c
    ctx.ecrire("")
    ctx.ecrire(c.titre("Nouveau panorama"))

    def question(invite, defaut=None, entier=None):
        while True:
            reponse = proposer(invite, c, _texte(defaut), lire=ctx.lire)
            if reponse is None:
                raise _Annule
            if entier is None or reponse == "":
                return reponse
            valeur = _nombre(reponse, entier=entier)
            if valeur is not None:
                return valeur
            ctx.ecrire(c.erreur(f"« {reponse} » : {'nombre entier' if entier else 'nombre'} attendu"))

    try:
        courant = ctx.panorama
        date = question("Date de la prise de vue (AAAA-MM-JJ)", datetime.date.today().isoformat())
        focale = question("Focale (mm)", courant.focale if courant else None, entier=False) or None
        T = question("Dossier de travail $T (hors catalogue Lightroom)",
                     config.propositions_nouveau(courant, date, focale, None, None)["T"])
        if not T:
            ctx.ecrire(c.attention("Dossier de travail vide : rien n'a été écrit."))
            return
        prop = config.propositions_nouveau(courant, date, focale, T, None)
        if prop["existant"]:
            ctx.ecrire(c.info(f"panorama.json trouvé dans {T} : ses valeurs sont proposées."))
        raws = question("Dossier des RAW de ce panorama, dans le catalogue Lightroom (facultatif)",
                        prop["raws"] or None)
        prop = config.propositions_nouveau(courant, date, focale, T, raws)
        valeurs = {"T": T, "focale": focale}
        valeurs["H"] = question("Dossier HDR $H (calques et DNG HDR)", prop["H"] or None)
        for cle, invite, entier in QUESTIONS:
            valeurs[cle] = question(invite, prop[cle], entier) or None
    except _Annule:
        ctx.ecrire(c.attention("Annulé : rien n'a été écrit."))
        return
    p, crees = config.creer_nouveau(ctx.poste, valeurs)
    ctx.panorama = p
    for d in crees:
        ctx.ecrire(c.succes(f"créé : {d}"))
    ctx.ecrire(c.succes(f"panorama.json écrit dans {T} ; panorama courant."))


def changer_panorama(ctx):
    c = ctx.c
    if not ctx.poste.panoramas:
        ctx.ecrire(c.attention("Aucun panorama connu : Préparer → Nouveau panorama."))
        return
    ctx.ecrire("")
    for i, T in enumerate(ctx.poste.panoramas, 1):
        marque = " (courant)" if T == ctx.poste.courant else ""
        ctx.ecrire(f"  {c.JAUNE}{i}{c.RESET}. {T}{marque}")
    choix = ctx.lire(c.prompt("  Panorama courant (0 pour annuler) : ")).strip()
    if choix.isdigit() and 1 <= int(choix) <= len(ctx.poste.panoramas):
        ctx.poste.courant = ctx.poste.panoramas[int(choix) - 1]
        config.enregistrer_poste(ctx.poste)
        ctx.panorama = config.panorama_courant(ctx.poste)
        ctx.ecrire(c.succes(f"Panorama courant : {ctx.poste.courant}"))


def cheminement(ctx):
    """1B : choisir le coin de départ et le serpentin de la prise de vue. Le dessin 3 x 5 montre le cheminement ;
    hg, hd, bg, bd choisit le coin (la flèche pointe vers le centre : le sens de la prise de vue), s bascule le
    serpentin, v ou ENTRÉE valide et écrit panorama.json, x annule."""
    c = ctx.c
    p = ctx.panorama
    if p is None:
        ctx.ecrire(c.attention("Aucun panorama courant : Préparer → Nouveau panorama."))
        return
    depart, serpentin = p.depart, bool(p.serpentin)
    if depart not in trace.COINS:       # panorama.json édité à la main : proposer le défaut, valider le répare
        ctx.ecrire(c.attention(f"panorama.json : départ {depart!r} inconnu, {trace.DEFAUT} proposé."))
        depart = trace.DEFAUT
    coins = "   ".join(f"{c.JAUNE}{k}{c.RESET} {trace.FLECHES_COINS[k]} {trace.NOMS_COINS[k]}" for k in trace.COINS)
    while True:
        ctx.ecrire("")
        ctx.ecrire(c.titre("Cheminement de la prise de vue (1B)"))
        ctx.ecrire(c.info("Toujours en lignes, jamais en colonnes ; 1 = première photo (dessin : 3 lignes x 5 colonnes)."))
        for ligne in trace.dessin_texte(depart, serpentin):
            ctx.ecrire(f"  {ligne}")
        ctx.ecrire(f"  {c.VALEUR}{trace.resume(depart, serpentin)}{c.RESET}")
        ctx.ecrire(f"  Coin de départ : {coins}")
        ctx.ecrire(f"  {c.JAUNE}s{c.RESET} Serpentin : {'activé' if serpentin else 'désactivé'}    "
                   f"{c.JAUNE}v{c.RESET} Valider    {c.JAUNE}x{c.RESET} Annuler")
        choix = ctx.lire(c.prompt("  Votre choix : ")).strip().lower()
        if choix == "x":
            ctx.ecrire(c.attention("Annulé : rien n'a été écrit."))
            return
        if choix in ("v", ""):
            ctx.panorama = config.mettre_a_jour(p.T, depart=depart, serpentin=serpentin)
            ctx.ecrire(c.succes(f"panorama.json : départ {depart}, serpentin {'oui' if serpentin else 'non'}."))
            return
        if choix == "s":
            serpentin = not serpentin
        elif choix in trace.COINS:
            depart = choix
        else:
            ctx.ecrire(c.erreur(f'Choix invalide : "{choix}" (hg, hd, bg, bd, s, v ou x)'))


def menu_phase0(ctx):
    return [
        Entree("Versions des outils", "nona, enblend, multiblend, vips, exiftool, python, Pillow, pwsh",
               action=versions, section="PHASE 0 — PRÉPARER LE POSTE"),
        Entree("Installer ce qui manque", "winget ou page de téléchargement, sur confirmation", effet="poste",
               action=installer, section="PHASE 0 — PRÉPARER LE POSTE"),
        Entree("Dossiers des préréglages Lightroom", "où créer les préréglages du guide (0C)",
               action=presets_lightroom, section="PHASE 0 — PRÉPARER LE POSTE"),
        Entree("Nouveau panorama", "$T, $H, grille, pas ; crée tous les dossiers, des exports à 7_galerie",
               effet="$T (exports, Assemblage-Hugin), $H\\TIFF et panorama.json",
               action=nouveau_panorama, section="PANORAMA"),
        Entree("Changer de panorama courant", "parmi les panoramas connus", effet="config du poste",
               action=changer_panorama, section="PANORAMA"),
        Entree("Cheminement de la prise de vue", "coin de départ et serpentin (1B)", effet="panorama.json",
               action=cheminement, section="PANORAMA"),
    ]


# ---------------------------------------------------------------- configuration

OUTILS_CONFIGURABLES = [("hugin", "Dossier bin de Hugin"), ("multiblend", "multiblend.exe"),
                        ("vips", "vips.exe"), ("exiftool", "exiftool.exe")]


def _regler_outil(cle, libelle):
    def action(ctx):
        actuel = ctx.poste.outils.get(cle, "")
        nouveau = demander(f"{libelle}", ctx.c, defaut=actuel or None, lire=ctx.lire)
        if nouveau is None:
            return
        ctx.poste.outils[cle] = nouveau
        config.enregistrer_poste(ctx.poste)
        ctx.etats = outils.detecter_tous(ctx.poste.outils)
        ctx.ecrire(ctx.c.succes(f"{libelle} : {nouveau}"))
    return action


def menu_configuration(ctx):
    entrees = []
    for cle, libelle in OUTILS_CONFIGURABLES:
        entrees.append(Entree(lambda ctx, cle=cle, libelle=libelle: f"{libelle} : {ctx.poste.outils.get(cle, '(détection automatique)')}",
                              action=_regler_outil(cle, libelle), effet="config du poste", section="CHEMINS DES OUTILS"))
    entrees.append(Entree("Changer de panorama courant", action=changer_panorama, effet="config du poste",
                          section="PANORAMA"))
    return entrees


# ---------------------------------------------------------------- menu principal

# ---------------------------------------------------------------- phases 2 à 7

def entree_depuis(tache):
    """Entrée de menu d'une tâche du catalogue : geste informatif, action du lanceur, script PowerShell ou Python.

    `tache.lit` relie des arguments au panorama (préremplissage), comme dans la page web. La console n'a qu'UNE
    entrée par script, celle de la tâche qui porte `groupe_console` : c'est son `lit` qui s'applique (5B pour
    nona_images.ps1), pas celui des autres repères du même script (6B, 6C.2), absents de la console."""
    if tache.geste:
        return geste(tache.tete, tache.geste, section=tache.section)
    if tache.action:
        cles = tache.outils
        return Entree(tache.tete, tache.sous_titre, effet=tache.effet, action=ACTIONS[tache.action],
                      disponible=_requiert(*cles, powershell=False),
                      raison=lambda ctx: _raison(ctx, *cles, powershell=False), section=tache.section)
    if tache.script.endswith(".ps1"):
        return entree_ps(tache.tete, tache.script, tache.effet, *tache.outils, section=tache.section,
                         sous_titre=tache.sous_titre, lit=tache.lit)
    return Entree(tache.tete, tache.sous_titre, effet=tache.effet,
                  action=_py(tache.script, tache.arguments, tache.ecrit or None, lit=tache.lit), section=tache.section)


ACTIONS = {"cpclean": cpclean}


def menu_phase2(ctx):
    return [entree_depuis(t) for t in catalogue.console("phase2")]


def menu_phase3(ctx):
    return [entree_depuis(t) for t in catalogue.console("phase3")]


def menu_rendus(ctx):
    return [entree_depuis(t) for t in catalogue.console("rendus")]


def menu_mesures(ctx):
    return [entree_depuis(t) for t in catalogue.console("mesures")]


def menu_phase7(ctx):
    return [entree_depuis(t) for t in catalogue.console("phase7")]


SOUS_MENUS = {
    "phase0": menu_phase0, "phase2": menu_phase2, "phase3": menu_phase3, "rendus": menu_rendus,
    "mesures": menu_mesures, "phase7": menu_phase7, "configuration": menu_configuration,
}


def menu_principal(ctx):
    def nav(tete, sous_titre, titre, constructeur):
        return Entree(tete, sous_titre, action=_sous_menu(titre, constructeur), navigation=True)
    return [
        nav("Préparer le poste et le panorama", "Phase 0", "PHASE 0", menu_phase0),
        nav("Contrôler et renommer l'export", "Phase 2", "PHASE 2", menu_phase2),
        nav("Établir la géométrie", "Phase 3", "PHASE 3", menu_phase3),
        nav("Rendre : vue centrée, HDR, pleine résolution", "Phases 4 à 6", "RENDUS", menu_rendus),
        nav("Mesurer et inspecter", "ciel, raccords, géométrie", "MESURES", menu_mesures),
        nav("Tuiler et cadrer", "Phase 7", "PHASE 7", menu_phase7),
        nav("Configuration", "chemins des outils, panorama courant", "CONFIGURATION", menu_configuration),
    ]


def boucle_principale(ctx, effacer=effacer_ecran):
    menu.boucle("LANCEUR", menu_principal(ctx), ctx, ctx.c, entete=entete, lire=ctx.lire, ecrire=ctx.ecrire,
                effacer=effacer)


def main(argv=None):
    preparer_console()
    poste = config.charger_poste()
    ctx = lancer.Contexte(poste=poste, panorama=config.panorama_courant(poste),
                          etats=outils.detecter_tous(poste.outils), c=Couleurs())
    try:
        boucle_principale(ctx)
    except (KeyboardInterrupt, EOFError):
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
