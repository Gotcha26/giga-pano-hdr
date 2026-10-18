"""Couleurs ANSI et éléments d'interface texte, avec détection du terminal et repli sans couleur."""

import os
import sys


class Couleurs:
    """Codes ANSI (chaînes vides si les couleurs sont désactivées) et petits formateurs.

    forcer=True active les couleurs, forcer=False les désactive ; None (défaut) : NO_COLOR les désactive,
    FORCE_COLOR les active, sinon elles suivent le fait que stdout soit un terminal.
    """

    def __init__(self, forcer=None):
        if forcer is None:
            if os.environ.get("NO_COLOR"):
                forcer = False
            elif os.environ.get("FORCE_COLOR"):
                forcer = True
            else:
                forcer = bool(getattr(sys.stdout, "isatty", lambda: False)())
        self.actives = forcer
        if forcer and os.name == "nt":
            self._activer_vt_windows()
        code = (lambda n: f"\033[{n}m") if forcer else (lambda n: "")
        self.RESET, self.BOLD, self.DIM = code(0), code(1), code(2)
        self.ROUGE, self.VERT, self.JAUNE = code(91), code(92), code(93)
        self.BLEU, self.CYAN, self.BLANC = code(94), code(96), code(97)
        self.OK, self.ERREUR, self.ATTENTION, self.INFO = self.VERT, self.ROUGE, self.JAUNE, self.BLEU
        self.VALEUR, self.CLE, self.PROMPT = self.CYAN, self.BLANC, self.JAUNE
        self.TITRE = self.BLANC + self.BOLD
        self.ENTETE = self.CYAN + self.BOLD

    @staticmethod
    def _activer_vt_windows():
        try:
            import ctypes
            noyau = ctypes.windll.kernel32
            handle = noyau.GetStdHandle(-11)
            mode = ctypes.c_uint()
            if noyau.GetConsoleMode(handle, ctypes.byref(mode)):
                noyau.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:  # pas une console Windows classique : on continue sans
            pass

    # Préfixés
    def succes(self, texte):
        return f"{self.OK}[OK]{self.RESET} {texte}"

    def erreur(self, texte):
        return f"{self.ERREUR}[ERREUR]{self.RESET} {texte}"

    def attention(self, texte):
        return f"{self.ATTENTION}[ATTENTION]{self.RESET} {texte}"

    def info(self, texte):
        return f"{self.INFO}[INFO]{self.RESET} {texte}"

    # En ligne
    def titre(self, texte):
        return f"{self.TITRE}{texte}{self.RESET}"

    def valeur(self, texte):
        return f"{self.VALEUR}{texte}{self.RESET}"

    def prompt(self, texte):
        return f"{self.PROMPT}{texte}{self.RESET}"

    # Éléments d'interface
    def separateur(self, car="-", largeur=60):
        return f"{self.DIM}{car * largeur}{self.RESET}"

    def boite(self, titre, largeur=70):
        bord = "=" * largeur
        return f"{bord}\n{self.ENTETE}{titre.center(largeur)}{self.RESET}\n{bord}"

    def ligne_config(self, cle, valeur, largeur_cle=25):
        return f"  {self.CLE}{cle.ljust(largeur_cle)}{self.RESET} : {self.VALEUR}{valeur}{self.RESET}"


def preparer_console():
    """Sortie en UTF-8 avec remplacement : les menus portent des accents et des flèches, et une console
    Windows en cp1252 planterait sur le premier caractère hors table."""
    for flux in (sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            try:
                flux.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def effacer_ecran():
    """Efface le terminal ; ne fait rien si stdout n'est pas un terminal (tests, redirection)."""
    if getattr(sys.stdout, "isatty", lambda: False)():
        os.system("cls" if os.name == "nt" else "clear")
