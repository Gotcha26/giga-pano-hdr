"""Exécution des scripts en arrière-plan : sortie capturée ligne à ligne, arrêt de l'arbre de processus.

Logique pure, sans NiceGUI. Un fil lit la sortie (erreurs mêlées) et la range dans Execution.lignes : la page peut
les relire à tout moment depuis son propre fil (list.append est atomique, on ne fait que lire ou ajouter à la fin).
REGISTRE garde la dernière exécution de chaque tâche, de quoi la retrouver quand l'onglet est rouvert.

Fin d'une exécution : normalement quand la sortie se ferme (le fil de lecture attend alors le code de sortie).
Deux cas tordus sont couverts :
- la sortie se ferme mais le processus tourne encore (il a fermé sa sortie) : après DELAI_FIN secondes, une ligne
  [interface] le signale et l'attente continue ; l'exécution reste « en cours », Arrêter la termine ;
- le processus se termine mais un descendant (un programme lancé par le .ps1) garde la sortie ouverte : un fil de
  surveillance attend la fin du processus puis DELAI_FIN secondes ; la sortie toujours ouverte, il clôt
  l'exécution avec le code du processus et une ligne [interface] ; la suite de la sortie s'ajoute encore au journal.
"""

import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

CODE_INTERRUPTION = 130
DELAI_FIN = 10                              # secondes de grâce entre fin de sortie et fin de processus (et inversement)
PAGE_OEM_REPLI = "cp850"
NOTE_ENFANT = ("[interface] processus parent terminé, un enfant garde la sortie : tâche close, "
               "la suite de sa sortie s'affiche encore ici")
# sans console à créer : le serveur peut tourner sans fenêtre, un script lancé ne doit pas en ouvrir une
SANS_FENETRE = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


class DejaEnCours(RuntimeError):
    """La même tâche tourne encore (deux onglets, ou un double clic)."""


@dataclass
class Execution:
    identifiant: str
    commande: list[str]
    lignes: list[str] = field(default_factory=list)
    code: Optional[int] = None
    etat: str = "en cours"                  # puis « terminée », « échec » ou « interrompue »
    demarre: float = field(default_factory=time.time)
    processus: object = field(default=None, repr=False)
    arret_demande: bool = False
    fini: threading.Event = field(default_factory=threading.Event, repr=False)
    conclue: bool = field(default=False, repr=False)
    verrou: threading.Lock = field(default_factory=threading.Lock, repr=False)


REGISTRE: dict = {}
_VERROU_DEMARRAGE = threading.Lock()       # contrôle « déjà en cours » et inscription au registre, d'un tenant


def en_cours():
    return [ex for ex in list(REGISTRE.values()) if ex.etat == "en cours"]


def derniere(identifiant):
    return REGISTRE.get(identifiant)


def _etat_final(ex):
    if ex.arret_demande or ex.code == CODE_INTERRUPTION:
        return "interrompue"
    return "terminée" if ex.code == 0 else "échec"


def page_oem():
    """Page de code OEM du système (« cp850 »…) : celle des programmes Windows qui n'écrivent pas en UTF-8. Les
    scripts tournent dans leur propre console cachée (CREATE_NO_WINDOW), ouverte avec cette page-là, quelle que
    soit celle de la console du serveur (un « chcp 65001 » n'y change rien) ; PAGE_OEM_REPLI hors Windows."""
    if sys.platform == "win32":
        try:
            import ctypes
            page = ctypes.windll.kernel32.GetOEMCP()
            if page:
                return f"cp{page}"
        except (OSError, AttributeError):
            pass
    return PAGE_OEM_REPLI


def _decoder(octets):
    """UTF-8 strict (les scripts du dépôt) ; sinon la page de code de la console (nona, enblend, cmd… écrivent
    en OEM) ; sinon UTF-8 avec remplacement des octets invalides."""
    try:
        return octets.decode("utf-8")
    except UnicodeDecodeError:
        pass
    try:
        return octets.decode(page_oem())
    except (UnicodeDecodeError, LookupError):
        return octets.decode("utf-8", errors="replace")


def _noter(ex, sur_ligne, texte):
    """Ligne de l'interface : rangée et transmise comme une ligne du script ; si le rappel lève sur elle, rien de
    plus (pas de nouvelle ligne d'erreur, donc pas de boucle)."""
    ex.lignes.append(texte)
    if sur_ligne is not None:
        try:
            sur_ligne(texte)
        except Exception:
            pass


def _appeler(ex, rappel, *args, sur_ligne=None):
    """Un rappel de la page qui lève ne doit pas tuer la lecture : l'erreur est notée dans la sortie."""
    if rappel is None:
        return
    try:
        rappel(*args)
    except Exception as e:
        _noter(ex, sur_ligne, f"[interface] erreur dans un rappel : {e}")


