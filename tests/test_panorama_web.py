"""Tests du point d'entrée web (panorama_web.py)."""

import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


class TestPointDEntree(unittest.TestCase):
    def test_sans_nicegui_message_et_code_1(self):
        import panorama_web
        with mock.patch.object(panorama_web, "verifier_nicegui", return_value="NiceGUI absent : pip install nicegui"):
            lignes = []
            self.assertEqual(panorama_web.main(ecrire=lignes.append), 1)
            self.assertIn("pip install nicegui", lignes[0])

    def test_port_libre_est_un_entier_haut(self):
        import panorama_web
        self.assertGreater(panorama_web.port_libre(), 1024)

    def test_mode_d_emploi_en_tete(self):
        texte = (SCRIPTS / "panorama_web.py").read_text(encoding="utf-8")
        for rubrique in ("CONTEXTE", "MODE OPÉRATOIRE", "ENTRÉES", "SORTIES", "EXEMPLE"):
            self.assertIn(rubrique, texte)


if __name__ == "__main__":
    unittest.main()
