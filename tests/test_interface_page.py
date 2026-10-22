"""Tests de interface.page : fonctions pures de la page (sans serveur) et fumée de la page avec le User de NiceGUI."""

import asyncio
import importlib.util
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from pilotage import catalogue, config, lancer, outils  # noqa: E402
from pilotage.couleurs import Couleurs  # noqa: E402

NICEGUI = importlib.util.find_spec("nicegui") is not None


def _tache(identifiant):
    return next(t for t in catalogue.TACHES if t.identifiant == identifiant)


def _contexte(etats=(), poste=None, panorama=None):
    return lancer.Contexte(poste=poste or config.Poste(), panorama=panorama, etats=list(etats),
                           c=Couleurs(forcer=False), scripts=SCRIPTS)


def _etat_outil(cle, chemin):
    outil = next(o for o in outils.OUTILS if o.cle == cle)
    return outils.Etat(outil, chemin, "1.0" if chemin else None)


class TestImport(unittest.TestCase):
    def test_page_expose_demarrer_si_nicegui(self):
        if not NICEGUI:
            self.skipTest("nicegui absent")
        from interface import page
        self.assertTrue(callable(page.demarrer))
        self.assertTrue(callable(page.application))

    def test_panorama_web_s_importe_toujours(self):
        import panorama_web
        self.assertTrue(callable(panorama_web.main))


class TestColonne(unittest.TestCase):
    def setUp(self):
        from interface import page
        self.page = page

    def test_phases_0_a_7_puis_mesures(self):
        arbre = self.page.arborescence(titres={})
        self.assertEqual([t for t, _ in arbre], [f"Phase {n}" for n in range(8)] + ["Mesures et inspection"])
        tout = [t for _, taches in arbre for t in taches]
        self.assertEqual(len(tout), len(catalogue.TACHES))

    def test_titres_lus_dans_le_guide(self):
        titres = self.page.titres_phases()
        self.assertEqual(sorted(titres), list(range(8)))
        self.assertTrue(titres[4].startswith("Phase 4 — "))

    def test_4a_dans_la_phase_4_triee_par_repere(self):
        arbre = dict(self.page.arborescence(titres={}))
        reperes = [t.repere for t in arbre["Phase 4"]]
        self.assertIn("4A", reperes)
        self.assertEqual(reperes, sorted(reperes, key=catalogue.cle_tri))

    def test_libelle_et_titre_sans_repere_double(self):
        geste = _tache("3B/geste")
        self.assertEqual(self.page.libelle(geste), "3B Points de contrôle")
        self.assertEqual(self.page.titre(geste), "3B — Points de contrôle")
        rendre = _tache("4A/rendre_projet.ps1")
        self.assertEqual(self.page.titre(rendre), "4A — Rendre un projet (nona puis fusion)")
        tiff = _tache("2/tiffinfo.py")
        self.assertEqual(self.page.libelle(tiff), "Lire la taille d'un TIFF")


