"""Bas de la zone centrale de la page web : le journal d'exécution, les fichiers produits et leurs aperçus.

Fonctions pures en haut (dossier des fichiers produits, vips, tailles), construction NiceGUI en bas. Le journal
(ui.log) est posé par la zone de la tâche ; `rafraichir_suivi` le rebranche sur la dernière exécution de la tâche
affichée et y pousse les lignes nouvelles, depuis le minuteur de l'onglet.
"""

import os
import time

from pilotage import lancer

from . import apercus, execution, formulaire

VIPS_ABSENT = "libvips absent : voir Configuration"
LIMITE_IMAGES = 200
ZOOM_MAX = 16
PAS_MOLETTE = 1.25
AIDE_ZOOM = "molette : zoom · clic : ×2 · Maj+clic : ÷2"
# position visée dans l'image (fractions de sa largeur et de sa hauteur) et sens de la molette ; le défilement
# natif est empêché pour que la molette ne fasse que zoomer
JS_MOLETTE = ("(e) => { e.preventDefault(); const i = e.currentTarget.querySelector('img');"
              " if (!i) return; const r = i.getBoundingClientRect();"
              " const borne = (v) => Math.min(Math.max(v, 0), 1);"
              " emit({avant: e.deltaY < 0, fx: borne((e.clientX - r.left) / r.width),"
              " fy: borne((e.clientY - r.top) / r.height)}); }")


# ---------------------------------------------------------------- fonctions pures

def dossier_sortie(t, liste_champs, valeurs, exclus=()):
    """Dossier montré par « Fichiers produits » : l'argument `t.sortie` s'il est renseigné, sinon le dossier du
    premier champ fichier ou dossier renseigné hors `exclus` (les chemins d'outils) ; "" faute de mieux."""
    def dossier(chemin, genre):
        if genre == "dossier" or os.path.isdir(chemin):
            return chemin
        return os.path.dirname(chemin)
    genres = {c.arg.nom: c.genre for c in liste_champs}
    if t.sortie and valeurs.get(t.sortie):
        return dossier(str(valeurs[t.sortie]), genres.get(t.sortie, "dossier"))
    for c in liste_champs:
        v = valeurs.get(c.arg.nom)
        if c.genre in ("fichier", "dossier") and c.arg.nom not in exclus and isinstance(v, str) and v:
            return dossier(v, c.genre)
    return ""


def chemin_vips(ctx):
    """vips.exe configuré sur le poste, sinon détecté ; None s'il manque."""
    configure = ctx.poste.outils.get("vips")
    if configure:
        return configure
    e = lancer.etat(ctx, "vips")
    return e.chemin if e and e.present else None


def borner_zoom(niveau):
    """Niveau de zoom ramené entre 1 (image ajustée à la largeur) et ZOOM_MAX."""
    return min(max(niveau, 1), ZOOM_MAX)


def niveau_molette(niveau, avant):
    """Niveau après un cran de molette : ×PAS_MOLETTE vers l'avant, ÷PAS_MOLETTE vers l'arrière, borné."""
    return borner_zoom(niveau * PAS_MOLETTE if avant else niveau / PAS_MOLETTE)


def taille_lisible(octets):
    for unite in ("o", "Ko", "Mo", "Go"):
        if octets < 1024 or unite == "Go":
            return f"{octets:.0f} {unite}" if unite == "o" else f"{octets:.1f} {unite}"
        octets /= 1024


# ---------------------------------------------------------------- partie NiceGUI

