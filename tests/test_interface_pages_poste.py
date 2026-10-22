"""Tests de interface.pages_poste : fonctions pures des pages Panorama, Nouveau panorama, Phase 0 et Configuration
(sans serveur), et fumée des quatre dialogues avec le User de NiceGUI."""

import asyncio
import dataclasses
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from interface import pages_poste  # noqa: E402
from pilotage import config, lancer, outils  # noqa: E402
from pilotage.couleurs import Couleurs  # noqa: E402

NICEGUI = importlib.util.find_spec("nicegui") is not None


def _etat_outil(cle, chemin, version="1.0"):
    outil = next(o for o in outils.OUTILS if o.cle == cle)
    return outils.Etat(outil, chemin, version if chemin else None)


class TestChampsPanorama(unittest.TestCase):
    def test_un_champ_par_cle_sauf_reglages_forme_stockee(self):
        p = config.Panorama(T=r"D:\P\a", P=r"D:\P\a\Assemblage-Hugin", lignes=6, focale=35.0,
                            maitre=r"3_optimisation\m.pto", reglages={"x": {"-a": "1"}})
        champs = pages_poste.champs_panorama(p)
        noms = [c.nom for c in champs]
        self.assertEqual(noms, [f.name for f in dataclasses.fields(config.Panorama) if f.name != "reglages"])
        par_nom = {c.nom: c for c in champs}
        self.assertEqual((par_nom["maitre"].genre, par_nom["maitre"].valeur, par_nom["maitre"].phase),
                         ("pto", r"3_optimisation\m.pto", "3_optimisation"))
        self.assertEqual(par_nom["hdr_pto"].phase, "5_hdr")
        self.assertEqual((par_nom["lignes"].genre, par_nom["lignes"].valeur), ("entier", 6))
        self.assertEqual((par_nom["focale"].genre, par_nom["pas_h"].genre), ("reel", "reel"))
        self.assertEqual({par_nom[c].genre for c in ("T", "P", "H", "export_l", "rendu_hdr", "calques_hdr")},
                         {"dossier"})
        self.assertEqual(par_nom["pleine_res"].genre, "fichier")

    def test_pto_de_la_phase_en_forme_stockee(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "3_optimisation").mkdir()
            for nom in ("b.pto", "a.pto", "c.txt"):
                (Path(d) / "3_optimisation" / nom).write_text("", encoding="utf-8")
            self.assertEqual(pages_poste.pto_de_la_phase(d, "3_optimisation"),
                             [os.path.join("3_optimisation", "a.pto"), os.path.join("3_optimisation", "b.pto")])
            self.assertEqual(pages_poste.pto_de_la_phase(d, "5_hdr"), [])
            self.assertEqual(pages_poste.pto_de_la_phase("", "5_hdr"), [])

    def test_forme_stockee(self):
        T, P = r"D:\P\a", r"D:\P\a\Assemblage-Hugin"
        self.assertEqual(pages_poste.forme_stockee("maitre", r"D:\P\a\Assemblage-Hugin\3_optimisation\m.pto", T, P),
                         r"3_optimisation\m.pto")
        self.assertEqual(pages_poste.forme_stockee("maitre", r"E:\ailleurs\m.pto", T, P), r"E:\ailleurs\m.pto")
        self.assertEqual(pages_poste.forme_stockee("export_l", r"D:\P\a\Export-L", T, P), "Export-L")
        self.assertEqual(pages_poste.forme_stockee("H", r"D:\RAW\HDR", T, P), r"D:\RAW\HDR")

    def test_chemin_absolu_depart_de_parcourir(self):
        T, P = r"D:\P\a", r"D:\P\a\Assemblage-Hugin"
        self.assertEqual(pages_poste.chemin_absolu("maitre", r"3_optimisation\m.pto", T, P),
                         os.path.join(P, r"3_optimisation\m.pto"))
        self.assertEqual(pages_poste.chemin_absolu("maitre", "", T, P), os.path.join(P, "3_optimisation"))
        self.assertEqual(pages_poste.chemin_absolu("export_h", "Export-TIFF-H", T, P), os.path.join(T, "Export-TIFF-H"))
        self.assertEqual(pages_poste.chemin_absolu("pleine_res", r"E:\x.tif", T, P), r"E:\x.tif")
        self.assertEqual(pages_poste.chemin_absolu("rendu_hdr", "", T, P), "")

    def test_seules_les_cles_modifiees_sont_reecrites(self):
        p = config.Panorama(T=r"D:\P\a", P=r"D:\P\a\Assemblage-Hugin", lignes=6, pas_h=5.0)
        affichees = {c.nom: c.valeur for c in pages_poste.champs_panorama(p)}
        saisies = dict(affichees, lignes=6.0, pas_h="5", colonnes=37.0)
        modifiees, erreurs = pages_poste.modifications_panorama(affichees, saisies)
        self.assertEqual((modifiees, erreurs), ({"colonnes": 37}, []))