class TestEnTete(unittest.TestCase):
    def setUp(self):
        from interface import page
        self.page = page
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.P = Path(self.tmp.name) / "P"
        (self.P / "3_optimisation").mkdir(parents=True)
        self.p = config.Panorama(T=self.tmp.name, P=str(self.P), lignes=3, colonnes=12)

    def test_grille(self):
        self.assertEqual(self.page.grille(self.p), "3×12×?")
        self.assertIsNone(self.page.grille(None))

    def test_maitre(self):
        self.assertFalse(self.page.maitre_present(self.p))
        self.p.maitre = r"3_optimisation\pano_grille_opt.pto"
        self.assertFalse(self.page.maitre_present(self.p))
        (self.P / "3_optimisation" / "pano_grille_opt.pto").write_text("", encoding="utf-8")
        self.assertTrue(self.page.maitre_present(self.p))

    def test_coches_dans_l_ordre_du_resume(self):
        etats = [_etat_outil("vips", None), _etat_outil("hugin", "nona.exe"), _etat_outil("python", "py")]
        self.assertEqual(self.page.coches(etats), [("Hugin", True, "1.0"), ("libvips", False, None)])

    def test_options_panoramas_avec_le_courant(self):
        poste = config.Poste(panoramas=[r"D:\A"], courant=r"D:\B")
        self.assertEqual(self.page.options_panoramas(poste), {r"D:\A": "A", r"D:\B": "B"})
        homonymes = config.Poste(panoramas=[r"D:\1\pano", r"E:\2\pano"])
        self.assertEqual(self.page.options_panoramas(homonymes), {r"D:\1\pano": r"D:\1\pano", r"E:\2\pano": r"E:\2\pano"})

    def test_formulaire_perime_si_un_autre_onglet_change_de_panorama(self):
        config.enregistrer_panorama(self.p)
        ctx = _contexte(poste=config.Poste(panoramas=[r"D:\A", self.tmp.name], courant=r"D:\A"))
        onglet_a = self.page.Etat(ctx=ctx, T_vu=r"D:\A")
        self.assertFalse(self.page.formulaire_perime(onglet_a, ctx))
        self.page.changer_panorama(ctx, self.tmp.name, enregistrer=lambda poste: None)   # depuis l'onglet B
        self.assertTrue(self.page.formulaire_perime(onglet_a, ctx))

    def test_changer_panorama(self):
        config.enregistrer_panorama(self.p)
        poste = config.Poste(panoramas=[self.tmp.name])
        ctx = _contexte(poste=poste)
        ecrits = []
        p = self.page.changer_panorama(ctx, self.tmp.name, enregistrer=ecrits.append)
        self.assertEqual(ctx.poste.courant, self.tmp.name)
        self.assertEqual(ecrits, [poste])
        self.assertEqual(p.P, str(self.P))
        self.assertIs(ctx.panorama, p)


class TestTache(unittest.TestCase):
    def setUp(self):
        from interface import formulaire, page
        self.page, self.formulaire = page, formulaire

    def test_raisons_indisponible(self):
        t = _tache("4A/rendre_projet.ps1")
        ctx = _contexte([_etat_outil("hugin", "nona.exe"), _etat_outil("multiblend", None),
                         _etat_outil("pwsh", "pwsh.exe")])
        self.assertEqual(self.page.raisons_indisponible(ctx, t), ["multiblend absent"])
        ctx = _contexte([_etat_outil("hugin", "nona.exe"), _etat_outil("multiblend", "m.exe"),
                         _etat_outil("pwsh", "pwsh.exe")])
        self.assertEqual(self.page.raisons_indisponible(ctx, t), [])

    def test_dossier_sortie_argument_designe(self):
        t = _tache("4A/rendre_projet.ps1")
        ctx = _contexte()
        args, _, _ = self.formulaire.arguments_de(t, ctx)
        champs = self.formulaire.champs(t, args, None, ctx)
        valeurs = {c.arg.nom: c.valeur for c in champs}
        valeurs["-Sortie"] = r"D:\P\4_vue_centree\rendu"
        self.assertEqual(self.page.dossier_sortie(t, champs, valeurs), r"D:\P\4_vue_centree\rendu")

    def test_dossier_sortie_sinon_dossier_du_premier_fichier(self):
        t = _tache("2/tiffinfo.py")
        ctx = _contexte()
        args, _, _ = self.formulaire.arguments_de(t, ctx)
        champs = self.formulaire.champs(t, args, None, ctx)
        valeurs = {c.arg.nom: c.valeur for c in champs}
        self.assertEqual(self.page.dossier_sortie(t, champs, valeurs), "")
        fichier = next(c for c in champs if c.genre == "fichier")
        valeurs[fichier.arg.nom] = r"D:\P\6_pleine_res\pano.tif"
        self.assertEqual(self.page.dossier_sortie(t, champs, valeurs), r"D:\P\6_pleine_res")

    def test_chemins_d_outils_exclus_du_dossier_des_fichiers_produits(self):
        t = _tache("4A/rendre_projet.ps1")
        ctx = _contexte([_etat_outil("hugin", r"C:\Hugin\bin\nona.exe")])
        args, _, _ = self.formulaire.arguments_de(t, ctx)
        self.assertEqual(self.page.arguments_d_outil(args), {"-Hugin", "-Multiblend"})
        champs = self.formulaire.champs(t, args, None, ctx)
        valeurs = {c.arg.nom: c.valeur for c in champs}
        self.assertEqual(self.page.dossier_sortie(t, champs, valeurs, self.page.arguments_d_outil(args)), "")

    def test_chemin_vips_configure_puis_detecte(self):
        ctx = _contexte([_etat_outil("vips", r"C:\v\vips.exe")])
        self.assertEqual(self.page.chemin_vips(ctx), r"C:\v\vips.exe")
        ctx.poste.outils["vips"] = r"D:\autre\vips.exe"
        self.assertEqual(self.page.chemin_vips(ctx), r"D:\autre\vips.exe")
        self.assertIsNone(self.page.chemin_vips(_contexte()))

    def test_liens_internes_vers_github(self):
        texte = self.page.liens_absolus("voir [0D](#0d--dossiers) et [ext](https://x.org)")
        self.assertIn("](https://github.com/Gotcha26/giga-pano-hdr/blob/main/docs/GUIDE.md#0d--dossiers)", texte)
        self.assertIn("](https://x.org)", texte)

    def test_etat_execution_et_taille(self):
        ex = SimpleNamespace(etat="échec", code=2)
        self.assertEqual(self.page.etat_execution(ex), "échec (code 2)")
        self.assertEqual(self.page.etat_execution(SimpleNamespace(etat="interrompue", code=1)), "interrompue")
        self.assertEqual(self.page.taille_lisible(512), "512 o")
        self.assertEqual(self.page.taille_lisible(3 * 1024 * 1024), "3.0 Mo")


