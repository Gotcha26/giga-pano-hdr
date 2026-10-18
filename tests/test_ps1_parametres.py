"""Les quatre scripts PowerShell qui appellent Hugin, multiblend ou libvips exposent le chemin en paramètre."""

import re
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

ATTENDUS = {
    "rendre_projet.ps1": [r"\[string\]\$Hugin = 'C:\\Program Files\\Hugin\\bin'",
                          r"\[string\]\$Multiblend = 'D:\\Outils\\multiblend\\multiblend\.exe'",
                          r"^\$hb = \$Hugin", r"^\$multiblend = \$Multiblend"],
    "nona_images.ps1": [r"\[string\]\$Hugin = 'C:\\Program Files\\Hugin\\bin'",
                        r"^\$nona = Join-Path \$Hugin 'nona\.exe'"],
    "fusionner_par_exposition.ps1": [r"\[string\]\$Hugin = 'C:\\Program Files\\Hugin\\bin'",
                                     r"\[string\]\$Multiblend = 'D:\\Outils\\multiblend\\multiblend\.exe'",
                                     r"^\$enblend = Join-Path \$Hugin 'enblend\.exe'", r"^\$multiblend = \$Multiblend"],
    "rendre_lisible.ps1": [r"\[string\]\$Vips = 'D:\\Outils\\libvips\\vips-dev-8\.18\\bin\\vips\.exe'",
                           r"^\$vips = \$Vips"],
}
INTERDITS = {   # plus aucun chemin en dur hors du bloc param
    "rendre_projet.ps1": [r"^\$hb = 'C:", r"^\$multiblend = 'D:"],
    "nona_images.ps1": [r"^\$nona = 'C:"],
    "fusionner_par_exposition.ps1": [r"^\$enblend = 'C:", r"^\$multiblend = 'D:"],
    "rendre_lisible.ps1": [r"^\$vips = 'D:"],
}


class TestParametres(unittest.TestCase):
    def test_parametres_presents_et_chemins_en_dur_retires(self):
        for nom, motifs in ATTENDUS.items():
            texte = (SCRIPTS / nom).read_text(encoding="utf-8")
            with self.subTest(nom):
                for m in motifs:
                    self.assertRegex(texte, re.compile(m, re.MULTILINE))
                for m in INTERDITS[nom]:
                    self.assertNotRegex(texte, re.compile(m, re.MULTILINE))

    def test_sans_accent(self):
        for nom in ATTENDUS:
            texte = (SCRIPTS / nom).read_text(encoding="utf-8")
            with self.subTest(nom):
                self.assertTrue(texte.isascii(), "les scripts PowerShell restent sans accents")


if __name__ == "__main__":
    unittest.main()
