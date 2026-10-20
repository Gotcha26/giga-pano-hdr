"""Ouvre les pyramides de tuiles dans une page web locale, HDR et pleine résolution superposés, pour les contrôler.

CONTEXTE
    Étape 7B : le contrôle se fait dans une visionneuse, à tous les zooms, comme le verra le visiteur. Une page
    OpenSeadragon doit être servie en HTTP (file:// bloque le chargement des tuiles) : ce script s'en charge,
    sans rien copier ni écrire.

MODE OPÉRATOIRE
    Sert sur 127.0.0.1 (ce poste seulement) la page de scripts\\visionneuse\\ (OpenSeadragon 6.1.1 embarqué) et les
    dossiers des deux .dzi, sous /hdr/ et /complet/ ; ouvre le navigateur sur la page, puis attend Entrée (ou Ctrl+C)
    pour arrêter le serveur. La pleine résolution est posée sur le HDR :
    - sources cadrées ensemble (7C) : même cadre, --box inutile ;
    - sources non recadrées : --box x,y,largeur donne le cadre de la pleine résolution dans le HDR, en largeurs du
      HDR (voir « Position des deux sources » dans le guide).
    Avec --fondu auto (défaut), la pleine résolution apparaît avec le zoom ; --fondu curseur donne un curseur.

ENTRÉES
    HDR                pyramide du HDR (.dzi), ou la seule pyramide à regarder
    COMPLET            pyramide de la pleine résolution (.dzi), facultative
    --box X,Y,L        cadre de la pleine résolution dans le HDR, en largeurs du HDR (sans : même cadre)
    --fondu MODE       auto (défaut) ou curseur
    --port N           port local (défaut : un port libre)
    --sans-navigateur  n'ouvre pas le navigateur (l'adresse est affichée)

SORTIES
    Console seulement : l'adresse de la page. Rien n'est écrit ni modifié.

EXEMPLE
    python controler_tuiles.py "$P\\7_tuiles\\hdr_webp\\hdr.dzi" "$P\\7_tuiles\\complet_webp\\complet.dzi" --box 0.016135,0.012329,0.983864

Usage : python controler_tuiles.py HDR.dzi [COMPLET.dzi] [--box X,Y,L] [--fondu auto|curseur] [--port N] [--sans-navigateur]
"""
import argparse
import sys
import threading
import urllib.parse
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pilotage.arguments import Arg, piloter, terminal_interactif

ARGUMENTS = [
    Arg("HDR", "Pyramide du HDR (.dzi), ou la seule à regarder", type="chemin", obligatoire=True),
    Arg("COMPLET", "Pyramide de la pleine résolution (.dzi)", type="chemin", obligatoire=False),
    Arg("--box", "Cadre X,Y,L de la pleine résolution dans le HDR (vide : sources cadrées ensemble)"),
    Arg("--fondu", "auto (avec le zoom) ou curseur", defaut="auto"),
    Arg("--port", "Port local (vide : un port libre)", type="entier"),
    Arg("--sans-navigateur", "N'ouvre pas le navigateur", type="drapeau"),
]

VISIONNEUSE = Path(__file__).resolve().parent / "visionneuse"


class Gestionnaire(SimpleHTTPRequestHandler):
    """Sert la page de VISIONNEUSE, et chaque dossier de `racines` sous /<clé>/ ; rien hors de ces dossiers."""
    racines = {}
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".dzi": "application/xml", ".webp": "image/webp"}

    def translate_path(self, path):
        chemin = urllib.parse.unquote(urllib.parse.urlsplit(path).path).replace("\\", "/")
        parties = [p for p in chemin.split("/") if p not in ("", ".", "..") and ":" not in p]
        if parties and parties[0] in self.racines:
            return str(Path(self.racines[parties[0]], *parties[1:]))
        return str(Path(VISIONNEUSE, *parties))

    def log_message(self, *args):       # une ligne par tuile noierait la console
        pass


def lire_box(texte):
    """(x, y, largeur) depuis « x,y,largeur » ; None si vide ; ValueError si mal formé."""
    if not texte:
        return None
    valeurs = [float(v) for v in texte.split(",")]
    if len(valeurs) != 3:
        raise ValueError(texte)
    return valeurs


def adresse(port, hdr, complet=None, box=None, fondu="auto"):
    params = {"hdr": f"hdr/{Path(hdr).name}"}
    if complet:
        params["full"] = f"complet/{Path(complet).name}"
        if box:
            params["box"] = ",".join(f"{v:g}" for v in box)
        if fondu == "auto":
            params["fondu"] = "auto"
    return f"http://127.0.0.1:{port}/?" + urllib.parse.urlencode(params, safe="/,")


def serveur(hdr, complet=None, port=0):
    """Serveur prêt à servir (pas encore lancé) ; son port réel est serveur.server_address[1]."""
    racines = {"hdr": str(Path(hdr).resolve().parent)}
    if complet:
        racines["complet"] = str(Path(complet).resolve().parent)
    gestionnaire = type("GestionnaireTuiles", (Gestionnaire,), {"racines": racines})
    return ThreadingHTTPServer(("127.0.0.1", port), gestionnaire)


def main():
    piloter(__doc__, ARGUMENTS, globals_=globals())
    ap = argparse.ArgumentParser()
    ap.add_argument("hdr")
    ap.add_argument("complet", nargs="?")
    ap.add_argument("--box")
    ap.add_argument("--fondu", choices=("auto", "curseur"), default="auto")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--sans-navigateur", action="store_true")
    args = ap.parse_args()

    for chemin in filter(None, (args.hdr, args.complet)):
        if Path(chemin).suffix.lower() != ".dzi" or not Path(chemin).is_file():
            sys.exit(f"pyramide introuvable (fichier .dzi attendu) : {chemin}")
        if not Path(chemin).with_name(Path(chemin).stem + "_files").is_dir():
            sys.exit(f"dossier des tuiles absent à côté de {chemin} ({Path(chemin).stem}_files)")
    try:
        box = lire_box(args.box)
    except ValueError:
        sys.exit(f"--box attend trois nombres X,Y,L séparés par des virgules, reçu « {args.box} »")

    srv = serveur(args.hdr, args.complet, args.port)
    url = adresse(srv.server_address[1], args.hdr, args.complet, box, args.fondu)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"Page de contrôle : {url}")
    if args.complet and not box:
        print("  Sans --box : même cadre supposé (sources cadrées ensemble en 7C).")
    if not args.sans_navigateur:
        webbrowser.open(url)
    try:
        if terminal_interactif():       # isatty() seul se trompe sur une entrée redirigée depuis NUL
            input("Entrée pour arrêter le serveur... ")
        else:
            print("Ctrl+C pour arrêter le serveur.")
            threading.Event().wait()
    except (KeyboardInterrupt, EOFError):
        pass
    srv.shutdown()
    print("Serveur arrêté.")


if __name__ == "__main__":
    main()