class TestApresExecution(unittest.TestCase):
    def setUp(self):
        from interface import page
        self.page = page
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.P = Path(self.tmp.name) / "P"
        (self.P / "3_optimisation").mkdir(parents=True)
        self.p = config.Panorama(T=self.tmp.name, P=str(self.P))
        config.enregistrer_panorama(self.p)
        self.ecrits = []

    def _mettre_a_jour(self, T, /, **cles):
        self.ecrits.append(dict(cles))
        return config.mettre_a_jour(T, **cles)

    def _ex(self, code, etat):
        return SimpleNamespace(code=code, etat=etat, lignes=["sortie"])

    def test_retour_au_meme_panorama_pendant_l_execution_recopie_le_report(self):
        t = _tache("5B/nona_images.ps1")
        revenu = config.charger_panorama(self.tmp.name)        # A → B → A : un autre objet pour le même $T
        ctx = SimpleNamespace(panorama=revenu)
        self.page.apres_execution(t, {"-Sortie": str(self.P / "5_hdr" / "rendu")}, self.p, self._ex(0, "terminée"),
                                  verrou=threading.Lock(), mettre_a_jour=self._mettre_a_jour, ctx=ctx)
        self.assertEqual(revenu.rendu_hdr, os.path.join("5_hdr", "rendu"))
        self.assertEqual(config.charger_panorama(self.tmp.name).rendu_hdr, os.path.join("5_hdr", "rendu"))
        autre = config.Panorama(T=str(self.P), P=str(self.P))     # un autre panorama courant : pas touché
        self.page.apres_execution(t, {"-Sortie": str(self.P / "r2")}, self.p, self._ex(0, "terminée"),
                                  verrou=threading.Lock(), mettre_a_jour=self._mettre_a_jour,
                                  ctx=SimpleNamespace(panorama=autre))
        self.assertEqual(autre.rendu_hdr, "")

    def test_valeurs_lues_par_un_geste(self):
        t = _tache("5C/geste")
        self.assertEqual(self.page.valeurs_lues(t, self.p), [])
        self.p.calques_hdr = r"5_hdr\calques"
        self.assertEqual(self.page.valeurs_lues(t, self.p), [("Calques à déplacer", str(self.P / "5_hdr" / "calques"))])

    def test_report_de_la_tache_annonce_dans_le_journal(self):
        t = _tache("5B/nona_images.ps1")
        ex = self._ex(0, "terminée")
        sortie = str(self.P / "5_hdr" / "rendu")
        self.page.apres_execution(t, {"-Sortie": sortie}, self.p, ex, verrou=threading.Lock(),
                                  mettre_a_jour=self._mettre_a_jour)
        attendu = "→ panorama.json : rendu_hdr = " + os.path.join("5_hdr", "rendu")
        self.assertEqual(ex.lignes, ["sortie", attendu])
        self.assertEqual(self.p.rendu_hdr, os.path.join("5_hdr", "rendu"))

    def test_geste_de_la_meme_phase_reporte(self):
        (self.P / "3_optimisation" / "pano_grille_opt.pto").write_text("", encoding="utf-8")
        t = _tache("3H/detecter_trous.py")
        ex = self._ex(0, "terminée")
        self.page.apres_execution(t, {}, self.p, ex, verrou=threading.Lock(), mettre_a_jour=self._mettre_a_jour)
        self.assertEqual(ex.lignes[-1], r"→ panorama.json : maitre = 3_optimisation\pano_grille_opt.pto")
        self.assertEqual(self.p.maitre, r"3_optimisation\pano_grille_opt.pto")

    def test_echec_ou_interruption_sans_report(self):
        t = _tache("5B/nona_images.ps1")
        ex = self._ex(None, "interrompue")
        self.page.apres_execution(t, {"-Sortie": str(self.P)}, self.p, ex, verrou=threading.Lock(),
                                  mettre_a_jour=self._mettre_a_jour)
        self.assertEqual(ex.lignes[1:], ["Interrompu.", lancer.MESSAGES_INTERRUPTION["nona_images.ps1"]])
        ex = self._ex(3, "échec")
        self.page.apres_execution(t, {"-Sortie": str(self.P)}, self.p, ex, verrou=threading.Lock(),
                                  mettre_a_jour=self._mettre_a_jour)
        self.assertEqual(ex.lignes[1:], ["Échec (code 3)."])
        self.assertEqual(self.ecrits, [])
        self.assertEqual(self.p.rendu_hdr, "")