def construire(etat):
    """Pose la zone des fichiers produits dans `etat.apercus` et le suivi du journal dans `etat.suivi`."""
    from nicegui import run, ui

    ctx = etat.ctx

    def choisir_dossier(v):
        etat.dossier_apercus = v or None
        apercus_zone.refresh()

    async def autre_dossier(depart):
        choisi = await formulaire.parcourir("dossier", depart)
        if choisi:
            choisir_dossier(choisi)

    def vider():
        n = apercus.vider_cache()
        ui.notify(f"{n} aperçu(s) supprimé(s) du cache")

    async def voir(image):
        vips = chemin_vips(ctx)
        if not vips:
            ui.notify(VIPS_ABSENT, type="warning")
            return
        attente = ui.notification(f"Aperçu de {image.chemin.name}…", spinner=True, timeout=None)
        try:
            jpeg = await run.io_bound(apercus.apercu, image.chemin, vips)
        except (RuntimeError, OSError) as e:
            ui.notify(f"Aperçu impossible : {e}", type="negative", multi_line=True)
            return
        finally:
            attente.dismiss()
        visionneuse(image.chemin.name, jpeg)

    @ui.refreshable
    def apercus_zone():
        t = etat.tache
        calcule = (dossier_sortie(t, etat.champs, formulaire.valeurs(etat.elements),
                                  formulaire.arguments_d_outil(etat.arguments))
                   if etat.elements else "")
        dossier = etat.dossier_apercus or calcule
        with ui.card().classes("w-full"):
            ui.label("Fichiers produits").classes("font-bold")
            with ui.row().classes("w-full items-center no-wrap gap-2"):
                saisie = ui.input("Dossier", value=dossier).classes("grow")
                saisie.on("keydown.enter", lambda: choisir_dossier(saisie.value))
                ui.button("Autre dossier…", on_click=lambda: autre_dossier(saisie.value)).props("flat no-caps")
                ui.button("Actualiser", on_click=lambda: choisir_dossier(saisie.value)).props("flat no-caps")
                ui.button("Vider le cache", on_click=vider).props("flat no-caps")
            if not chemin_vips(ctx):
                ui.label(VIPS_ABSENT).classes("text-amber-700")
            images = apercus.lister_images(dossier)
            if not dossier:
                ui.label("Aucun dossier de sortie renseigné.").classes("text-gray-600")
            elif not images:
                ui.label("Aucune image (.tif, .jpg, .png) dans ce dossier.").classes("text-gray-600")
            with ui.list().props("dense separator").classes("w-full"):
                for image in images[:LIMITE_IMAGES]:
                    with ui.item(on_click=lambda i=image: voir(i)):
                        with ui.item_section():
                            ui.item_label(image.chemin.name)
                        with ui.item_section().props("side"):
                            ui.item_label(f"{taille_lisible(image.taille)} · "
                                          f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(image.modifie))}")
            if len(images) > LIMITE_IMAGES:
                ui.label(f"… et {len(images) - LIMITE_IMAGES} autres").classes("text-gray-600")

    def visionneuse(nom, jpeg):
        """Aperçu en grand ; molette : zoom ×1,25 sur le point visé ; clic : zoom ×2 centré sur le point,
        Maj+clic : dézoom ; barres de défilement pour se déplacer."""
        zoom = {"niveau": 1, "largeur": 1, "hauteur": 1}
        with ui.dialog().props("maximized") as dialogue, ui.card().classes("w-full h-full p-2"):
            with ui.row().classes("w-full items-center gap-2"):
                ui.label(nom).classes("font-bold")
                ui.space()
                ui.label(AIDE_ZOOM).classes("text-xs text-gray-500")
                ui.button("−", on_click=lambda: zoomer(zoom["niveau"] / 2)).props("flat")
                ui.button("+", on_click=lambda: zoomer(zoom["niveau"] * 2)).props("flat")
                ui.button("Ajuster", on_click=lambda: zoomer(1)).props("flat no-caps")
                ui.button("Fermer", on_click=dialogue.close).props("flat no-caps")
            with ui.element("div").classes("w-full grow overflow-auto") as cadre:
                image = ui.interactive_image(jpeg, events=["click"]).style("width: 100%")

        def zoomer(niveau, fx=0.5, fy=0.5):
            zoom["niveau"] = borner_zoom(niveau)
            image.style(f"width: {zoom['niveau'] * 100}%")
            ui.run_javascript(
                f"setTimeout(() => {{ const c = document.getElementById('c{cadre.id}');"
                f" c.scrollLeft = {fx} * c.scrollWidth - c.clientWidth / 2;"
                f" c.scrollTop = {fy} * c.scrollHeight - c.clientHeight / 2; }}, 50)")

        def taille(e):
            zoom["largeur"], zoom["hauteur"] = e.args.get("width") or 1, e.args.get("height") or 1

        def clic(e):
            facteur = 0.5 if e.shift else 2
            zoomer(zoom["niveau"] * facteur, e.image_x / zoom["largeur"], e.image_y / zoom["hauteur"])

        def molette(e):
            a = e.args if isinstance(e.args, dict) else {}
            if not a:
                return
            zoomer(niveau_molette(zoom["niveau"], a.get("avant", True)), a.get("fx", 0.5), a.get("fy", 0.5))

        image.on("loaded", taille)
        image.on_mouse(clic)
        # le navigateur ne défile pas (preventDefault) : la molette zoome sur le point visé de l'image
        cadre.on("wheel", molette, throttle=0.1, js_handler=JS_MOLETTE)
        dialogue.on("hide", dialogue.delete)
        dialogue.open()

    def rafraichir_suivi():
        """Rebranche le journal sur la dernière exécution de la tâche affichée, et pousse ce qui manque."""
        t, journal = etat.tache, etat.journal
        if journal is None or t is None or not formulaire.a_un_formulaire(t):
            return
        ex = execution.derniere(t.identifiant)
        if ex is not etat.ex_vue:
            journal.clear()
            etat.ex_vue, etat.lus, etat.etat_vu = ex, 0, ""
        if ex is None:
            return
        nouvelles = ex.lignes[etat.lus:]
        for ligne in nouvelles:
            journal.push(ligne)
        etat.lus += len(nouvelles)
        if ex.etat != etat.etat_vu:
            etat.etat_vu = ex.etat
            etat.boutons.refresh()

    etat.apercus, etat.suivi = apercus_zone, rafraichir_suivi
    return apercus_zone
