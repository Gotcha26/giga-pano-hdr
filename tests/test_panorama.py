"""Tests du lanceur : exécution des scripts (pilotage.lancer) et menus de panorama.py."""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from pilotage import config, lancer, outils  # noqa: E402
from pilotage.arguments import Arg  # noqa: E402
from pilotage.couleurs import Couleurs  # noqa: E402

C = Couleurs(forcer=False)


def saisies(*valeurs):
    it = iter(valeurs)
    return lambda _invite="": next(it)


def contexte(valeurs, executer=None, etats=None, poste=None, ecrire=None):
    return lancer.Contexte(poste=poste or config.Poste(), panorama=None, etats=etats or [], c=C,
                           lire=saisies(*valeurs), ecrire=ecrire or (lambda *a, **k: None), scripts=SCRIPTS,
                           executer=executer or (lambda *a, **k: SimpleNamespace(returncode=0)))


class TestConstruirePs(unittest.TestCase):
    def test_switch_et_valeurs(self):
        args = [Arg("-Projet", "p", type="pto"), Arg("-BigTiff", "b", type="drapeau"), Arg("-De", "d", type="entier"),
                Arg("-OptionsMultiblend", "o")]
        v = {"-Projet": "a.pto", "-BigTiff": True, "-De": "0", "-OptionsMultiblend": "--cache-threshold=4G"}
        self.assertEqual(lancer.construire_ps(args, v),
                         ["-Projet", "a.pto", "-BigTiff", "-De", "0", "-OptionsMultiblend", "--cache-threshold=4G"])
        with self.assertRaises(ValueError):
            lancer.construire_ps([Arg("sans_tiret", "x")], {"sans_tiret": "1"})


class TestExecution(unittest.TestCase):
    def test_python_annule(self):
        ctx = contexte(["0"], executer=lambda *a, **k: self.fail("ne doit pas exécuter"))
        self.assertIsNone(lancer.python(ctx, "tiffinfo.py", [Arg("image.tif", "i", type="chemin")], None))

    def test_python_lance_et_interruption(self):
        vu = {}

        def executer(cmd, **k):
            vu["cmd"] = cmd
            return SimpleNamespace(returncode=0)
        ctx = contexte(["1", "x.tif", "L"], executer)
        self.assertEqual(lancer.python(ctx, "tiffinfo.py", [Arg("image.tif", "i", type="chemin")], None), 0)
        self.assertEqual(vu["cmd"][1:], [str(SCRIPTS / "tiffinfo.py"), "x.tif"])

        def interrompre(cmd, **k):
            raise KeyboardInterrupt
        ctx2 = contexte(["1", "x.tif", "L"], interrompre)
        self.assertEqual(lancer.python(ctx2, "tiffinfo.py", [Arg("image.tif", "i", type="chemin")], None), 130)

    def test_python_lit_la_declaration_du_script(self):
        vu = {}

        def executer(cmd, **k):
            vu["cmd"] = cmd
            return SimpleNamespace(returncode=0)
        ctx = contexte(["1", "x.tif", "L"], executer)
        self.assertEqual(lancer.python(ctx, "tiffinfo.py"), 0)
        self.assertEqual(vu["cmd"][-1], "x.tif")

    def test_powershell_commande(self):
        vu = {}

        def executer(cmd, **k):
            vu["cmd"] = cmd
            return SimpleNamespace(returncode=0)
        pwsh = next(o for o in outils.OUTILS if o.cle == "pwsh")
        ctx = contexte(["1", "a.pto", "L"], executer, etats=[outils.Etat(pwsh, r"C:\pwsh.exe", "7.6")])
        lancer.powershell(ctx, "nona_images.ps1", [Arg("-Projet", "p", type="pto")], "le dossier de rendu")
        self.assertEqual(vu["cmd"][:5], [r"C:\pwsh.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"])
        self.assertEqual(vu["cmd"][6:], ["-Projet", "a.pto"])

    def test_powershell_prerempli_depuis_les_outils_du_poste(self):
        vu = {}

        def executer(cmd, **k):
            vu["cmd"] = cmd
            return SimpleNamespace(returncode=0)
        ctx = contexte(["L"], executer, poste=config.Poste(outils={"vips": r"D:\O\vips.exe"}))
        lancer.powershell(ctx, "rendre_lisible.ps1", [Arg("-Vips", "v", type="chemin", config="outil:vips")], None)
        self.assertEqual(vu["cmd"][-2:], ["-Vips", r"D:\O\vips.exe"])


class TestLanceur(unittest.TestCase):
    def test_menu_principal_et_quitter(self):
        import panorama
        lignes = []
        ctx = contexte(["0"], ecrire=lignes.append)
        self.assertEqual(len(panorama.menu_principal(ctx)), 7)
        panorama.boucle_principale(ctx, effacer=lambda: None)
        self.assertIn("Aucun panorama courant", "\n".join(lignes))

    def test_nouveau_panorama_cree_et_rend_courant(self):
        import panorama
        with tempfile.TemporaryDirectory() as d:
            T = str(Path(d) / "pano")
            chemin_poste = Path(d) / "config.json"
            ctx = contexte([T, "", "6", "37", "7", "200", "24", "5", "5.8", "20000", "90112"])
            with mock.patch.object(config, "chemin_poste", lambda: chemin_poste):
                panorama.nouveau_panorama(ctx)
            self.assertTrue((Path(T) / "Assemblage-Hugin" / "3_grille").is_dir())
            self.assertEqual(config.charger_panorama(T).pas_v, 5.8)
            self.assertEqual(config.charger_poste(chemin_poste).courant, T)
            self.assertEqual(ctx.panorama.colonnes, 37)

    def test_versions_affiche_un_tableau(self):
        import panorama
        lignes = []
        hugin = next(o for o in outils.OUTILS if o.cle == "hugin")
        ctx = contexte([], etats=[outils.Etat(hugin, r"C:\H\nona.exe", "2025.0.1"),
                                  outils.Etat(outils.OUTILS[3], None, None)], ecrire=lignes.append)
        panorama.versions(ctx)
        texte = "\n".join(lignes)
        self.assertIn("2025.0.1", texte)
        self.assertIn("ABSENT", texte)

    def test_installer_affiche_la_commande_et_n_execute_pas_sans_accord(self):
        import panorama
        lignes = []
        exif = next(o for o in outils.OUTILS if o.cle == "exiftool")
        ctx = contexte([""], executer=lambda *a, **k: self.fail("refusé"), etats=[outils.Etat(exif, None, None)],
                       ecrire=lignes.append)
        panorama.installer(ctx)
        self.assertIn("winget install --id OliverBetz.ExifTool", "\n".join(lignes))


if __name__ == "__main__":
    unittest.main()
