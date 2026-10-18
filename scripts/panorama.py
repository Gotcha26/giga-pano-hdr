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

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pilotage import config, lancer, menu, outils  # noqa: E402
from pilotage.couleurs import Couleurs, effacer_ecran, preparer_console  # noqa: E402
from pilotage.menu import Entree, confirmer, demander  # noqa: E402

A_VENIR = "sous-menu construit à la tâche suivante"


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


def a_venir(ctx):
    ctx.ecrire(ctx.c.info(A_VENIR))


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


def nouveau_panorama(ctx):
    c = ctx.c
    ctx.ecrire("")
    ctx.ecrire(c.titre("Nouveau panorama"))
    T = demander("Dossier de travail $T (hors catalogue Lightroom)", c, lire=ctx.lire)
    if not T:
        return
    H = demander("Dossier HDR $H dans le dossier des RAW (facultatif)", c, lire=ctx.lire) or ""
    lignes = _nombre(demander("Lignes de la grille", c, lire=ctx.lire), entier=True)
    colonnes = _nombre(demander("Colonnes de la grille", c, lire=ctx.lire), entier=True)
    expos = _nombre(demander("Expositions par position", c, lire=ctx.lire), entier=True)
    focale = _nombre(demander("Focale (mm)", c, lire=ctx.lire))
    largeur_mm = _nombre(demander("Côté horizontal du capteur (mm : 24 en portrait plein format)", c, lire=ctx.lire))
    pas_h = _nombre(demander("Pas horizontal (°)", c, lire=ctx.lire))
    pas_v = _nombre(demander("Pas vertical (°)", c, lire=ctx.lire))
    largeur_hdr = _nombre(demander("Largeur du HDR (px)", c, lire=ctx.lire), entier=True)
    largeur_pleine = _nombre(demander("Largeur de la pleine résolution (px)", c, lire=ctx.lire), entier=True)
    p = config.Panorama(T=T, P=os.path.join(T, "Assemblage-Hugin"), H=H, lignes=lignes, colonnes=colonnes,
                        expos=expos, focale=focale, largeur_mm=largeur_mm, pas_h=pas_h, pas_v=pas_v,
                        largeur_hdr=largeur_hdr, largeur_pleine=largeur_pleine)
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
        Entree("Nouveau panorama", "$T, $H, grille, pas ; crée l'arborescence", effet="$T et panorama.json",
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

def menu_principal(ctx):
    return [
        Entree("Préparer le poste et le panorama", "Phase 0", action=_sous_menu("PHASE 0", menu_phase0)),
        Entree("Contrôler et renommer l'export", "Phase 2", action=_sous_menu("PHASE 2", lambda ctx: [Entree("À venir", action=a_venir)])),
        Entree("Établir la géométrie", "Phase 3", action=_sous_menu("PHASE 3", lambda ctx: [Entree("À venir", action=a_venir)])),
        Entree("Rendre : vue centrée, HDR, pleine résolution", "Phases 4 à 6", action=_sous_menu("RENDUS", lambda ctx: [Entree("À venir", action=a_venir)])),
        Entree("Mesurer et inspecter", "ciel, raccords, géométrie", action=_sous_menu("MESURES", lambda ctx: [Entree("À venir", action=a_venir)])),
        Entree("Tuiler et cadrer", "Phase 7", action=_sous_menu("PHASE 7", lambda ctx: [Entree("À venir", action=a_venir)])),
        Entree("Configuration", "chemins des outils, panorama courant", action=_sous_menu("CONFIGURATION", menu_configuration)),
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
