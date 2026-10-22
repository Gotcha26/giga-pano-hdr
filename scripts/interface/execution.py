"""Exécution des scripts en arrière-plan : sortie capturée ligne à ligne, arrêt de l'arbre de processus.

Logique pure, sans NiceGUI. Un fil lit la sortie (erreurs mêlées) et la range dans Execution.lignes : la page peut
les relire à tout moment depuis son propre fil (list.append est atomique, on ne fait que lire ou ajouter à la fin).
REGISTRE garde la dernière exécution de chaque tâche, de quoi la retrouver quand l'onglet est rouvert.
"""

import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

CODE_INTERRUPTION = 130


@dataclass
class Execution:
    identifiant: str
    commande: list
    lignes: list = field(default_factory=list)
    code: Optional[int] = None
    etat: str = "en cours"                  # puis « terminée », « échec » ou « interrompue »
    demarre: float = field(default_factory=time.time)
    processus: object = field(default=None, repr=False)
    arret_demande: bool = False
    fini: threading.Event = field(default_factory=threading.Event, repr=False)


REGISTRE: dict = {}


def en_cours():
    return [ex for ex in list(REGISTRE.values()) if ex.etat == "en cours"]


def derniere(identifiant):
    return REGISTRE.get(identifiant)


def _etat_final(ex):
    if ex.arret_demande or ex.code == CODE_INTERRUPTION:
        return "interrompue"
    return "terminée" if ex.code == 0 else "échec"


def _appeler(ex, rappel, *args):
    """Un rappel de la page qui lève ne doit pas tuer la lecture : l'erreur est notée dans la sortie."""
    if rappel is None:
        return
    try:
        rappel(*args)
    except Exception as e:
        ex.lignes.append(f"[interface] erreur dans un rappel : {e}")


def _ligne(ex, octets, sur_ligne):
    texte = octets.rstrip(b"\r").decode("utf-8", errors="replace")
    ex.lignes.append(texte)
    _appeler(ex, sur_ligne, texte)


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
        ex.lignes.append(f"[interface] lecture interrompue : {e}")
    finally:
        ex.code = ex.processus.wait()
        ex.etat = _etat_final(ex)
        try:
            _appeler(ex, sur_fin, ex)
        finally:
            ex.fini.set()


def demarrer(identifiant, commande, cwd, env, sur_ligne: Optional[Callable] = None,
             sur_fin: Optional[Callable] = None, Popen=subprocess.Popen):
    """Lance la commande, enregistre l'exécution dans REGISTRE et rend la main ; OSError si le lancement échoue.

    L'entrée standard est fermée (DEVNULL) : un script interactif qui appelle input() échoue au lieu d'attendre
    une saisie que la page ne peut pas fournir."""
    processus = Popen(commande, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                      stderr=subprocess.STDOUT, bufsize=0)
    ex = Execution(identifiant, list(commande), processus=processus)
    REGISTRE[identifiant] = ex
    threading.Thread(target=_lire, args=(ex, sur_ligne, sur_fin), daemon=True).start()
    return ex


def arreter(ex, lancer=subprocess.run):
    """Arrête le processus et ses descendants (taskkill /T /F sous Windows : un .ps1 lance d'autres programmes)."""
    ex.arret_demande = True
    if sys.platform == "win32":
        lancer(["taskkill", "/T", "/F", "/PID", str(ex.processus.pid)], capture_output=True)
    else:
        ex.processus.terminate()
    if ex.processus.poll() is None and sys.platform == "win32":
        ex.processus.kill()                 # repli si taskkill n'a pas abouti