class TestLirePanorama(unittest.TestCase):
    def _saisies(self, **autres):
        saisies = {c.nom: c.valeur for c in pages_poste.champs_panorama(
            config.Panorama(T=r"D:\P\a", P=r"D:\P\a\Assemblage-Hugin"))}
        saisies.update(autres)
        return saisies

    def test_nombres_convertis_et_chemins_ranges(self):
        valeurs, erreurs = pages_poste.lire_panorama(self._saisies(
            lignes=6.0, colonnes="37", focale=35, pas_h="5,5", largeur_hdr=None, H=r"  D:\RAW\HDR ",
            maitre=r"D:\P\a\Assemblage-Hugin\3_optimisation\pano_grille_opt.pto"))
        self.assertEqual(erreurs, [])
        self.assertEqual((valeurs["lignes"], valeurs["colonnes"], valeurs["focale"], valeurs["pas_h"]), (6, 37, 35.0, 5.5))
        self.assertIsInstance(valeurs["lignes"], int)
        self.assertIsInstance(valeurs["focale"], float)
        self.assertIsNone(valeurs["largeur_hdr"])
        self.assertEqual(valeurs["H"], r"D:\RAW\HDR")
        self.assertEqual(valeurs["maitre"], r"3_optimisation\pano_grille_opt.pto")
        self.assertNotIn("reglages", valeurs)

    def test_erreurs_entier_nombre_et_obligatoires(self):
        _, erreurs = pages_poste.lire_panorama(self._saisies(lignes=6.5, expos="x", pas_v="abc", T=" ", P=""))
        self.assertEqual(len(erreurs), 5)
        self.assertTrue(any(e.startswith("lignes") and "entier" in e for e in erreurs))
        self.assertTrue(any(e.startswith("pas_v") for e in erreurs))
        self.assertTrue(any(e.startswith("T") for e in erreurs))


class TestDeplacement(unittest.TestCase):
    def test_deplacement_refuse_si_introuvable_ou_deja_un_panorama(self):
        with tempfile.TemporaryDirectory() as d:
            ancien, libre, occupe = (str(Path(d) / n) for n in ("ancien", "libre", "occupe"))
            for dossier in (ancien, libre, occupe):
                os.mkdir(dossier)
            config.enregistrer_panorama(config.Panorama(T=occupe, P="", maitre=r"3_optimisation\m.pto"))
            self.assertIsNone(pages_poste.deplacement_refuse(ancien, libre))
            self.assertIsNone(pages_poste.deplacement_refuse(ancien, ancien.upper() + os.sep))
            self.assertIn("introuvable", pages_poste.deplacement_refuse(ancien, str(Path(d) / "absent")))
            raison = pages_poste.deplacement_refuse(ancien, occupe)
            self.assertIn("contient déjà un panorama.json", raison)
            (Path(occupe) / "panorama.json").write_text("{illisible", encoding="utf-8")
            self.assertIsNotNone(pages_poste.deplacement_refuse(ancien, occupe))

    def test_liste_des_panoramas_sans_doublon(self):
        f = pages_poste.panoramas_apres_deplacement
        self.assertEqual(f(["a", "b", "c"], "b", "x"), ["a", "x", "c"])
        self.assertEqual(f(["a", "b", "x"], "b", "x"), ["a", "x"])
        self.assertEqual(f(["a"], "b", "x"), ["a", "x"])


