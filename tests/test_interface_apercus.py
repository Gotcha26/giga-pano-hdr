"""Tests de interface.apercus : liste des images, cache et aperçus réduits par libvips."""

import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from interface import apercus  # noqa: E402


class TestApercus(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.cache = self.tmp / "cache"

    def _fichier(self, nom, mtime=None, contenu=b"x"):
        f = self.tmp / nom
        f.write_bytes(contenu)
        if mtime is not None:
            os.utime(f, (mtime, mtime))
        return f

    def _lanceur(self, vu, code=0, stderr=""):
        def lancer(cmd, **k):
            vu.append((cmd, k))
            if code == 0:
                Path(cmd[3].split("[")[0]).write_bytes(b"jpg")
            return SimpleNamespace(returncode=code, stderr=stderr)
        return lancer

    def test_dossier_absent_liste_vide(self):
        self.assertEqual(apercus.lister_images(None), [])
        self.assertEqual(apercus.lister_images(""), [])
        self.assertEqual(apercus.lister_images(self.tmp / "n_existe" / "pas"), [])

    def test_fichier_au_lieu_d_un_dossier_liste_vide(self):
        f = self._fichier("a.tif")
        self.assertEqual(apercus.lister_images(f), [])

    def test_liste_filtre_et_trie(self):
        self._fichier("a.tif", 1000)
        self._fichier("b.jpg", 2000)
        self._fichier("c.txt", 3000)
        (self.tmp / "d.png").mkdir()
        images = apercus.lister_images(self.tmp)
        self.assertEqual([i.chemin.name for i in images], ["b.jpg", "a.tif"])
        self.assertEqual(images[0].taille, 1)
        self.assertEqual(images[0].modifie, 2000)

    def test_extensions_insensibles_a_la_casse(self):
        self._fichier("A.TIF")
        self._fichier("B.Jpeg")
        self.assertEqual(sorted(i.chemin.name for i in apercus.lister_images(str(self.tmp))), ["A.TIF", "B.Jpeg"])

    def test_permission_refusee_liste_vide(self):
        with mock.patch.object(Path, "iterdir", side_effect=PermissionError):
            self.assertEqual(apercus.lister_images(self.tmp), [])

    def test_chemin_cache_change_avec_la_date(self):
        f = self._fichier("a.tif", 1000)
        c1 = apercus.chemin_cache(f, racine=self.cache)
        os.utime(f, (1, 2))
        c2 = apercus.chemin_cache(f, racine=self.cache)
        self.assertNotEqual(c1, c2)
        self.assertEqual(c1.parent, self.cache)
        self.assertEqual(c1.suffix, ".jpg")

    def test_dossier_cache_localappdata_puis_repli(self):
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": str(self.tmp)}):
            self.assertEqual(apercus.dossier_cache(), self.tmp / "giga-pano-hdr" / "apercus")
        env = {k: v for k, v in os.environ.items() if k != "LOCALAPPDATA"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(apercus.dossier_cache(), Path.home() / ".giga-pano-hdr" / "apercus")

    def test_apercu_lance_vips_une_fois_puis_relit_le_cache(self):
        f = self._fichier("a.tif")
        vu = []
        lancer = self._lanceur(vu)
        a1 = apercus.apercu(f, "vips.exe", lancer=lancer, racine=self.cache)
        a2 = apercus.apercu(f, "vips.exe", lancer=lancer, racine=self.cache)
        self.assertEqual(a1, a2)
        self.assertTrue(a1.is_file())
        self.assertEqual(len(vu), 1)
        cmd = vu[0][0]
        self.assertEqual(cmd[:3], ["vips.exe", "thumbnail", str(f)])
        self.assertEqual(cmd[3], f"{a1.with_suffix('.part.jpg')}[Q=85]")
        self.assertEqual(cmd[-1], "2000")
        self.assertTrue(vu[0][1]["capture_output"])
        self.assertTrue(vu[0][1]["text"])
        self.assertEqual(vu[0][1]["timeout"], 120)
        self.assertEqual([p.name for p in self.cache.iterdir()], [a1.name])     # le .part a été renommé

    def test_apercu_echec_apres_ecriture_ne_laisse_aucun_jpeg(self):
        f = self._fichier("a.tif")

        def lancer(cmd, **k):
            Path(cmd[3].split("[")[0]).write_bytes(b"jpg tronque")
            return SimpleNamespace(returncode=1, stderr="coupé")
        with self.assertRaises(RuntimeError):
            apercus.apercu(f, "vips.exe", lancer=lancer, racine=self.cache)
        self.assertEqual(list(self.cache.glob("*.jpg")), [])

    def test_partiel_indelebile_ne_masque_pas_l_erreur_de_vips(self):
        f = self._fichier("a.tif")
        with mock.patch.object(Path, "unlink", side_effect=PermissionError("verrouillé")):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                apercus.apercu(f, "vips.exe", lancer=self._lanceur([], code=1, stderr="boom"), racine=self.cache)

    def test_apercu_delai_depasse_leve_en_francais(self):
        f = self._fichier("a.tif")
        vu = []

        def lancer(cmd, **k):
            vu.append(k)
            Path(cmd[3].split("[")[0]).write_bytes(b"debut")
            raise subprocess.TimeoutExpired(cmd, k["timeout"])
        with self.assertRaises(RuntimeError) as ctx:
            apercus.apercu(f, "vips.exe", lancer=lancer, racine=self.cache, delai=7)
        self.assertEqual(vu[0]["timeout"], 7)
        self.assertIn("7 s", str(ctx.exception))
        self.assertEqual(list(self.cache.glob("*.jpg")), [])

    def test_apercus_concurrents_un_seul_appel_vips(self):
        f = self._fichier("a.tif")
        vu, entre = [], threading.Event()

        def lancer(cmd, **k):
            vu.append(cmd)
            entre.set()
            time.sleep(0.2)                     # laisse le second fil arriver sur le verrou
            Path(cmd[3].split("[")[0]).write_bytes(b"jpg")
            return SimpleNamespace(returncode=0, stderr="")
        resultats = []

        def tache():
            resultats.append(apercus.apercu(f, "vips.exe", lancer=lancer, racine=self.cache))
        fils = [threading.Thread(target=tache) for _ in range(2)]
        fils[0].start()
        entre.wait(5)
        fils[1].start()
        for t in fils:
            t.join(5)
        self.assertEqual(len(vu), 1)
        self.assertEqual(len(resultats), 2)
        self.assertEqual(resultats[0], resultats[1])

    def test_liste_ignore_un_fichier_illisible(self):
        self._fichier("a.tif", 1000)
        self._fichier("b.tif", 2000)
        stat_reel = Path.stat

        def stat(self_, *a, **k):
            if self_.name == "a.tif":
                raise PermissionError("verrouillé")
            return stat_reel(self_, *a, **k)
        with mock.patch.object(Path, "stat", stat):
            images = apercus.lister_images(self.tmp)
        self.assertEqual([i.chemin.name for i in images], ["b.tif"])

    def test_apercu_largeur_personnalisee(self):
        f = self._fichier("a.tif")
        vu = []
        apercus.apercu(f, "vips.exe", largeur=800, lancer=self._lanceur(vu), racine=self.cache)
        self.assertEqual(vu[0][0][-1], "800")

    def test_apercu_echec_vips_leve(self):
        f = self._fichier("a.tif")
        with self.assertRaises(RuntimeError) as ctx:
            apercus.apercu(f, "vips.exe", lancer=self._lanceur([], code=1, stderr="boom"), racine=self.cache)
        self.assertIn("boom", str(ctx.exception))

    def test_apercu_echec_sans_stderr_message_de_repli(self):
        f = self._fichier("a.tif")
        with self.assertRaises(RuntimeError) as ctx:
            apercus.apercu(f, "vips.exe", lancer=self._lanceur([], code=1), racine=self.cache)
        self.assertTrue(str(ctx.exception))

    def test_vider_cache(self):
        self.assertEqual(apercus.vider_cache(racine=self.cache), 0)
        self.cache.mkdir()
        (self.cache / "a.jpg").write_bytes(b"1")
        (self.cache / "b.jpg").write_bytes(b"2")
        (self.cache / "autre.txt").write_bytes(b"3")
        self.assertEqual(apercus.vider_cache(racine=self.cache), 2)
        self.assertEqual([p.name for p in self.cache.iterdir()], ["autre.txt"])


if __name__ == "__main__":
    unittest.main()
