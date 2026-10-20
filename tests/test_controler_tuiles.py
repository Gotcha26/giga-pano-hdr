"""Tests de controler_tuiles.py : adresse de la page, --box, et serveur local (page, pyramides, rien d'autre)."""

import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import controler_tuiles as ct  # noqa: E402


def pyramide(dossier, nom):
    """<nom>.dzi et une tuile <nom>_files/0/0_0.webp ; retourne le chemin du .dzi."""
    dzi = Path(dossier) / f"{nom}.dzi"
    dzi.write_text("<Image/>", encoding="utf-8")
    (Path(dossier) / f"{nom}_files" / "0").mkdir(parents=True)
    (Path(dossier) / f"{nom}_files" / "0" / "0_0.webp").write_bytes(b"RIFF")
    return dzi


class TestAdresse(unittest.TestCase):
    def test_une_source(self):
        self.assertEqual(ct.adresse(8000, r"D:\T\hdr.dzi"), "http://127.0.0.1:8000/?hdr=hdr/hdr.dzi")

    def test_deux_sources_cadre_et_fondu(self):
        url = ct.adresse(8000, r"D:\T\hdr.dzi", r"D:\T\complet.dzi", [0.016135, 0.012329, 0.983864])
        self.assertEqual(url, "http://127.0.0.1:8000/?hdr=hdr/hdr.dzi&full=complet/complet.dzi"
                              "&box=0.016135,0.012329,0.983864&fondu=auto")
        self.assertNotIn("fondu", ct.adresse(8000, "h.dzi", "c.dzi", fondu="curseur"))

    def test_box(self):
        self.assertIsNone(ct.lire_box(""))
        self.assertEqual(ct.lire_box("0.1,0.2,0.9"), [0.1, 0.2, 0.9])
        with self.assertRaises(ValueError):
            ct.lire_box("0.1,0.2")


class TestServeur(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        (base / "a").mkdir()
        (base / "b").mkdir()
        (base / "secret.txt").write_text("non", encoding="utf-8")
        self.srv = ct.serveur(pyramide(base / "a", "hdr"), pyramide(base / "b", "complet"))
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()

    def lire(self, chemin):
        with urllib.request.urlopen(self.base + chemin, timeout=5) as r:
            return r.status, r.headers.get_content_type(), r.read()

    def test_page_openseadragon_et_pyramides(self):
        statut, _, page = self.lire("/?hdr=hdr/hdr.dzi")
        self.assertEqual(statut, 200)
        self.assertIn(b"openseadragon.min.js", page)
        self.assertEqual(self.lire("/openseadragon/openseadragon.min.js")[0], 200)
        self.assertEqual(self.lire("/hdr/hdr.dzi")[1], "application/xml")
        self.assertEqual(self.lire("/complet/complet_files/0/0_0.webp")[1], "image/webp")

    def test_rien_hors_des_dossiers_servis(self):
        for chemin in ("/hdr/../secret.txt", "/hdr/..%2F..%2Fsecret.txt", "/hdr/..%5Csecret.txt", "/complet/C:%5Csecret.txt"):
            with self.subTest(chemin), self.assertRaises(urllib.error.HTTPError) as e:
                self.lire(chemin)
            self.assertEqual(e.exception.code, 404)
            e.exception.close()


if __name__ == "__main__":
    unittest.main()
