"""La page du lanceur web (disposition A) : assemblage de l'en-tête, de la colonne des phases, de la zone de la
tâche, de la console (journal, fichiers produits, aperçus) et du volet d'aide.

Chaque partie vit dans son module (entete, colonne, zone_tache, console, aide_volet) : fonctions pures en haut,
testées sans serveur, et une fonction `construire(etat)` qui pose ses éléments NiceGUI et range ses fonctions
rafraîchissables dans l'`Etat` de l'onglet ; les parties s'appellent entre elles par cet `Etat`. Ce module garde
l'`Etat`, l'assemblage (`construire`), le minuteur de l'onglet et le démarrage du serveur ; il ré-exporte les
fonctions pures des parties pour ses appelants et ses tests.

Fils d'exécution : un script lancé est lu par un fil de `execution`. Ce fil ne touche jamais la page : la sortie
s'accumule dans `Execution.lignes`, le report automatique (`apres_execution`) n'écrit que panorama.json et ajoute
ses lignes à cette même liste. Chaque onglet relit le tout depuis un `ui.timer` de 0,5 s, dans son propre contexte :
fermer l'onglet ne perd rien, le rouvrir retrouve le journal.
"""

from dataclasses import dataclass, field
from typing import Optional

from pilotage import lancer
from pilotage.catalogue import Tache

from . import aide_volet, colonne, console, entete, execution, zone_tache
from .aide_volet import liens_absolus  # noqa: F401  (ré-exports des fonctions pures des parties)
from .colonne import PHASE0_ENTREE, TITRE_MESURES, arborescence, libelle, titre, titres_phases  # noqa: F401
from .console import LIMITE_IMAGES, VIPS_ABSENT, chemin_vips, dossier_sortie, taille_lisible  # noqa: F401
from .entete import DELAI_SORTIE_FORCEE, changer_panorama, coches, grille, maitre_present, options_panoramas  # noqa: F401
from .formulaire import arguments_d_outil  # noqa: F401
from .reglages import VERROU_PANORAMA  # noqa: F401
from .zone_tache import (ACTION_MESSAGE, DEJA_EN_COURS, MESSAGE_PERIME, apres_execution, cle_attendu,  # noqa: F401
                         etat_execution, formulaire_perime, ligne_report, raisons_indisponible, reporter_gestes,
                         valeurs_lues)

MESSAGE_CHANGE = "Le panorama courant a changé dans un autre onglet : page rechargée."


@dataclass
class Etat:
    """État d'un onglet : la tâche affichée, ses champs, le journal et les fonctions des parties de la page."""
    ctx: lancer.Contexte
    tache: Optional[Tache] = None
    vue: str = "accueil"                    # « accueil », « tache » ou une clé de pages_poste.VUES
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
    # fonctions posées par les parties (construire de chaque module)
    en_tete: object = None                  # entete : en-tête rafraîchissable
    colonne: object = None                  # colonne : colonne rafraîchissable
    centre: object = None                   # zone_tache : zone centrale rafraîchissable
    boutons: object = None                  # zone_tache : boutons Lancer / Mémoriser / Arrêter
    apercus: object = None                  # console : fichiers produits rafraîchissables
    suivi: object = None                    # console : rafraichir_suivi() du journal
    aide: object = None                     # aide_volet : volet d'aide rafraîchissable
    volet: object = None                    # le tiroir de droite qui porte l'aide (Aide le replie)
    rafraichir: object = None               # tout_rafraichir de l'onglet (pages hors tâches)


def construire(ctx):
    """Construit la page d'un onglet : chaque partie pose ses fonctions dans l'`Etat`, puis la disposition."""
    from nicegui import ui

    etat = Etat(ctx=ctx)
    ui.add_head_html('<base target="_blank">')     # les liens du guide s'ouvrent à côté de la page

    def tout_rafraichir():
        etat.en_tete.refresh()
        etat.colonne.refresh()
        etat.centre.refresh()
        etat.aide.refresh()

    def tic():
        if formulaire_perime(etat, ctx):
            ui.notify(MESSAGE_CHANGE, multi_line=True)
            tout_rafraichir()
        etat.suivi()
        n = len(execution.en_cours())
        changement = n != etat.compteur
        etat.compteur = n
        for ex in [ex for ex in etat.lancees if ex.fini.is_set()]:
            etat.lancees.remove(ex)
            ui.notify(f"{ex.identifiant} : {etat_execution(ex)}",
                      type="positive" if ex.code == 0 else "warning")
            changement = True
            if etat.tache is not None and etat.tache.script:
                etat.apercus.refresh()
            elif etat.tache is not None and etat.tache.est_geste:
                etat.centre.refresh()
        if changement:
            etat.en_tete.refresh()

    etat.rafraichir = tout_rafraichir
    entete.construire(etat)
    colonne.construire(etat, arborescence())
    zone_tache.construire(etat)
    console.construire(etat)
    aide_volet.construire(etat)

    with ui.header().classes("items-center gap-4 bg-slate-800 text-white"):
        etat.en_tete()
    with ui.left_drawer(value=True).props("width=300 bordered").classes("p-0"):
        etat.colonne()
    with ui.right_drawer(value=True).props("width=440 bordered") as volet:
        etat.volet = volet
        etat.aide()
    with ui.column().classes("w-full max-w-5xl gap-3"):
        etat.centre()
    ui.timer(0.5, tic)
    return etat


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
