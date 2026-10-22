"""Tests de pilotage.arguments : déclaration des arguments d'un script et menu de pilotage."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pilotage import arguments, config  # noqa: E402
from pilotage.couleurs import Couleurs  # noqa: E402

C = Couleurs(forcer=False)


def saisies(*valeurs):
    it = iter(valeurs)
    return lambda _invite="": next(it)


ARGS = [
    arguments.Arg("optimise.pto", "Projet optimisé", type="pto", config="maitre", phase="3_optimisation"),
    arguments.Arg("sortie.pto", "Projet à écrire", type="pto"),
    arguments.Arg("PAS_H", "Pas horizontal (°)", type="nombre", config="pas_h", defaut=5.0),
    arguments.Arg("PAS_V", "Pas vertical (°)", type="nombre", config="pas_v", defaut=5.8),
    arguments.Arg("SEUIL_CP", "Points minimum", type="entier", defaut=30),
    arguments.Arg("--rapport", "Analyse seule", type="drapeau"),
    arguments.Arg("--images", "Taille LARG HAUT", nargs=2),
]
PANO = config.Panorama(T=r"D:\T", P=r"D:\T\A", colonnes=40, pas_h=5.0, pas_v=6.1, maitre=r"3_optimisation\m.pto")


class TestArgv(unittest.TestCase):
    def test_positionnels_options_et_arret(self):
        v = {"optimise.pto": "a.pto", "sortie.pto": "b.pto", "PAS_H": "5.0", "PAS_V": "", "SEUIL_CP": "30",
             "--rapport": True, "--images": "3456 5184"}
        self.assertEqual(arguments.construire_argv(ARGS, v),
                         ["a.pto", "b.pto", "5.0", "--rapport", "--images", "3456", "5184"])

    def test_option_vide_et_drapeau_faux_omis(self):
        v = {"optimise.pto": "a.pto", "sortie.pto": "b.pto", "--rapport": False, "--images": ""}
        self.assertEqual(arguments.construire_argv(ARGS, v), ["a.pto", "b.pto"])

    def test_appliquer_lit_relie_au_panorama_sans_toucher_la_declaration(self):
        relies = arguments.appliquer_lit(ARGS, {"sortie.pto": "hdr_pto"})
        self.assertEqual(relies[1].config, "hdr_pto")
        self.assertIsNone(ARGS[1].config)                         # copie : la déclaration est intacte
        self.assertEqual([a.nom for a in relies], [a.nom for a in ARGS])
        self.assertEqual(relies[:1] + relies[2:], ARGS[:1] + ARGS[2:])
        self.assertEqual(arguments.appliquer_lit(ARGS, {}), ARGS)
        with self.assertRaisesRegex(ValueError, "non déclaré : -Absent"):
            arguments.appliquer_lit(ARGS, {"-Absent": "maitre"})

    def test_obligatoire_deduit(self):
        self.assertTrue(ARGS[0].obligatoire)
        self.assertFalse(ARGS[2].obligatoire)
        self.assertFalse(ARGS[5].obligatoire)
        self.assertTrue(ARGS[5].option)


class TestDeclaration(unittest.TestCase):
    def test_lire_declaration_sans_executer(self):
        args, ecrit, doc = arguments.lire_declaration(Path(__file__).resolve().parent.parent / "scripts" / "placer_isoles.py")
        self.assertEqual(len(args), 5)
        self.assertEqual((args[0].type, args[0].phase), ("pto", "3_optimisation"))
        self.assertEqual(ecrit, "le projet de sortie")
        self.assertTrue(doc.startswith("Place les images"))

    def test_drapeau_vrai_par_defaut(self):
        a = [arguments.Arg("DOSSIER", "d", type="dossier"), arguments.Arg("--table", "t", type="drapeau", defaut=True)]
        lignes = []
        r = arguments.menu("T", a, None, c=C, lire=saisies("1", "D:\\x", "L"), ecrire=lignes.append, effacer=lambda: None)
        self.assertEqual(r, ["D:\\x", "--table"])


class TestConstantes(unittest.TestCase):
    def test_extraction_et_ecarts(self):
        g = {"COLS": 37, "PAS_V": 5.8, "AUTRE": 1}
        self.assertEqual(arguments.constantes_du_script(g), {"COLS": 37, "PAS_V": 5.8})
        self.assertEqual(arguments.ecarts({"COLS": 37, "PAS_V": 5.8, "PAS_H": 5.0}, PANO),
                         [("COLS", 37, 40), ("PAS_V", 5.8, 6.1)])
        self.assertEqual(arguments.ecarts({"COLS": 37}, None), [])


class TestMenu(unittest.TestCase):
    def menu(self, valeurs, panorama=PANO, constantes=None, args=ARGS):
        lignes = []
        r = arguments.menu("Replace les images isolées.\n\nCONTEXTE…", args, ecrit="le projet de sortie",
                           constantes=constantes, panorama=panorama, c=C, lire=saisies(*valeurs),
                           ecrire=lignes.append, effacer=lambda: None)
        return r, "\n".join(lignes)

    def test_prerempli_et_lancement(self):
        r, texte = self.menu(["2", "s.pto", "L"])
        self.assertEqual(r, [r"D:\T\A\3_optimisation\m.pto", "s.pto", "5.0", "6.1", "30"])
        self.assertIn("Replace les images isolées.", texte)
        self.assertIn("[écrit — le projet de sortie]", texte)

    def test_sans_panorama_affiche_a_saisir(self):
        r, texte = self.menu(["0"], panorama=None)
        self.assertIsNone(r)
        self.assertIn("à saisir", texte)

    def test_refus_si_obligatoire_vide(self):
        r, texte = self.menu(["L", "", "0"])
        self.assertIsNone(r)
        self.assertIn("obligatoire", texte.lower())

    def test_drapeau_et_nargs(self):
        r, _ = self.menu(["2", "s.pto", "6", "7", "3456 5184", "L"])
        self.assertEqual(r[-4:], ["--rapport", "--images", "3456", "5184"])

    def test_ecart_constante_demande_confirmation(self):
        r, texte = self.menu(["2", "s.pto", "L", ""], constantes={"COLS": 37})   # ENTRÉE = Non
        self.assertIsNone(r)
        self.assertIn("COLS", texte)
        r2, _ = self.menu(["2", "s.pto", "L", "o"], constantes={"COLS": 37})
        self.assertIsNotNone(r2)

    def test_annulation_saisie_garde_la_valeur(self):
        r, _ = self.menu(["3", "x", "2", "s.pto", "L"])
        self.assertEqual(r[2], "5.0")

    def test_liste_pto_du_dossier_de_phase(self):
        with tempfile.TemporaryDirectory() as d:
            P = Path(d)
            (P / "3_optimisation").mkdir()
            (P / "3_optimisation" / "opt4.pto").write_text("p")
            pano = config.Panorama(T=d, P=str(P))
            lignes = []
            r = arguments.menu("T", ARGS[:2], None, panorama=pano, c=C,
                               lire=saisies("1", "1", "2", "s.pto", "L"), ecrire=lignes.append, effacer=lambda: None)
            self.assertEqual(r[0], str(P / "3_optimisation" / "opt4.pto"))
            self.assertIn("[lecture seule]", "\n".join(lignes))


class TestValeursInitialesEtVerification(unittest.TestCase):
    def test_valeurs_initiales_memorisees_avant_panorama(self):
        p = config.Panorama(T="D:\\x", P="D:\\x\\P", largeur_hdr=20000)
        args = [arguments.Arg("-Largeur", "l", type="entier", config="largeur_hdr"),
                arguments.Arg("-Nom", "n", defaut="panorama")]
        v = arguments.valeurs_initiales(args, p, memorises={"-Nom": "vue"})
        self.assertEqual(v, {"-Largeur": "20000", "-Nom": "vue"})
        self.assertIs(arguments._valeurs_initiales, arguments.valeurs_initiales)

    def test_verifier_rend_les_trois_familles_de_messages(self):
        args = [arguments.Arg("a.pto", "a", type="pto"), arguments.Arg("b.pto", "b", type="pto")]
        self.assertTrue(any("obligatoire" in m for m in arguments.verifier(args, {"a.pto": "", "b.pto": ""})))
        self.assertTrue(any("en entier" in m for m in arguments.verifier(args, {"a.pto": r"rel\x.pto", "b.pto": ""})))
        self.assertTrue(any("positionnels" in m for m in arguments.verifier(args, {"a.pto": "", "b.pto": r"D:\b.pto"})))
        self.assertEqual(arguments.verifier(args, {"a.pto": r"D:\a.pto", "b.pto": r"D:\b.pto"}), [])

    def test_verifier_accepte_le_relatif_sans_chemins_absolus(self):
        args = [arguments.Arg("a.pto", "a", type="pto")]
        self.assertEqual(arguments.verifier(args, {"a.pto": r"rel\x.pto"}, chemins_absolus=False), [])


if __name__ == "__main__":
    unittest.main()
