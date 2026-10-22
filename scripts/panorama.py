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
from pilotage.arguments import Arg  # noqa: E402
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


def _py(script, arguments=None, ecrit=None):
    """Action : menu de pilotage puis exécution d'un script Python (déclaration lue dans le script)."""
    return menu.sans_pause(lambda ctx: lancer.python(ctx, script, arguments, ecrit))


def _ps(script):
    """Action : menu de pilotage puis exécution d'un script PowerShell (déclaration de declarations_ps)."""
    args, ecrit = declarations_ps.PS[script]
    return menu.sans_pause(lambda ctx: lancer.powershell(ctx, script, args, ecrit))


def _requiert(*cles):
    """Disponibilité : PowerShell et les outils nommés doivent être présents ; sinon la raison dit lequel manque."""
    def disponible(ctx):
        return lancer.powershell_disponible(ctx) and all(lancer.present(ctx, k) for k in cles)
    return disponible


def _raison(ctx, *cles):
    if not lancer.powershell_disponible(ctx):
        return "PowerShell introuvable"
    manquants = [outils.OUTILS[[o.cle for o in outils.OUTILS].index(k)].nom for k in cles if not lancer.present(ctx, k)]
    return f"{', '.join(manquants)} absent" if manquants else ""


def entree_ps(tete, script, effet, *cles, etape="", section=""):
    sous_titre = f"{script} ({etape})" if etape else script
    return Entree(tete, sous_titre, effet=effet, action=_ps(script), disponible=_requiert(*cles),
                  raison=lambda ctx: _raison(ctx, *cles), section=section)


def geste(tete, rappel, section=""):
    """Entrée informative : un geste dans Hugin ou Lightroom, jamais numérotée."""
    return Entree(tete, rappel, action=None, section=section)


def cpclean(ctx):
    """cpclean.exe (livré avec Hugin), puis on rappelle de remettre les chemins en relatifs."""
    args = [Arg("entree.pto", "Projet avec points de contrôle bruts", type="pto", config="cp_pto", phase="3_grille"),
            Arg("sortie.pto", "Projet nettoyé à écrire (dans 3_optimisation)", type="pto")]
    argv = arguments.menu("cpclean : nettoyage statistique des points de contrôle (-p -n 2)", args,
                          "le projet de sortie (chemins d'images ABSOLUS : remettre en relatifs ensuite)",
                          panorama=ctx.panorama, c=ctx.c, lire=ctx.lire, ecrire=ctx.ecrire)
    if argv is None:
        return None
    return lancer.outil(ctx, "hugin", ["cpclean.exe", "-p", "-n", "2", "-o", argv[1], argv[0]])


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
        racine = str(Path(courant.T).parent.parent) if courant and courant.T else RACINE_GUIDE
        T = question("Dossier de travail $T (hors catalogue Lightroom)",
                     str(Path(racine, date, f"{focale:g}mm" if focale else "")))
        if not T:
            ctx.ecrire(c.attention("Dossier de travail vide : rien n'a été écrit."))
            return
        existant = config.charger_panorama(T)
        if existant:
            ctx.ecrire(c.info(f"panorama.json trouvé dans {T} : ses valeurs sont proposées."))
        source = existant or courant
        raws = question("Dossier des RAW de ce panorama, dans le catalogue Lightroom (facultatif)",
                        str(Path(existant.H).parent) if existant and existant.H else None)
        H = question("Dossier HDR $H (calques et DNG HDR)",
                     existant.H if existant and existant.H else (str(Path(raws, "HDR")) if raws else None))
        valeurs = {"focale": focale}
        for cle, invite, entier in QUESTIONS:
            defaut = getattr(source, cle, None) if source else None
            valeurs[cle] = question(invite, defaut if defaut is not None else DEFAUTS_GUIDE.get(cle), entier) or None
    except _Annule:
        ctx.ecrire(c.attention("Annulé : rien n'a été écrit."))
        return
    p = config.Panorama(T=T, P=os.path.join(T, "Assemblage-Hugin"), H=H or "", **valeurs)
    if existant:            # ce que le lanceur ne demande pas (maître, noms d'export) est conservé
        p.maitre, p.export_l, p.export_h = existant.maitre, existant.export_l, existant.export_h
    crees = config.creer_arborescence(p)
    config.enregistrer_panorama(p)
    if T not in ctx.poste.panoramas:
        ctx.poste.panoramas.append(T)
    ctx.poste.courant = T
    config.enregistrer_poste(ctx.poste)
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
    """Entrée de menu d'une tâche du catalogue : geste informatif, action du lanceur, script PowerShell ou Python."""
    if tache.geste:
        return geste(tache.tete, tache.geste, section=tache.section)
    if tache.action:
        cles = tache.outils
        return Entree(tache.tete, tache.sous_titre, effet=tache.effet, action=ACTIONS[tache.action],
                      disponible=lambda ctx: all(lancer.present(ctx, k) for k in cles),
                      raison=lambda ctx: ", ".join(o.nom for o in outils.OUTILS
                                                   if o.cle in cles and not lancer.present(ctx, o.cle)) + " absent",
                      section=tache.section)
    if tache.script.endswith(".ps1"):
        e = entree_ps(tache.tete, tache.script, tache.effet, *tache.outils, section=tache.section)
        e.sous_titre = tache.sous_titre
        return e
    return Entree(tache.tete, tache.sous_titre, effet=tache.effet,
                  action=_py(tache.script, tache.arguments, tache.ecrit or None), section=tache.section)


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
