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

from pilotage import arguments, config, declarations_ps, lancer, menu, outils  # noqa: E402
from pilotage.arguments import Arg  # noqa: E402
from pilotage.couleurs import Couleurs, effacer_ecran, preparer_console  # noqa: E402
from pilotage.menu import Entree, confirmer, demander  # noqa: E402


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

# ---------------------------------------------------------------- phases 2 à 7

def menu_phase2(ctx):
    S = "PHASE 2 — CONTRÔLER ET RENOMMER L'EXPORT"
    table = [Arg("REFERENCE", "Dossier déjà renommé L_C_E", type="dossier", config="export_l"),
             Arg("NOUVEL_EXPORT", "Fichier CSV à écrire (table raw,lce)", type="chemin", config="table"),
             Arg("--table", "Écrire la table", type="drapeau", defaut=True)]
    return [
        Entree("Vérifier l'ordre et le motif d'exposition", "verifier_ordre.py (2E)", action=_py("verifier_ordre.py"), section=S),
        Entree("Contrôler les réglages Lightroom des TIFF", "controle_reglages_export.py (2E)", action=_py("controle_reglages_export.py"), section=S),
        Entree("Mesurer l'écart de rendu entre voisines", "ecart_paires.py (2E, à partir de la Phase 3)", action=_py("ecart_paires.py"), section=S),
        Entree("Lire la taille d'un TIFF", "tiffinfo.py", action=_py("tiffinfo.py"), section=S),
        Entree("Renommer le premier export en L_C_E", "renommer_pano.py (2F) : contrôlé par la table, ou l'écrit",
               effet="noms de fichiers du dossier et table_raw_LCE.csv si elle manque (essai à blanc sans --apply)",
               action=_py("renommer_pano.py"), section=S),
        Entree("Écrire la table RAW → L_C_E", "renommer_par_raw.py --table (export déjà renommé autrement)", effet="table_raw_LCE.csv",
               action=_py("renommer_par_raw.py", table, "la table CSV"), section=S),
        Entree("Renommer un export d'après la table RAW", "renommer_par_raw.py (2D, 6A.2)", effet="noms de fichiers du nouvel export (essai à blanc sans --apply)",
               action=_py("renommer_par_raw.py"), section=S),
    ]


def menu_phase3(ctx):
    A, B = "GRILLE ET POINTS (3A à 3D)", "OPTIMISER ET REPLACER (3E à 3H)"
    return [
        Entree("Générer le projet de grille", "generer_pto.py (3A)", effet="3_grille\\pano_grille.pto", action=_py("generer_pto.py"), section=A),
        geste("3B — Points de contrôle", "dans Hugin : Photos → CPFind (prealigned) → Créer des points → Enregistrer sous 3_grille\\pano_grille_cp.pto", section=A),
        Entree("Nettoyer les points", "cpclean -p -n 2 (3C.1)", effet="3_optimisation\\…_clean.pto", action=cpclean,
               disponible=lambda ctx: lancer.present(ctx, "hugin"), raison="Hugin absent", section=A),
        Entree("Remettre les chemins d'images en relatifs", "deplacer_projet.py (3C.1, après cpclean)", effet="le projet, en place", action=_py("deplacer_projet.py"), section=A),
        Entree("Vérifier la grille", "diagnostic_cp.py (3C.2)", action=_py("diagnostic_cp.py"), section=A),
        Entree("Chercher le pas vertical réel", "diagnostic_pas_v.py (3C.3)", action=_py("diagnostic_pas_v.py"), section=A),
        Entree("Appliquer le pas vertical", "corriger_pas_v.py (3C.3)", effet="le projet de sortie", action=_py("corriger_pas_v.py"), section=A),
        Entree("Filtrer les faux points", "filtrer_cp.py (3D)", effet="le projet de sortie", action=_py("filtrer_cp.py"), section=A),
        Entree("Préparer l'optimisation", "preparer_optimisation.py (3E)", effet="le projet de sortie", action=_py("preparer_optimisation.py"), section=B),
        geste("3E — Optimiser", "dans Hugin : ouvrir le projet préparé → Optimiser maintenant ! → Yes → Enregistrer sous", section=B),
        Entree("Replacer les images du ciel", "placer_isoles.py (3G)", effet="le projet de sortie", action=_py("placer_isoles.py"), section=B),
        Entree("Affiner les images faibles", "affiner_images_faibles.py (3G)", effet="le projet de sortie", action=_py("affiner_images_faibles.py"), section=B),
        Entree("Détecter les trous", "detecter_trous.py (3H)", action=_py("detecter_trous.py"), section=B),
        Entree("Compter les points d'une paire", "compter_cp_paire.py (3H)", action=_py("compter_cp_paire.py"), section=B),
    ]


