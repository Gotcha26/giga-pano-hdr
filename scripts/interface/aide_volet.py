"""Volet d'aide de la page web (à droite) : la section du guide de la tâche choisie et le mode d'emploi du script.

Fonctions pures en haut (liens du guide rendus absolus, échappement), construction NiceGUI en bas.
"""

from . import aide


# ---------------------------------------------------------------- fonctions pures

def liens_absolus(markdown):
    """Les liens internes du guide (« (#ancre) ») deviennent des liens vers le guide sur GitHub."""
    return markdown.replace("](#", "](" + aide.URL_GUIDE + "#")


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
