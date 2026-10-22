"""Tests du catalogue de tâches (pilotage.catalogue) et de son rendu à l'identique dans la console."""

import json
import re
import sys
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SCRIPTS = RACINE / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pilotage import menu  # noqa: E402
from test_panorama import contexte  # noqa: E402


class TestConsoleIdentique(unittest.TestCase):
    def test_menus_console_identiques_a_l_instantane(self):
        import panorama
        attendu = json.loads((FIXTURES / "menus_console.json").read_text(encoding="utf-8"))
        ctx = contexte([])
        for groupe, lignes in attendu.items():
            entrees = panorama.SOUS_MENUS[groupe](ctx)
            obtenu = [{"libelle": l, "numero": n, "section": e.section, "effet": e.effet, "informative": e.action is None}
                      for l, n, e in zip(menu.libelles(entrees, ctx), menu.numeroter(entrees, ctx), entrees)]
            self.assertEqual(obtenu, lignes, groupe)


class TestCatalogue(unittest.TestCase):
    def setUp(self):
        from pilotage import catalogue
        self.catalogue = catalogue

    def test_chaque_tache_a_un_script_existant_ou_une_action_ou_un_geste(self):
        for t in self.catalogue.TACHES:
            with self.subTest(t.identifiant):
                self.assertTrue(t.script or t.action or t.geste)
                if t.script:
                    self.assertTrue((SCRIPTS / t.script).exists())

    def test_identifiants_uniques(self):
        ids = [t.identifiant for t in self.catalogue.TACHES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_reperes_existent_dans_le_guide(self):
        guide = (RACINE / "docs" / "GUIDE.md").read_text(encoding="utf-8")
        for t in self.catalogue.TACHES:
            if t.repere:
                with self.subTest(t.identifiant):
                    self.assertRegex(guide, rf"(?m)^#{{3,4}} .*\b{re.escape(t.repere)}\b",
                                     f"{t.repere} absent des titres du guide")

    def test_par_phase_trie_naturellement(self):
        reperes = [t.repere for t in self.catalogue.par_phase()[3]]
        self.assertEqual(reperes, sorted(reperes, key=self.catalogue.cle_tri))
        self.assertLess(reperes.index("3C.2"), reperes.index("3D"))

    def test_par_phase_cles(self):
        self.assertEqual(list(self.catalogue.par_phase()), [0, 1, 2, 3, 4, 5, 6, 7, "mesures"])

    def test_rendre_projet_a_trois_taches_une_seule_en_console(self):
        rp = [t for t in self.catalogue.TACHES if t.script == "rendre_projet.ps1"]
        self.assertEqual(sorted(t.repere for t in rp), ["4A", "6B", "6C.4"])
        self.assertEqual([t.groupe_console for t in rp].count("rendus"), 1)

    def test_geste_3g_reporte_le_maitre(self):
        t = next(t for t in self.catalogue.TACHES if t.attendu)
        self.assertEqual(t.attendu, r"3_optimisation\pano_grille_opt.pto")
        self.assertEqual(t.reporte, {"maitre": "attendu"})

    def test_console_dans_l_ordre_du_catalogue(self):
        self.assertEqual([t.identifiant for t in self.catalogue.console("phase7")],
                         [t.identifiant for t in self.catalogue.TACHES if t.groupe_console == "phase7"])

    def test_scripts_cites(self):
        cites = self.catalogue.scripts_cites()
        self.assertIn("rendre_projet.ps1", cites)
        self.assertIn("verifier_ordre.py", cites)


if __name__ == "__main__":
    unittest.main()
