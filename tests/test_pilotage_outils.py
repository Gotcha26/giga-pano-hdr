"""Tests de pilotage.outils : détection des outils, versions, commandes d'installation."""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pilotage import outils  # noqa: E402
from pilotage.couleurs import Couleurs  # noqa: E402


def outil_vips():
    return outils.Outil("vips", "libvips", "vips.exe", ["--version"], r"vips-([\d.]+)", [], None, None, None)


class TestDetecter(unittest.TestCase):
    def test_trouve_avec_version(self):
        lancer = lambda cmd, **k: SimpleNamespace(returncode=0, stdout="vips-8.18.7-Tue\n", stderr="")
        e = outils.detecter(outil_vips(), {}, which=lambda n: r"C:\bin\vips.exe", lancer=lancer)
        self.assertEqual((e.chemin, e.version, e.present), (r"C:\bin\vips.exe", "8.18.7", True))

    def test_config_prioritaire(self):
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            chemin = f.name
        lancer = lambda *a, **k: SimpleNamespace(returncode=0, stdout="vips-8.1", stderr="")
        e = outils.detecter(outil_vips(), {"vips": chemin}, which=lambda n: "ailleurs", lancer=lancer)
        self.assertEqual(e.chemin, chemin)

    def test_absent(self):
        e = outils.detecter(outil_vips(), {}, which=lambda n: None)
        self.assertEqual((e.chemin, e.version, e.present), (None, None, False))

    def test_version_inconnue_si_plantage(self):
        def lancer(cmd, **k):
            raise OSError("boom")
        e = outils.detecter(outil_vips(), {}, which=lambda n: "x.exe", lancer=lancer)
        self.assertEqual((e.chemin, e.version), ("x.exe", None))
        e2 = outils.detecter(outil_vips(), {}, which=lambda n: "x.exe",
                             lancer=lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr=""))
        self.assertIsNone(e2.version)

    def test_version_lue_sur_stderr(self):
        lancer = lambda cmd, **k: SimpleNamespace(returncode=0, stdout="", stderr="vips-8.2.0\n")
        e = outils.detecter(outil_vips(), {}, which=lambda n: "x.exe", lancer=lancer)
        self.assertEqual(e.version, "8.2.0")


class TestDivers(unittest.TestCase):
    def test_cles_attendues(self):
        self.assertEqual([o.cle for o in outils.OUTILS],
                         ["hugin", "enblend", "multiblend", "vips", "exiftool", "python", "pillow", "pwsh"])

    def test_resume_et_installation(self):
        etats = [outils.Etat(o, "x" if o.cle != "vips" else None, None) for o in outils.OUTILS]
        r = outils.resume(etats, Couleurs(forcer=False))
        self.assertEqual(r, "Hugin OK · multiblend OK · libvips ABSENT · ExifTool OK")
        self.assertEqual(outils.commande_installation(outils.OUTILS[0]),
                         "winget install --id Hugin.Hugin -e --accept-package-agreements --accept-source-agreements")
        self.assertIsNone(outils.commande_installation(next(o for o in outils.OUTILS if o.cle == "multiblend")))
        self.assertEqual(outils.commande_installation(next(o for o in outils.OUTILS if o.cle == "pillow")),
                         "pip install pillow")

    def test_presets(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "Adobe" / "Lightroom" / "Export Presets").mkdir(parents=True)
            r = outils.dossiers_presets_lightroom(appdata=d)
            self.assertEqual([x[2] for x in r], [True, False])
            self.assertEqual(r[0][1], Path(d) / "Adobe" / "Lightroom" / "Export Presets")


if __name__ == "__main__":
    unittest.main()
