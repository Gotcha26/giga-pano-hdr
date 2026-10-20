"""Tests de empaqueter.py sur deux pyramides factices : dossier, panorama.json, ZIP, refus."""

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import empaqueter as emp  # noqa: E402
from pilotage import arguments  # noqa: E402


def pyramide(base, largeur, hauteur):
    """<base>.dzi (avec l'espace de noms Deep Zoom) et une tuile <base>_files/0/0_0.webp."""
    base = Path(base)
    (base.parent / f"{base.name}_files" / "0").mkdir(parents=True)
    (base.parent / f"{base.name}_files" / "0" / "0_0.webp").write_bytes(b"x")
    base.with_suffix(".dzi").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><Image xmlns="http://schemas.microsoft.com/deepzoom/2008" Format="webp"'
        f' Overlap="0" TileSize="512"><Size Height="{hauteur}" Width="{largeur}"/></Image>', encoding="utf-8")
    return base.with_suffix(".dzi")


class TestEmpaqueter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bac = Path(self.tmp.name)
        self.hdr = pyramide(self.bac / "src_h" / "hdr", 18822, 4235)
        self.complet = pyramide(self.bac / "src_c" / "complet", 84804, 19081)
        self.sortie = self.bac / "galerie"

    def tearDown(self):
        self.tmp.cleanup()

    def test_dossier_manifeste_et_zip(self):
        cible, archive, _ = emp.empaqueter("pano-test", self.hdr, self.complet, self.sortie, "Panorama d'essai",
                                           emp.lire_box("0,0.000007,0.999995"))
        octets = (cible / "panorama.json").read_bytes()
        self.assertEqual(octets[:1], b"{")                           # sans BOM
        m = json.loads(octets.decode("utf-8"))
        self.assertEqual(m, {"version": 1, "titre": "Panorama d'essai",
                             "hdr": {"dzi": "hdr/hdr.dzi", "width": 18822, "height": 4235},
                             "full": {"dzi": "complet/complet.dzi", "width": 84804, "height": 19081},
                             "box": [0.0, 0.000007, 0.999995]})
        for f in ("hdr/hdr.dzi", "hdr/hdr_files/0/0_0.webp", "complet/complet.dzi", "complet/complet_files/0/0_0.webp"):
            self.assertTrue((cible / f).is_file(), f)
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(sorted(z.namelist()), sorted(
                f"pano-test/{f}" for f in ("panorama.json", "hdr/hdr.dzi", "hdr/hdr_files/0/0_0.webp",
                                           "complet/complet.dzi", "complet/complet_files/0/0_0.webp")))
            self.assertTrue(all(i.compress_type == zipfile.ZIP_STORED for i in z.infolist()))

    def test_sans_zip(self):
        _, archive, _ = emp.empaqueter("pano-test", self.hdr, self.complet, self.sortie, zipper=False)
        self.assertIsNone(archive)
        self.assertFalse((self.sortie / "pano-test.zip").exists())

    def test_refus_sans_rien_ecrire(self):
        cas = [("mauvais nom!", self.hdr, "nom invalide"), ("ok\n", self.hdr, "nom invalide"),
               ("ok", self.bac / "absent.dzi", "introuvable")]
        for nom, hdr, motif in cas:
            with self.subTest(nom=nom, hdr=hdr), self.assertRaisesRegex(emp.Refus, motif):
                emp.empaqueter(nom, hdr, self.complet, self.sortie)
        self.assertFalse(self.sortie.exists())

    def test_nom_deja_present_refuse(self):
        emp.empaqueter("pano-test", self.hdr, self.complet, self.sortie, zipper=False)
        with self.assertRaisesRegex(emp.Refus, "existe déjà"):
            emp.empaqueter("pano-test", self.hdr, self.complet, self.sortie)

    def test_box(self):
        self.assertEqual(emp.lire_box("0.016135,0.012329,0.983864"), [0.016135, 0.012329, 0.983864])
        for texte, motif in [("0.5,0,0.8", "hors du cadre"), ("0.5,0,0.52", "hors du cadre"),
                             ("0.5,abc,0.5", "illisible"), ("0.5,0.5", "trois nombres")]:
            with self.subTest(texte), self.assertRaisesRegex(emp.Refus, motif):
                emp.lire_box(texte)

    def test_le_lanceur_lit_ce_que_le_script_ecrit(self):
        _, ecrit, _ = arguments.lire_declaration(SCRIPTS / "empaqueter.py")
        self.assertIn("<Nom>.zip", ecrit)


if __name__ == "__main__":
    unittest.main()