def _ligne(ex, octets, sur_ligne):
    texte = _decoder(octets.rstrip(b"\r"))
    ex.lignes.append(texte)
    _appeler(ex, sur_ligne, texte, sur_ligne=sur_ligne)


def _attendre_code(ex, sur_ligne):
    """Code de sortie ; si le processus tourne encore DELAI_FIN s après la fermeture de sa sortie, le signale puis
    attend sans limite (l'exécution reste « en cours » : Arrêter la termine)."""
    try:
        return ex.processus.wait(timeout=DELAI_FIN)
    except subprocess.TimeoutExpired:
        _noter(ex, sur_ligne, "[interface] sortie fermée mais le processus tourne encore : attente de sa fin")
        return ex.processus.wait()


def _conclure(ex, sur_ligne, sur_fin, code=None, note=None):
    """Clôt l'exécution une seule fois (fil de lecture ou fil de surveillance, le premier arrivé) ; `note` n'est
    écrite que par celui qui clôt (jamais une ligne trompeuse si l'autre fil a déjà conclu)."""
    with ex.verrou:
        if ex.conclue:
            return
        ex.conclue = True
        if note:
            _noter(ex, sur_ligne, note)
        try:
            ex.code = _attendre_code(ex, sur_ligne) if code is None else code
            ex.etat = _etat_final(ex)
            _appeler(ex, sur_fin, ex, sur_ligne=sur_ligne)
        finally:
            ex.fini.set()


def _lire(ex, sur_ligne, sur_fin):
    reste = b""
    try:
        while True:
            bloc = ex.processus.stdout.read(4096)
            if not bloc:
                break
            reste += bloc
            *entieres, reste = reste.split(b"\n")
            for octets in entieres:
                _ligne(ex, octets, sur_ligne)
        if reste:
            _ligne(ex, reste, sur_ligne)
    except (OSError, ValueError) as e:       # tube fermé sous les pieds du fil
        _noter(ex, sur_ligne, f"[interface] lecture interrompue : {e}")
    finally:
        _conclure(ex, sur_ligne, sur_fin)


def _surveiller(ex, sur_ligne, sur_fin):
    """Clôt l'exécution si le processus est fini mais qu'un descendant garde sa sortie ouverte."""
    code = ex.processus.wait()
    if ex.fini.wait(DELAI_FIN):
        return
    _conclure(ex, sur_ligne, sur_fin, code=code, note=NOTE_ENFANT)


def options_fenetre():
    """Arguments de subprocess pour ne pas ouvrir de console sous Windows ({} ailleurs)."""
    return {"creationflags": SANS_FENETRE} if sys.platform == "win32" else {}


def demarrer(identifiant, commande, cwd, env, sur_ligne: Optional[Callable] = None,
             sur_fin: Optional[Callable] = None, Popen=subprocess.Popen):
    """Lance la commande, enregistre l'exécution dans REGISTRE et rend la main ; OSError si le lancement échoue,
    DejaEnCours (une RuntimeError) si la même tâche tourne encore (deux onglets, ou un double clic : une seule à
    la fois).

    L'entrée standard est fermée (DEVNULL) : un script interactif qui appelle input() échoue au lieu d'attendre
    une saisie que la page ne peut pas fournir."""
    with _VERROU_DEMARRAGE:
        precedente = derniere(identifiant)
        if precedente is not None and precedente.etat == "en cours":
            raise DejaEnCours(f"tâche déjà en cours : {identifiant}")
        return _lancer(identifiant, commande, cwd, env, sur_ligne, sur_fin, Popen)


def _lancer(identifiant, commande, cwd, env, sur_ligne, sur_fin, Popen):
    processus = Popen(commande, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                      stderr=subprocess.STDOUT, bufsize=0, **options_fenetre())
    ex = Execution(identifiant, list(commande), processus=processus)
    REGISTRE[identifiant] = ex
    threading.Thread(target=_lire, args=(ex, sur_ligne, sur_fin), daemon=True).start()
    threading.Thread(target=_surveiller, args=(ex, sur_ligne, sur_fin), daemon=True).start()
    return ex


def arreter(ex, lancer=subprocess.run):
    """Arrête le processus et ses descendants (taskkill /T /F sous Windows : un .ps1 lance d'autres programmes).

    Un processus déjà fini (fin naturelle juste avant le clic) n'est pas touché : l'exécution garde l'état de sa
    fin (« terminée », « échec »), pas « interrompue »."""
    if ex.processus.poll() is not None:
        return
    ex.arret_demande = True
    if sys.platform == "win32":
        lancer(["taskkill", "/T", "/F", "/PID", str(ex.processus.pid)], capture_output=True, **options_fenetre())
    else:
        ex.processus.terminate()
    if ex.processus.poll() is None and sys.platform == "win32":
        ex.processus.kill()                 # repli si taskkill n'a pas abouti
