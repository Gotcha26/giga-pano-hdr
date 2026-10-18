"""Les scripts pilotés : déclaration présente, et aucun menu quand l'entrée standard n'est pas un terminal."""

import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

PILOTES = [
    # Tâche 5 : chemin principal
    "verifier_ordre.py", "controle_reglages_export.py", "ecart_paires.py", "renommer_pano.py",
    "renommer_par_raw.py", "tiffinfo.py", "generer_pto.py", "generer_pto_hdr.py", "diagnostic_cp.py",
    "diagnostic_pas_v.py", "corriger_pas_v.py", "filtrer_cp.py", "preparer_optimisation.py", "detecter_trous.py",
    "placer_isoles.py", "affiner_images_faibles.py", "propager_geometrie.py", "extraire_sous_projet.py",
    "redimensionner_projet.py", "deplacer_projet.py", "ranger_intermediaires.py", "cadrage_lightroom.py",
    # Tâche 6 : mesures et inspection
    "voir_positions.py", "lister_pires_cp.py", "detecter_aberrantes.py", "compter_cp_paire.py", "mesurer_ciel.py",
    "mesurer_gain_paires.py", "mesurer_bandes_ciel.py", "localiser_sauts_ciel.py", "comparer_rendus.py",
    "comparer_couleur.py", "rehausser_ciel.py",
]
EXEMPTES = ["verifier_renvois.py",   # sans argument, il contrôle : jamais de menu de pilotage
            "panorama.py"]           # le lanceur lui-même

MARQUEUR_MENU = "PILOTAGE"


class TestSansTerminal(unittest.TestCase):
    def test_sans_argument_et_sans_tty_le_menu_ne_s_affiche_pas(self):
        for nom in PILOTES:
            with self.subTest(nom):
                # sans -I : avec lui, scripts/ n'est pas dans sys.path et l'import de pilotage échouerait avant piloter()
                r = subprocess.run([sys.executable, str(SCRIPTS / nom)], stdin=subprocess.DEVNULL,
                                   capture_output=True, text=True, timeout=60, cwd=SCRIPTS)
                self.assertNotIn(MARQUEUR_MENU, r.stdout + r.stderr)
                self.assertNotIn("No module named 'pilotage'", r.stderr)
                # (cadrage_lightroom.py pose sa propre question quand --catalogue manque : comportement antérieur)


class TestDeclaration(unittest.TestCase):
    def test_declaration_presente(self):
        for nom in PILOTES:
            with self.subTest(nom):
                texte = (SCRIPTS / nom).read_text(encoding="utf-8")
                self.assertIn("ARGUMENTS = [", texte)
                self.assertIn("piloter(__doc__, ARGUMENTS", texte)

    def test_tous_les_scripts_python_sont_pilotes_sauf_l_exempte(self):
        presents = sorted(p.name for p in SCRIPTS.glob("*.py"))
        self.assertEqual(presents, sorted(PILOTES + EXEMPTES))
        for nom in EXEMPTES:
            self.assertNotIn("piloter(", (SCRIPTS / nom).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