class TestNouveau(unittest.TestCase):
    def setUp(self):
        self.courant = config.Panorama(T=r"D:\Panoramas\2026-07-01\35mm",
                                       P=r"D:\Panoramas\2026-07-01\35mm\Assemblage-Hugin", focale=35, lignes=6)

    def test_valeurs_initiales(self):
        initiales = pages_poste.valeurs_initiales_nouveau(self.courant, "2026-10-22")
        self.assertEqual((initiales["date"], initiales["focale"], initiales["T"]),
                         ("2026-10-22", 35, r"D:\Panoramas\2026-10-22\35mm"))
        self.assertEqual((initiales["lignes"], initiales["largeur_hdr"]), (6, 20000))
        self.assertEqual(list(initiales), [nom for nom, _ in pages_poste.CHAMPS_NOUVEAU])

    def test_recalcul_ne_touche_pas_aux_champs_edites(self):
        saisies = {"date": "2026-10-23", "focale": 50, "T": r"E:\mien", "raws": r"D:\RAW\jour", "lignes": 9}
        remplir, existant = pages_poste.recalculer_nouveau(self.courant, saisies, touches={"lignes"})
        self.assertIsNone(existant)
        self.assertEqual(remplir["T"], r"D:\Panoramas\2026-10-23\50mm")
        self.assertNotIn("lignes", remplir)
        self.assertNotIn("date", remplir)
        self.assertNotIn("focale", remplir)
        remplir, _ = pages_poste.recalculer_nouveau(self.courant, saisies, touches={"T", "raws"})
        self.assertNotIn("T", remplir)
        self.assertNotIn("raws", remplir)
        self.assertEqual(remplir["H"], str(Path(r"D:\RAW\jour", "HDR")))
        self.assertEqual(remplir["lignes"], 6)

    def test_recalcul_reprend_le_panorama_json_existant(self):
        with tempfile.TemporaryDirectory() as d:
            T = str(Path(d) / "pano")
            config.enregistrer_panorama(config.Panorama(T=T, P="", H=r"D:\RAW\x\HDR", lignes=4))
            remplir, existant = pages_poste.recalculer_nouveau(self.courant, {"date": "d", "focale": "", "T": T},
                                                               touches={"T"})
            self.assertIsNotNone(existant)
            self.assertEqual((remplir["lignes"], remplir["H"], remplir["raws"]), (4, r"D:\RAW\x\HDR", r"D:\RAW\x"))

    def test_lire_nouveau(self):
        valeurs, erreurs = pages_poste.lire_nouveau({"date": "2026-10-22", "focale": 35, "T": r" E:\T ", "raws": "x",
                                                     "H": "", "lignes": 6.0, "pas_h": "5", "largeur_mm": 24})
        self.assertEqual(erreurs, [])
        self.assertEqual((valeurs["T"], valeurs["H"], valeurs["focale"], valeurs["lignes"], valeurs["pas_h"]),
                         (r"E:\T", "", 35.0, 6, 5.0))
        self.assertIsNone(valeurs["expos"])
        self.assertNotIn("raws", valeurs)
        _, erreurs = pages_poste.lire_nouveau({"T": "", "lignes": "6,5", "focale": "x"})
        self.assertEqual(len(erreurs), 3)


