"""Volet d'aide de la page web (à droite) : la section du guide de la tâche choisie et le mode d'emploi du script.

Fonctions pures en haut (liens du guide rendus absolus, échappement), construction NiceGUI en bas.
"""

import posixpath
import re

from . import aide

DEPOT_BLOB = aide.URL_GUIDE.rsplit("/docs/", 1)[0]          # https://github.com/<dépôt>/blob/main
DEPOT_RAW = DEPOT_BLOB.replace("/blob/", "/raw/", 1)        # images : le fichier lui-même, pas sa page
DOSSIER_GUIDE = "docs"                                       # les liens relatifs du guide partent de docs/

# [texte](cible) ou ![texte](cible "titre") ; la cible s'arrête au premier blanc ou à la parenthèse fermante
RE_LIEN = re.compile(r'(!?\[[^\]]*\])\(([^)\s]+)((?:\s+"[^"]*")?)\)')
RE_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")       # http:, https:, mailto:…


# ---------------------------------------------------------------- fonctions pures

def _absolu(image, cible):
    """URL GitHub d'une cible relative au guide ; None si elle n'est pas à réécrire (absolue, hors du dépôt)."""
    if cible.startswith("#"):
        return None if image else aide.URL_GUIDE + cible
    if RE_SCHEMA.match(cible) or cible.startswith("/"):
        return None
    chemin, diese, ancre = cible.partition("#")
    normalise = posixpath.normpath(posixpath.join(DOSSIER_GUIDE, chemin))
    if normalise == ".." or normalise.startswith("../"):
        return None
    return f"{DEPOT_RAW if image else DEPOT_BLOB}/{normalise}{diese}{ancre}"


def liens_absolus(markdown):
    """Les liens du guide, affiché hors de GitHub, deviennent absolus : une ancre (« (#0d--dossiers) ») vise le
    guide sur GitHub ; un lien relatif (« ../scripts/INDEX.md », « ./AUTRE.md », « AUTRE.md#x ») vise le fichier
    du dépôt (…/blob/main/<chemin depuis docs/>) ; une image relative, son contenu (…/raw/main/…). Les liens
    absolus (http:, mailto:…) et ceux qui sortiraient du dépôt restent tels quels."""
    def remplacer(m):
        texte, cible, titre_lien = m.groups()
        url = _absolu(texte.startswith("!"), cible)
        return m.group(0) if url is None else f"{texte}({url}{titre_lien})"
    return RE_LIEN.sub(remplacer, markdown)


def echapper(texte):
    return texte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- partie NiceGUI

def construire(etat):
    """Pose la fonction rafraîchissable du volet dans `etat.aide`."""
    from nicegui import ui

    ctx = etat.ctx

    @ui.refreshable
    def volet_aide():
        t = etat.tache
        if t is None:
            ui.label("L'aide de la tâche choisie s'affiche ici.").classes("text-gray-600")
            ui.link("Le guide", aide.URL_GUIDE, new_tab=True)
            return
        section = aide.section_du_guide(t.repere) if t.repere else None
        if section:
            ui.markdown(liens_absolus(section), extras=["fenced-code-blocks", "tables", "code-friendly"]).classes(
                "text-sm w-full [&_h3]:text-lg [&_h4]:text-base [&_pre]:whitespace-pre-wrap [&_pre]:break-all "
                "[&_table]:block [&_table]:overflow-x-auto")
        else:
            ui.label("Section introuvable dans le guide.").classes("text-gray-600")
            ui.link("Ouvrir le guide", aide.lien_guide(t.repere) if t.repere else aide.URL_GUIDE, new_tab=True)
        if t.script:
            mode = aide.mode_d_emploi(ctx.scripts / t.script)
            with ui.expansion("Mode d'emploi du script").classes("w-full"):
                ui.html(f"<pre class='text-xs whitespace-pre-wrap'>{echapper(mode)}</pre>", sanitize=False)

    etat.aide = volet_aide
    return volet_aide