def menu_rendus(ctx):
    P4, P5, P6 = "PHASE 4 — VUE CENTRÉE", "PHASE 5 — HDR", "PHASE 6 — PLEINE RÉSOLUTION"
    return [
        Entree("Régler la taille du projet", "redimensionner_projet.py (4A, 6C.1)", effet="le projet de sortie", action=_py("redimensionner_projet.py"), section=P4),
        entree_ps("Rendre un projet (nona puis fusion)", "rendre_projet.ps1", "le dossier de rendu", "hugin", "multiblend", etape="4A, 6B, 6C.4", section=P4),
        Entree("Ranger les images intermédiaires", "ranger_intermediaires.py (4B)", effet="_a_supprimer\\ (essai à blanc sans --apply)", action=_py("ranger_intermediaires.py"), section=P4),
        Entree("Reporter la géométrie sur les expositions", "propager_geometrie.py (5A)", effet="le projet HDR dérivé", action=_py("propager_geometrie.py"), section=P5),
        entree_ps("Reprojeter les images une à une", "nona_images.ps1", "le dossier de rendu (f_NNNN.tif)", "hugin", etape="5B, 6B, 6C.2", section=P5),
        entree_ps("Fusionner un calque par exposition", "fusionner_par_exposition.ps1", "les calques pano_HDR_E*.tif", "multiblend", etape="5B", section=P5),
        geste("5C — Fusion HDR", "dans Lightroom : déplacer les calques dans $H, Synchroniser le dossier, Photo → Fusion de photos → HDR", section=P5),
        geste("6A — Export H", "dans Lightroom : préréglage PANO TIFF (H) E0 depuis les copies virtuelles, puis renommer d'après la table RAW", section=P6),
        Entree("Extraire un sous-projet", "extraire_sous_projet.py (6B, 6C.1)", effet="le projet de sortie", action=_py("extraire_sous_projet.py"), section=P6),
        Entree("Rattacher un projet à un dossier d'images", "deplacer_projet.py --images (6B, 6C.1)", effet="le projet de sortie", action=_py("deplacer_projet.py"), section=P6),
        entree_ps("Copier un rendu en version lisible", "rendre_lisible.ps1", "<nom>_lisible.tif et <nom>_sRGB.jpg", "vips", etape="6B", section=P6),
        entree_ps("Surveiller multiblend pendant la fusion", "surveiller_multiblend.ps1", "le fichier de relevés", etape="6C.4", section=P6),
    ]


def menu_mesures(ctx):
    CIEL, GEO = "CIEL ET RACCORDS", "GÉOMÉTRIE ET CHARGE"
    controle = [Arg("--controle", "Pleine résolution recadrée dont mesurer le vide par coin", type="chemin", obligatoire=True),
                Arg("--vips", "Chemin de vips.exe", type="chemin", config="outil:vips")]
    return [
        Entree("Luminosité du ciel par image", "mesurer_ciel.py (3F)", action=_py("mesurer_ciel.py"), section=CIEL),
        Entree("Écart d'exposition entre voisines (ciel)", "mesurer_gain_paires.py (3F)", action=_py("mesurer_gain_paires.py"), section=CIEL),
        Entree("Ondulation périodique d'un rendu", "mesurer_bandes_ciel.py (3F, 6C.5)", action=_py("mesurer_bandes_ciel.py"), section=CIEL),
        Entree("Localiser les sauts de luminosité", "localiser_sauts_ciel.py (3F)", action=_py("localiser_sauts_ciel.py"), section=CIEL),
        Entree("Comparer deux rendus (luminosité)", "comparer_rendus.py", action=_py("comparer_rendus.py"), section=CIEL),
        Entree("Comparer des rendus (couleur)", "comparer_couleur.py", action=_py("comparer_couleur.py"), section=CIEL),
        Entree("Rehausser le ciel pour voir les raccords", "rehausser_ciel.py (6C.5)", effet="l'image de sortie", action=_py("rehausser_ciel.py"), section=CIEL),
        entree_ps("Profil d'une jonction", "profil_jonction.ps1", None, "vips", etape="6C.5", section=CIEL),
        Entree("Voir les corrections par image", "voir_positions.py (3E, 3G)", action=_py("voir_positions.py"), section=GEO),
        Entree("Lister les pires points de contrôle", "lister_pires_cp.py (3G)", action=_py("lister_pires_cp.py"), section=GEO),
        Entree("Détecter les images aberrantes", "detecter_aberrantes.py (3G)", action=_py("detecter_aberrantes.py"), section=GEO),
        Entree("Mesurer le vide d'un cadrage", "cadrage_lightroom.py --controle (7C)", action=_py("cadrage_lightroom.py", controle, None), section=GEO),
        entree_ps("Mesurer la charge CPU et mémoire d'un rendu", "mesurer_charge.ps1", None, section=GEO),
    ]


def menu_phase7(ctx):
    S = "PHASE 7 — TUILER ET CADRER"
    return [
        entree_ps("Tuiler un panorama en pyramide Deep Zoom", "tuiler.ps1", "la pyramide .dzi et _files", "vips", etape="7A", section=S),
        Entree("Contrôler les tuiles dans le navigateur", "controler_tuiles.py (7B)", action=_py("controler_tuiles.py"), section=S),
        geste("7C — Cadrer", "dans Lightroom, sur le DNG HDR : outil Recadrage, angle 0 ; exporter une copie virtuelle NON recadrée", section=S),
        Entree("Lire le cadrage Lightroom et imprimer les commandes", "cadrage_lightroom.py (7C)", action=_py("cadrage_lightroom.py"), section=S),
        Entree("Empaqueter pour la mise en ligne", "empaqueter.py (7D)", effet="<Sortie>\\<Nom>\\ et <Nom>.zip",
               action=_py("empaqueter.py"), section=S),
    ]


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