class TestOutils(unittest.TestCase):
    def test_lignes_outils(self):
        lignes = pages_poste.lignes_outils([_etat_outil("hugin", r"C:\H\nona.exe"),
                                            _etat_outil("vips", r"C:\v.exe", version=None),
                                            _etat_outil("exiftool", None), _etat_outil("multiblend", None)])
        hugin, vips, exiftool, multiblend = lignes
        self.assertEqual((hugin["etat"], hugin["version"], hugin["chemin"], hugin["commande"]),
                         ("OK", "1.0", r"C:\H\nona.exe", None))
        self.assertEqual(vips["version"], "version inconnue")
        self.assertEqual(exiftool["etat"], "absent")
        self.assertIn("winget install --id OliverBetz.ExifTool", exiftool["commande"])
        self.assertIsNone(multiblend["commande"])
        self.assertEqual(multiblend["url"], "http://horman.net/multiblend/")
        self.assertTrue(multiblend["dezipper"])

    def test_outils_modifies(self):
        actuels = {"vips": r"C:\v.exe", "hugin": r"C:\H", "autre": "x"}
        nouveaux = pages_poste.outils_modifies(actuels, {"vips": "  ", "hugin": r" D:\Hugin\bin ", "exiftool": r"C:\e.exe",
                                                         "multiblend": ""})
        self.assertEqual(nouveaux, {"hugin": r"D:\Hugin\bin", "exiftool": r"C:\e.exe", "autre": "x"})
        self.assertEqual(actuels["vips"], r"C:\v.exe")      # copie, pas de modification en place

    def test_statut_outil(self):
        with tempfile.TemporaryDirectory() as d:
            etats = [_etat_outil("vips", r"C:\v.exe"), _etat_outil("exiftool", None)]
            self.assertEqual(pages_poste.statut_outil("vips", None, etats), r"✓ 1.0 — C:\v.exe")
            self.assertEqual(pages_poste.statut_outil("vips", d, etats), r"✓ 1.0 — C:\v.exe")
            self.assertEqual(pages_poste.statut_outil("exiftool", str(Path(d) / "absent.exe"), etats),
                             "⚠ chemin configuré introuvable ; ✗ absent")

    def test_genres_des_outils_configurables(self):
        import panorama
        self.assertEqual([c for c, _ in panorama.OUTILS_CONFIGURABLES], list(pages_poste.GENRES_OUTILS))
        self.assertEqual(pages_poste.GENRES_OUTILS["hugin"], "dossier")
        self.assertEqual({pages_poste.GENRES_OUTILS[c] for c in ("multiblend", "vips", "exiftool")}, {"fichier"})


class TestFumee(unittest.IsolatedAsyncioTestCase):
    """Les quatre dialogues s'ouvrent depuis l'en-tête, dans le User simulé de nicegui.testing (voir
    test_interface_page.TestFumee pour la mise en place hors pytest)."""

    async def asyncSetUp(self):
        asyncio.get_running_loop().slow_callback_duration = 30

    async def test_les_quatre_pages_s_ouvrent(self):
        if not NICEGUI:
            self.skipTest("nicegui absent")
        try:
            from nicegui import app, storage, ui
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
        T = str(Path(tmp.name) / "pano")
        p = config.Panorama(T=T, P=str(Path(T) / "Assemblage-Hugin"), lignes=6)
        ctx = lancer.Contexte(poste=config.Poste(panoramas=[T], courant=T), panorama=p,
                              etats=[_etat_outil("hugin", r"C:\H\nona.exe"), _etat_outil("exiftool", None)],
                              c=Couleurs(forcer=False), scripts=SCRIPTS)
        with mock.patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_interface_pages_poste"}):
            async with user_simulation(root=page.application(ctx)) as user:
                await user.open("/")
                for bouton, attendu in (("Panorama", "Oublier les réglages mémorisés"),
                                        ("Nouveau panorama", "Créer"),
                                        ("Phase 0", "Installer"),
                                        ("⚙ Configuration", "Dossier bin de Hugin")):
                    user.find(kind=ui.button, content=bouton).click()
                    await user.should_see(attendu)


if __name__ == "__main__":
    unittest.main()
