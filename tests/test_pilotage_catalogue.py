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

    def test_phase_mesures_reservee_aux_taches_sans_repere(self):
        for t in self.catalogue.TACHES:
            if t.phase == "mesures":
                with self.subTest(t.identifiant):
                    self.assertEqual(t.repere, "")
            elif t.repere:
                with self.subTest(t.identifiant):
                    self.assertEqual(t.phase, int(t.repere[0]))
        self.assertTrue(any(t.repere == "3F" for t in self.catalogue.par_phase()[3]))

    def test_par_phase_cles(self):
        self.assertEqual(list(self.catalogue.par_phase()), [0, 1, 2, 3, 4, 5, 6, 7, "mesures"])

    def test_rendre_projet_a_trois_taches_une_seule_en_console(self):
        rp = [t for t in self.catalogue.TACHES if t.script == "rendre_projet.ps1"]
        self.assertEqual(sorted(t.repere for t in rp), ["4A", "6B", "6C.4"])
        self.assertEqual([t.groupe_console for t in rp].count("rendus"), 1)

    def test_geste_3g_reporte_le_maitre(self):
        t = next(t for t in self.catalogue.TACHES if t.identifiant == "3G/geste")
        self.assertTrue(t.est_geste)
        self.assertEqual(t.attendu, r"3_optimisation\pano_grille_opt.pto")
        self.assertEqual(t.reporte, {"maitre": "attendu"})

    def test_console_dans_l_ordre_du_catalogue(self):
        self.assertEqual([t.identifiant for t in self.catalogue.console("phase7")],
                         [t.identifiant for t in self.catalogue.TACHES if t.groupe_console == "phase7"])

    # Clés reportées qu'aucune tâche ne relit, avec la raison ; vide aujourd'hui (calques_hdr : rappel du geste 5C).
    CLES_REPORTEES_NON_LUES = {}

    def _configs_des_arguments(self):
        from pilotage import arguments as args_mod
        from pilotage import declarations_ps
        configs = set()
        for t in self.catalogue.TACHES:
            if t.arguments is not None:
                declares = t.arguments
            elif t.script.endswith(".ps1"):
                declares = declarations_ps.PS[t.script][0]
            elif t.script:
                declares = args_mod.lire_declaration(SCRIPTS / t.script)[0]
            else:
                declares = []
            configs |= {a.config for a in declares if a.config}
        return configs

    def test_toute_cle_reportee_est_relue(self):
        reportees = {cle for t in self.catalogue.TACHES for cle in t.reporte}
        lues = {cle for t in self.catalogue.TACHES for cle in t.lit.values()} | self._configs_des_arguments()
        for cle in sorted(reportees):
            with self.subTest(cle):
                self.assertTrue(cle in lues or cle in self.CLES_REPORTEES_NON_LUES,
                                f"{cle} est reportée mais aucune tâche ne la relit")

    def test_lit_nomme_des_arguments_declares(self):
        from pilotage import declarations_ps
        for t in self.catalogue.TACHES:
            if t.lit and t.script.endswith(".ps1"):
                with self.subTest(t.identifiant):
                    self.assertLessEqual(set(t.lit), {a.nom for a in declarations_ps.PS[t.script][0]})

    def test_les_reperes_supplementaires_ne_lisent_pas_la_cle_du_repere_d_origine(self):
        nona = {t.repere: t.lit for t in self.catalogue.TACHES if t.script == "nona_images.ps1"}
        self.assertEqual(nona, {"5B": {"-Projet": "hdr_pto"}, "6B": {}, "6C.2": {}})

    def test_scripts_cites(self):
        cites = self.catalogue.scripts_cites()
        self.assertIn("rendre_projet.ps1", cites)
        self.assertIn("verifier_ordre.py", cites)


if __name__ == "__main__":
    unittest.main()
