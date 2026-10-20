"""Tests de pilotage.couleurs et pilotage.menu (rendu des menus déclaratifs, saisies)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pilotage import menu as m  # noqa: E402
from pilotage.couleurs import Couleurs  # noqa: E402

C = Couleurs(forcer=False)


def saisies(*valeurs):
    """Un `lire` de test : comme input(), il reçoit l'invite et rend la saisie suivante."""
    it = iter(valeurs)
    return lambda _invite="": next(it)


def entrees_exemple():
    return [
        m.Entree("Générer la grille", "generer_pto.py", effet=r"3_grille\pano_grille.pto",
                 action=lambda ctx: ctx.append("grille"), section="PHASE 3"),
        m.Entree("Points de contrôle", "dans Hugin : Photos → CPFind", action=None, section="PHASE 3"),
        m.Entree("Vérifier la grille", "diagnostic_cp.py", action=lambda ctx: ctx.append("diag"), section="PHASE 3"),
        m.Entree("Tuiler", "tuiler.ps1", effet="7_tuiles", action=lambda ctx: None,
                 disponible=lambda ctx: False, raison="libvips absent", section="PHASE 7"),
        m.Entree("Cachée", action=lambda ctx: None, disponible=lambda ctx: False, masquer=True, section="PHASE 7"),
    ]


class TestLibelles(unittest.TestCase):
    def test_alignement_par_section_et_effet(self):
        l = m.libelles(entrees_exemple(), ctx=[])
        self.assertEqual(l[0], "Générer la grille  — generer_pto.py  [écrit — 3_grille\\pano_grille.pto]")
        self.assertEqual(l[2], "Vérifier la grille — diagnostic_cp.py  [lecture seule]")
        self.assertTrue(l[1].startswith("Points de contrôle — dans Hugin"))
        self.assertNotIn("[", l[1])
        self.assertEqual(l[3], "Tuiler — tuiler.ps1  [écrit — 7_tuiles]")


class TestNumerotation(unittest.TestCase):
    def test_numeros_sur_entrees_actives_seulement(self):
        self.assertEqual(m.numeroter(entrees_exemple(), ctx=[]), [1, None, 2, None, None])

    def test_rendu_cadre_a_droite_au_dela_de_neuf(self):
        entrees = [m.Entree(f"E{i}", action=lambda ctx: None) for i in range(11)]
        lignes = []
        table = m.rendre(entrees, ctx=None, c=C, ecrire=lignes.append)
        texte = "\n".join(lignes)
        self.assertIn("   1. E0", texte)
        self.assertIn("  11. E10", texte)
        self.assertIn("   0. Retour", texte)
        self.assertEqual(set(table), {str(i) for i in range(1, 12)})

    def test_rendu_grise_et_masque(self):
        lignes = []
        m.rendre(entrees_exemple(), ctx=[], c=C, ecrire=lignes.append)
        texte = "\n".join(lignes)
        self.assertIn("–. Tuiler", texte)
        self.assertIn("[libvips absent]", texte)
        self.assertNotIn("Cachée", texte)
        self.assertIn("PHASE 3", texte)
        self.assertIn("PHASE 7", texte)


class TestBoucle(unittest.TestCase):
    def test_choix_puis_retour(self):
        ctx, lignes = [], []
        lire = saisies("2", "", "0")
        m.boucle("TEST", entrees_exemple(), ctx, C, lire=lire, ecrire=lignes.append, effacer=lambda: None)
        self.assertEqual(ctx, ["diag"])

    def test_pas_de_pause_apres_un_sous_menu_ni_une_action_sans_pause(self):
        vu = []
        entrees = [m.Entree("Sous-menu", action=lambda ctx: vu.append("sous-menu"), navigation=True),
                   m.Entree("Script", action=m.sans_pause(lambda ctx: vu.append("script"))),
                   m.Entree("Tableau", action=lambda ctx: vu.append("tableau"))]
        lues = []
        valeurs = iter(["1", "2", "3", "", "0"])     # seule l'action « Tableau » attend Entrée

        def lire(invite=""):
            lues.append(invite)
            return next(valeurs)
        m.boucle("TEST", entrees, [], C, lire=lire, ecrire=lambda *a: None, effacer=lambda: None)
        self.assertEqual(vu, ["sous-menu", "script", "tableau"])
        self.assertEqual(sum("Entrée" in i for i in lues), 1)

    def test_saisie_invalide_reaffiche(self):
        ctx, lignes = [], []
        lire = saisies("9", "", "0")
        m.boucle("TEST", entrees_exemple(), ctx, C, lire=lire, ecrire=lignes.append, effacer=lambda: None)
        self.assertIn('Choix invalide : "9"', "\n".join(lignes))
        self.assertEqual(ctx, [])


class TestSaisies(unittest.TestCase):
    def test_demander(self):
        self.assertIsNone(m.demander("Chemin", C, lire=lambda _: "x"))
        self.assertEqual(m.demander("Chemin", C, defaut="D:\\a", lire=lambda _: ""), "D:\\a")
        self.assertEqual(m.demander("Chemin", C, lire=lambda _: " D:\\b "), "D:\\b")

    def test_confirmer(self):
        self.assertTrue(m.confirmer("Continuer ?", C, defaut_oui=True, lire=lambda _: ""))
        self.assertFalse(m.confirmer("Continuer ?", C, defaut_oui=False, lire=lambda _: ""))
        self.assertTrue(m.confirmer("Continuer ?", C, defaut_oui=False, lire=lambda _: "o"))


class TestCouleurs(unittest.TestCase):
    def test_desactivees(self):
        c = Couleurs(forcer=False)
        self.assertEqual(c.VERT, "")
        self.assertEqual(c.succes("ok"), "[OK] ok")
        self.assertEqual(c.boite("T", largeur=10).splitlines()[0], "=" * 10)
        self.assertEqual(c.ligne_config("Clé", "v", largeur_cle=6), "  Clé    : v")


if __name__ == "__main__":
    unittest.main()
