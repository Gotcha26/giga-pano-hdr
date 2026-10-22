"""Tests de interface.aide : sections du guide, lien GitHub et modes d'emploi des scripts."""

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from interface import aide  # noqa: E402
from pilotage import lancer  # noqa: E402


class TestAide(unittest.TestCase):
    def test_section_4a_contient_rendre_projet_et_s_arrete_avant_la_variante(self):
        s = aide.section_du_guide("4A")
        self.assertTrue(s.startswith("### 4A — "))
        self.assertIn("rendre_projet.ps1", s)
        self.assertNotIn("### Variante de 4A", s)

    def test_sous_etape_6c5(self):
        s = aide.section_du_guide("6C.5")
        self.assertTrue(s.startswith("#### 6C.5 — "))
        self.assertIn("rehausser_ciel.py", s)

    def test_repere_inconnu_retourne_none(self):
        self.assertIsNone(aide.section_du_guide("9Z"))
        self.assertIsNone(aide.section_du_guide("4A", guide=Path("inexistant.md")))

    def test_titre_dans_un_bloc_de_code_est_ignore(self):
        with tempfile.TemporaryDirectory() as t:
            guide = Path(t) / "G.md"
            guide.write_text("### 2A — Un\n```\n# 2E. faux titre\n### 2F — faux\n```\nsuite\n### 2B — Deux\n",
                             encoding="utf-8")
            s = aide.section_du_guide("2A", guide)
            self.assertIn("faux titre", s)
            self.assertIn("suite", s)
            self.assertNotIn("2B", s)
            self.assertIsNone(aide.section_du_guide("2F", guide))

    def test_niveau_inferieur_ne_termine_pas_la_section(self):
        with tempfile.TemporaryDirectory() as t:
            guide = Path(t) / "G.md"
            guide.write_text("### 6C — Mère\n#### 6C.1 — Fille\ntexte\n### 6D — Autre\n", encoding="utf-8")
            s = aide.section_du_guide("6C", guide)
            self.assertIn("6C.1", s)
            self.assertNotIn("6D", s)

    def test_lien_guide_ancre(self):
        self.assertTrue(aide.lien_guide("3A").endswith("#3a--générer-le-projet-de-grille"))
        self.assertEqual(aide.lien_guide("9Z"), aide.URL_GUIDE)

    def test_mode_d_emploi_py_et_ps1(self):
        self.assertIn("MODE OPÉRATOIRE", aide.mode_d_emploi(SCRIPTS / "generer_pto.py"))
        self.assertIn("MODE OPERATOIRE", aide.mode_d_emploi(SCRIPTS / "rendre_projet.ps1"))
        self.assertEqual(aide.mode_d_emploi(SCRIPTS / "INDEX.md"), "")

    def test_commentaire_ps_s_arrete_au_premier_code(self):
        with tempfile.TemporaryDirectory() as t:
            ps = Path(t) / "x.ps1"
            ps.write_text("# Titre\n#\n# Suite\nparam(\n  # interne\n)\n", encoding="utf-8")
            self.assertEqual(lancer.commentaire_ps(ps), "Titre\n\nSuite")
            self.assertEqual(lancer._titre_ps(ps), "Titre")

    def test_commentaire_ps_retire_diese_et_un_seul_espace(self):
        with tempfile.TemporaryDirectory() as t:
            ps = Path(t) / "x.ps1"
            ps.write_text("#Titre\n#   indenté\n# # double\n", encoding="utf-8")
            self.assertEqual(lancer.commentaire_ps(ps), "Titre\n  indenté\n# double")

    def test_titres_des_ps1_du_depot(self):
        ps1 = sorted(SCRIPTS.glob("*.ps1"))
        self.assertEqual(len(ps1), 9)
        for p in ps1:
            with self.subTest(p.name):
                titre = lancer._titre_ps(p)
                self.assertTrue(titre)
                self.assertFalse(titre.startswith(("#", " ")))

    def test_titres_hors_blocs_de_code_tilde_et_backtick(self):
        with tempfile.TemporaryDirectory() as t:
            guide = Path(t) / "G.md"
            guide.write_text("~~~\n### 1A — Faux\n```\n### 1B — Faux aussi\n~~~\n### 2A — Vrai\n```\n### 2B — Faux\n```\n",
                             encoding="utf-8")
            lignes, titres = aide._titres(guide)
            self.assertEqual([t for _, _, t in titres], ["2A — Vrai"])
            self.assertEqual(lignes[titres[0][0]], "### 2A — Vrai")
            self.assertIsNone(aide._titres(Path(t) / "absent.md"))


if __name__ == "__main__":
    unittest.main()
