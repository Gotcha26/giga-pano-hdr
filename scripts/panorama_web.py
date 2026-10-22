"""Interface web du lanceur : même catalogue de tâches que panorama.py, dans le navigateur (NiceGUI).

CONTEXTE
    Second point d'entrée (python panorama_web.py), à côté du lanceur console. Il sert une page locale
    (127.0.0.1, port libre choisi au démarrage) construite sur le paquet pilotage/ ; la façade web vit dans
    interface/. Seule cette façade dépend de NiceGUI : le lanceur console et les scripts restent sans
    dépendance hors bibliothèque standard.

MODE OPÉRATOIRE
    1. vérifie que NiceGUI est installé, sinon indique « pip install nicegui » et sort avec le code 1 ;
    2. lit la configuration du poste (%LOCALAPPDATA%\\giga-pano-hdr\\config.json) et le panorama courant
       ($T\\panorama.json) ;
    3. détecte les outils (Hugin, multiblend, libvips, ExifTool, Python, Pillow, PowerShell) ;
    4. choisit un port libre et démarre le serveur ; le navigateur s'ouvre tout seul.

ENTRÉES
    Aucune obligatoire : tout se fait dans la page.
    --sans-navigateur (ou la variable GIGA_PANO_SANS_NAVIGATEUR=1) : démarre le serveur sans ouvrir le
    navigateur, pour un test automatisé ; l'adresse s'affiche dans la console.

SORTIES
    Celles des scripts lancés depuis la page. Le point d'entrée n'écrit rien lui-même.

EXEMPLE
    python panorama_web.py
    python panorama_web.py --sans-navigateur
"""

import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pilotage import config, lancer, outils  # noqa: E402
from pilotage.couleurs import Couleurs  # noqa: E402

SANS_NAVIGATEUR = "GIGA_PANO_SANS_NAVIGATEUR"


def verifier_nicegui():
    """None si NiceGUI s'importe, sinon le message à afficher."""
    try:
        import nicegui  # noqa: F401
    except ImportError:
        return "NiceGUI est absent : pip install nicegui"
    return None


def port_libre():
    """Un port TCP libre sur 127.0.0.1, choisi par le système."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def ouvrir_navigateur(argv=None, environ=None):
    """Faux avec --sans-navigateur ou GIGA_PANO_SANS_NAVIGATEUR=1 (serveur seul, pour un test automatisé)."""
    argv = sys.argv[1:] if argv is None else argv
    environ = os.environ if environ is None else environ
    return "--sans-navigateur" not in argv and environ.get(SANS_NAVIGATEUR) != "1"


def main(argv=None, ecrire=print):
    message = verifier_nicegui()
    if message:
        ecrire(message)
        return 1
    poste = config.charger_poste()
    ctx = lancer.Contexte(poste=poste, panorama=config.panorama_courant(poste),
                          etats=outils.detecter_tous(poste.outils), c=Couleurs())
    from interface.page import demarrer
    demarrer(ctx, port_libre(), ouvrir=ouvrir_navigateur(argv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