class TestFumee(unittest.IsolatedAsyncioTestCase):
    """La page se construit dans le User simulé de nicegui.testing (sans navigateur ni serveur réseau).

    nicegui.testing est prévu pour pytest : on reproduit ce que fait son greffon (variable PYTEST_CURRENT_TEST,
    stockage dans un dossier temporaire), sans quoi NiceGUI se croit en « mode script » et vide .nicegui/."""

    async def asyncSetUp(self):
        asyncio.get_running_loop().slow_callback_duration = 30     # construire la page prend près d'une seconde

    async def test_la_page_se_construit(self):
        if not NICEGUI:
            self.skipTest("nicegui absent")
        try:
            from nicegui import app, storage
            from nicegui.testing.user_simulation import user_simulation
        except ImportError as e:
            self.skipTest(f"nicegui.testing indisponible : {e}")
        from interface import page
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        ancien_chemin, ancien_stockage = storage.Storage.path, app.storage
        storage.Storage.path = Path(tmp.name)
        app.storage = storage.Storage()
        self.addCleanup(setattr, app, "storage", ancien_stockage)
        self.addCleanup(setattr, storage.Storage, "path", ancien_chemin)
        ctx = _contexte()
        with mock.patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_interface_page"}):
            async with user_simulation(root=page.application(ctx)) as user:
                await user.open("/")
                for texte in ("Phase 0", "4A", "Configuration"):
                    await user.should_see(texte)
                # une tâche ouverte construit la zone centrale, la console et le volet d'aide (pages découpées)
                from nicegui import ui
                from nicegui.testing.user_interaction import UserInteraction
                items = {e for e in user.find(kind=ui.item).elements
                         if any("4A Rendre" in (getattr(d, "text", "") or "") for d in e.descendants())}
                self.assertEqual(len(items), 1)
                UserInteraction(user, items, None).click()
                for texte in ("4A — Rendre", "Mémoriser ces réglages", "Fichiers produits", "Mode d'emploi du script"):
                    await user.should_see(texte)


if __name__ == "__main__":
    unittest.main()
