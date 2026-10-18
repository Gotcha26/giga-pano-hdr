"""Menus déclaratifs : entrées (tête, sous-titre, effet, action, disponibilité), rendu numéroté, boucle, saisies.

Règles : les numéros ne vont qu'aux entrées disponibles qui ont une action ; ils sont cadrés à droite sur la
largeur du plus grand numéro affiché ; les têtes d'une même section sont alignées ; l'effet est déclaré en fin
de libellé ([écrit — cible] ou [lecture seule]) ; 0 revient, x annule une saisie, ENTRÉE garde la valeur.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union

from .couleurs import effacer_ecran


@dataclass
class Entree:
    tete: Union[str, Callable[[Any], str]]
    sous_titre: str = ""
    effet: Optional[str] = None            # None = lecture seule ; sinon la cible écrite
    action: Optional[Callable[[Any], Any]] = None   # None = entrée informative (grisée, jamais numérotée)
    disponible: Callable[[Any], bool] = field(default=lambda ctx: True)
    raison: Union[str, Callable[[Any], str]] = ""   # texte, ou callable(ctx) -> texte (raison vivante)
    masquer: bool = False
    section: str = ""

    def tete_texte(self, ctx):
        return self.tete(ctx) if callable(self.tete) else self.tete

    def active(self, ctx):
        return self.action is not None and self.disponible(ctx)

    def visible(self, ctx):
        return not (self.masquer and not self.disponible(ctx))


def libelles(entrees, ctx):
    """Libellés alignés par section : tête padée, ' — ' sous-titre, puis l'effet (si l'entrée a une action)."""
    largeurs = {}
    for e in entrees:
        largeurs[e.section] = max(largeurs.get(e.section, 0), len(e.tete_texte(ctx)))
    resultat = []
    for e in entrees:
        texte = e.tete_texte(ctx).ljust(largeurs[e.section])
        if e.sous_titre:
            texte += f" — {e.sous_titre}"
        if e.action is not None:
            texte += f"  [écrit — {e.effet}]" if e.effet else "  [lecture seule]"
        resultat.append(texte)
    return resultat


def numeroter(entrees, ctx):
    numeros, compteur = [], 0
    for e in entrees:
        if e.active(ctx):
            compteur += 1
            numeros.append(compteur)
        else:
            numeros.append(None)
    return numeros


def rendre(entrees, ctx, c, ecrire=print):
    """Affiche le menu par sections ; retourne {numéro (str): entrée}."""
    numeros = numeroter(entrees, ctx)
    textes = libelles(entrees, ctx)
    largeur = len(str(max((n for n in numeros if n), default=1)))
    table = {}
    section_courante = None
    for e, n, texte in zip(entrees, numeros, textes):
        if not e.visible(ctx):
            continue
        if e.section and e.section != section_courante:
            if section_courante is not None:
                ecrire("")
            ecrire(c.titre(e.section))
            ecrire(c.separateur())
            section_courante = e.section
        if n is not None:
            ecrire(f"  {c.JAUNE}{str(n).rjust(largeur)}{c.RESET}. {texte}")
            table[str(n)] = e
        else:
            texte_raison = e.raison(ctx) if callable(e.raison) else e.raison
            raison = f"  [{texte_raison}]" if texte_raison else ""
            ecrire(f"  {c.DIM}{'–'.rjust(largeur)}. {texte}{raison}{c.RESET}")
    ecrire("")
    ecrire(f"  {c.JAUNE}{'0'.rjust(largeur)}{c.RESET}. {c.DIM}Retour{c.RESET}")
    return table


def pause(c, lire=input):
    try:
        lire(f"{c.DIM}Appuyez sur Entrée...{c.RESET}")
    except StopIteration:
        pass


def demander(invite, c, defaut=None, lire=input):
    """Saisie de texte : x annule (None), vide garde le défaut, sinon la valeur sans espaces autour."""
    suffixe = f" (ENTRÉE pour garder « {defaut} », x pour annuler)" if defaut not in (None, "") else " (x pour annuler)"
    saisie = lire(c.prompt(f"{invite}{suffixe} : ")).strip()
    if saisie.lower() == "x":
        return None
    return defaut if saisie == "" else saisie


def confirmer(question, c, defaut_oui, lire=input):
    choix = "[O/n]" if defaut_oui else "[o/N]"
    saisie = lire(c.prompt(f"{question} {choix} : ")).strip().lower()
    if saisie == "":
        return defaut_oui
    return saisie in ("o", "oui", "y", "yes")


def boucle(titre, entrees, ctx, c, entete=None, lire=input, ecrire=print, effacer=effacer_ecran):
    """Affiche, lit un choix, exécute l'action, recommence ; 0 revient. Fin des saisies (StopIteration) : retour."""
    while True:
        effacer()
        if entete:
            entete(ctx)
        else:
            ecrire(c.boite(titre))
        ecrire("")
        table = rendre(entrees, ctx, c, ecrire)
        try:
            choix = lire(c.prompt(f"\n  Votre choix (0-{len(table)}) : ")).strip()
        except StopIteration:
            return
        if choix == "0":
            return
        if choix in table:
            table[choix].action(ctx)
            pause(c, lire)
        else:
            ecrire(c.erreur(f'Choix invalide : "{choix}"'))
            pause(c, lire)
