"""Tests issus de la relecture finale : chacun reproduit un défaut constaté avant sa correction."""

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from pilotage import arguments, declarations_ps, lancer, menu, outils  # noqa: E402
from pilotage.couleurs import Couleurs  # noqa: E402

C = Couleurs(forcer=False)


def saisies(*valeurs):
    it = iter(valeurs)
    return lambda _invite="": next(it)


class TestC1EntreeRedirigee(unittest.TestCase):
    """Sous Windows, NUL est un périphérique caractère : isatty() ment. Le menu ne doit pas s'ouvrir."""

    def test_stdin_devnull_sans_menu_ni_plantage_import(self):
        r = subprocess.run([sys.executable, str(SCRIPTS / "tiffinfo.py")], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=60, cwd=SCRIPTS)
        self.assertNotIn("PILOTAGE", r.stdout + r.stderr)
        self.assertNotIn("No module named", r.stderr)
        self.assertNotIn("EOFError", r.stderr)

    def test_terminal_interactif_faux_sans_console(self):
        with open(os.devnull) as nul:
            self.assertFalse(arguments.terminal_interactif(stdin=nul, stdout=sys.stdout))


class TestPiloterGardes(unittest.TestCase):
    def test_import_depuis_un_autre_programme_ne_declenche_rien(self):
        # sys.argv désigne un autre fichier que le script importé (ex. python -m unittest) : pas de menu
        with mock.patch.object(sys, "argv", ["autre_programme.py"]), \
                mock.patch.object(arguments, "terminal_interactif", lambda **k: True), \
                mock.patch.object(arguments, "menu", side_effect=AssertionError("menu ouvert")):
            arguments.piloter("doc", [], None, {"__file__": str(SCRIPTS / "ecart_paires.py")})

    def test_variable_d_environnement_sans_menu(self):
        with mock.patch.object(sys, "argv", [str(SCRIPTS / "tiffinfo.py")]), \
                mock.patch.object(arguments, "terminal_interactif", lambda **k: True), \
                mock.patch.dict(os.environ, {arguments.SANS_MENU: "1"}), \
                mock.patch.object(arguments, "menu", side_effect=AssertionError("menu ouvert")):
            arguments.piloter("doc", [], None, {"__file__": str(SCRIPTS / "tiffinfo.py")})

    def test_le_lanceur_pose_la_variable_pour_l_enfant(self):
        vu = {}

        def executer(cmd, **k):
            vu["env"] = k.get("env") or {}
            return SimpleNamespace(returncode=0)
        ctx = lancer.Contexte(poste=SimpleNamespace(outils={}), panorama=None, etats=[], c=C, lire=saisies("L"),
                              ecrire=lambda *a, **k: None, scripts=SCRIPTS, executer=executer)
        lancer.python(ctx, "cadrage_lightroom.py")
        self.assertEqual(vu["env"].get(arguments.SANS_MENU), "1")


class TestI1ObligatoiresPowerShell(unittest.TestCase):
    def test_parametres_mandatory_declares_obligatoires(self):
        for nom, (args, _) in declarations_ps.PS.items():
            texte = (SCRIPTS / nom).read_text(encoding="utf-8")
            m = re.search(r"param\((.*?)^\)", texte, re.S | re.M) or re.search(r"param\((.*?)\)\s*$", texte, re.M)
            self.assertIsNotNone(m, nom)
            mandatory = set(re.findall(r"Mandatory = \$true\)\]\[[\w\[\]]+\]\$(\w+)", m.group(1)))
            with self.subTest(nom):
                for a in args:
                    if a.nom.lstrip("-") in mandatory and a.defaut is None:
                        self.assertTrue(a.obligatoire, f"{nom} {a.nom} est Mandatory dans le .ps1")


class TestI2PositionnelsFacultatifs(unittest.TestCase):
    CAS = {"ecart_paires.py": ["COL_DEBUT", "COL_FIN"], "comparer_rendus.py": ["PERIODE_PX"],
           "propager_geometrie.py": ["LARG_IMAGE", "HAUT_IMAGE"], "mesurer_bandes_ciel.py": ["X_DEBUT", "X_FIN"]}

    def test_positionnels_facultatifs_non_obligatoires(self):
        for nom, facultatifs in self.CAS.items():
            args, _, _ = arguments.lire_declaration(SCRIPTS / nom)
            par_nom = {a.nom: a for a in args}
            with self.subTest(nom):
                for f in facultatifs:
                    self.assertFalse(par_nom[f].obligatoire, f)

    def test_voir_positions_pas_avec_defaut(self):
        args, _, _ = arguments.lire_declaration(SCRIPTS / "voir_positions.py")
        par_nom = {a.nom: a for a in args}
        self.assertEqual((par_nom["PAS_H"].defaut, par_nom["PAS_V"].defaut), (5.0, 5.8))


