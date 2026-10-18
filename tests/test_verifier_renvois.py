"""Tests de verifier_renvois.py (garde-fou de la numérotation du guide).

Lancer depuis la racine du dépôt :
    python -I -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from verifier_renvois import ancre, ancres, cites, declares, restes, verifier  # noqa: E402


class TestAncres(unittest.TestCase):
    def test_ancre_style_github(self):
        self.assertEqual(ancre("📸 Phase 1 — Prise de vue"), "-phase-1--prise-de-vue")
        self.assertEqual(ancre("3E — Optimiser (dans ***Hugin***)"), "3e--optimiser-dans-hugin")
        self.assertEqual(ancre("1. Combien de pixels à 100 % ?"), "1-combien-de-pixels-à-100--")
        # GitHub garde le sélecteur de variante U+FE0F d'un emoji comme 🖥️
        self.assertEqual(ancre("🖥️ Configuration de référence"), "️-configuration-de-référence")

    def test_ancres_dupliquees(self):
        t = "## Variante : tester\n\n## Variante : tester\n"
        self.assertEqual(ancres(t), {"variante--tester", "variante--tester-1"})


class TestIdentifiants(unittest.TestCase):
    def test_declares_et_cites(self):
        t = "### 3E — Optimiser\n\nVoir **3E** puis **3Z**.\n```\n# 3E.2. HUGIN\n```\n"
        self.assertEqual(declares(t), {"3E"})
        self.assertEqual([i for _, i in cites(t, est_script=False)], ["3E", "3Z", "3E.2"])

    def test_ids_hors_gras(self):
        t = "| 0A – 0D |\nvoir l'étape 3Z dans `L1_C05_` et [x](#3c--y)\n```\n├── 3_grille\\   ← 3A-3B : grille\n```\n"
        self.assertEqual([i for _, i in cites(t, est_script=False)], ["0A", "0D", "3Z", "3A", "3B"])

    def test_faux_amis(self):
        # « EOS-1D » et « écran 4K » ne sont pas des étapes ; en gras, ils redeviennent des citations
        self.assertEqual([i for _, i in cites("Canon EOS-1D X, écran 4K, **1D**", est_script=False)], ["1D"])

    def test_mermaid(self):
        t = "```mermaid\nflowchart LR\n    A[2. Grille] --> B[0a-0b. Sélectionner]\n    C[3Z. Truc] --> D[3A-3B. Ok]\n```\n"
        self.assertEqual([n for n, _ in restes(t, False)], [3])
        self.assertEqual([i for _, i in cites(t, est_script=False)], ["3Z", "3A", "3B"])

    def test_cites_script(self):
        self.assertEqual([i for _, i in cites("    Étapes 3C à 3E, puis Etape 6B.", est_script=True)],
                         ["3C", "3E", "6B"])


class TestRestes(unittest.TestCase):
    def test_reste_ancien_systeme(self):
        self.assertEqual(restes("Étape 3F (vignettage)", False), [])
        self.assertEqual(len(restes("voir l'étape 10", False)), 1)
        self.assertEqual(len(restes("voir l'étape 6b", False)), 1)
        self.assertEqual(len(restes("**0b bis. Préréglage**", False)), 1)

    def test_formes_ancien_systeme(self):
        for ligne in ("ÉTAPE 10", "étape n° 10", "voir 10b", "étapes 3A à 11"):
            self.assertEqual(len(restes(ligne, False)), 1, ligne)

    def test_restes_script(self):
        self.assertEqual(len(restes("    Phase 3, étape 6b (vignettage)", False, est_script=True)), 1)
        self.assertEqual(restes("# 1. lire le fichier", False, est_script=True), [])

    def test_commentaire_aide_memoire(self):
        t = "```powershell\n# 6bis. HUGIN : ouvrir\n$OPT = \"$P\\20_optimisation\"\n# 3E.2. HUGIN\n```\n"
        self.assertEqual(len(restes(t, False)), 2)
        self.assertEqual([i for _, i in cites(t, est_script=False)], ["3E.2"])

    def test_exemption_dossiers_journal(self):
        t = "rendu dans 30_phase1_centree\nvoir l'étape 9"
        self.assertEqual(len(restes(t, exempter_dossiers=True)), 1)
        self.assertEqual(len(restes(t, exempter_dossiers=False)), 2)


class TestVerifier(unittest.TestCase):
    def test_lien_casse(self):
        with tempfile.TemporaryDirectory() as d:
            racine = Path(d)
            (racine / "docs").mkdir()
            (racine / "scripts").mkdir()
            (racine / "docs" / "GUIDE.md").write_text("### 3A — Grille\n", encoding="utf-8")
            (racine / "scripts" / "INDEX.md").write_text(
                "[a](../docs/GUIDE.md#3a--grille)\n"
                "[b](../docs/GUIDE.md#3b--absent)\n",
                encoding="utf-8",
            )
            ecarts = verifier(racine)
        self.assertEqual(len(ecarts), 1)
        self.assertEqual(ecarts[0][2], "lien-casse")
        self.assertIn("3b--absent", ecarts[0][3])

    def test_lien_local_casse(self):
        with tempfile.TemporaryDirectory() as d:
            racine = Path(d)
            (racine / "docs").mkdir()
            (racine / "scripts").mkdir()
            (racine / "docs" / "GUIDE.md").write_text(
                "### 3A — Grille\n\n[x](#3a--grille) et [y](#3b--absent)\n", encoding="utf-8")
            ecarts = verifier(racine)
        self.assertEqual([(e[2], e[3]) for e in ecarts], [("lien-casse", "#3b--absent")])


if __name__ == "__main__":
    unittest.main()