class TestI3PositionnelApresVide(unittest.TestCase):
    ARGS = [arguments.Arg("image.tif", "i", type="chemin"),
            arguments.Arg("X_DEBUT", "x0", type="entier", obligatoire=False),
            arguments.Arg("X_FIN", "x1", type="entier", obligatoire=False)]

    def test_refus_si_un_positionnel_renseigne_suit_un_vide(self):
        lignes = []
        r = arguments.menu("T", self.ARGS, None, c=C, lire=saisies("1", "a.tif", "3", "4000", "L", "", "0"),
                           ecrire=lignes.append, effacer=lambda: None)
        self.assertIsNone(r)
        self.assertIn("X_FIN", "\n".join(lignes))
        self.assertIn("X_DEBUT", "\n".join(lignes))


class TestI4ListesPowerShell(unittest.TestCase):
    def test_construire_ps_liste_un_element_par_valeur(self):
        a = [arguments.Arg("-Groupes", "g", type="liste")]
        self.assertEqual(lancer.construire_ps(a, {"-Groupes": "1 2"}), ["-Groupes", "1", "2"])

    def test_groupes_et_options_declares_en_liste(self):
        args, _ = declarations_ps.PS["fusionner_par_exposition.ps1"]
        par_nom = {a.nom: a for a in args}
        self.assertEqual(par_nom["-Groupes"].type, "liste")
        self.assertEqual(par_nom["-OptionsFusionneur"].type, "liste")
        args2, _ = declarations_ps.PS["rendre_projet.ps1"]
        self.assertEqual({a.nom: a for a in args2}["-OptionsMultiblend"].type, "liste")


class TestI5Navigation(unittest.TestCase):
    def test_une_entree_de_navigation_ne_porte_pas_de_mention_d_effet(self):
        e = menu.Entree("Préparer", "Phase 0", action=lambda ctx: None, navigation=True)
        self.assertEqual(menu.libelles([e], None), ["Préparer — Phase 0"])

    def test_menu_principal_sans_lecture_seule(self):
        import panorama
        ctx = lancer.Contexte(poste=SimpleNamespace(outils={}), panorama=None, etats=[], c=C)
        self.assertNotIn("[lecture seule]", "\n".join(menu.libelles(panorama.menu_principal(ctx), ctx)))


class TestI6Pillow(unittest.TestCase):
    def test_pillow_absent_si_import_echoue(self):
        pillow = next(o for o in outils.OUTILS if o.cle == "pillow")
        e = outils.detecter(pillow, {}, lancer=lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="ModuleNotFoundError"))
        self.assertFalse(e.present)
        self.assertTrue(outils.commande_installation(pillow).endswith("-m pip install pillow"))

    def test_pillow_present_si_version_lue(self):
        pillow = next(o for o in outils.OUTILS if o.cle == "pillow")
        e = outils.detecter(pillow, {}, lancer=lambda *a, **k: SimpleNamespace(returncode=0, stdout="12.2.0\n", stderr=""))
        self.assertTrue(e.present)
        self.assertEqual(e.version, "12.2.0")


class TestCompteDesScripts(unittest.TestCase):
    """L'INDEX annonçait « 43 scripts » alors que le dossier en compte davantage : le nombre suit le dossier."""

    def test_nombre_annonce_par_l_index(self):
        lanceurs = {"panorama.py", "panorama_web.py"}
        fichiers = [p for ext in ("*.py", "*.ps1", "*.cmd") for p in SCRIPTS.glob(ext) if p.name not in lanceurs]
        index = (SCRIPTS / "INDEX.md").read_text(encoding="utf-8")
        annonces = {int(n) for n in re.findall(r"[Ll]es (\d+) (?:scripts|fichiers)", index)}
        self.assertEqual(annonces, {len(fichiers)})


if __name__ == "__main__":
    unittest.main()
