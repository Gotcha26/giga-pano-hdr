"""Tests de pilotage.cheminement : ordre des cases selon le coin de départ et le serpentin, dessins texte et SVG."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pilotage import cheminement  # noqa: E402


class TestOrdre(unittest.TestCase):
    def test_defaut_equivaut_a_l_ancien_calcul(self):
        L, C = 6, 37
        self.assertEqual(cheminement.cases_nommees(L, C, "hd", False), [divmod(k, C) for k in range(L * C)])

    def test_coins_lineaires(self):
        premiere = {c: cheminement.ordre_prise(3, 5, c, False)[0] for c in cheminement.COINS}
        self.assertEqual(premiere, {"hg": (0, 0), "hd": (0, 4), "bg": (2, 0), "bd": (2, 4)})
        self.assertEqual(cheminement.ordre_prise(3, 5, "bg", False)[-1], (0, 4))

    def test_serpentin_inverse_une_ligne_sur_deux(self):
        serpentin = cheminement.ordre_prise(3, 5, "hg", True)
        lineaire = cheminement.ordre_prise(3, 5, "hg", False)
        self.assertEqual((serpentin[5], serpentin[10]), ((1, 4), (2, 0)))
        self.assertEqual(lineaire[5], (1, 0))

    def test_cases_nommees_bord_droit(self):
        self.assertEqual(cheminement.cases_nommees(3, 5, "hg", False)[0], (0, 4))
        self.assertEqual(cheminement.cases_nommees(3, 5, "bd", True)[5], (1, 4))

    def test_chaque_case_une_fois(self):
        for lignes, colonnes in ((1, 5), (3, 1), (3, 5)):
            tout = {(r, c) for r in range(lignes) for c in range(colonnes)}
            for depart in cheminement.COINS:
                for serpentin in (False, True):
                    ordre = cheminement.ordre_prise(lignes, colonnes, depart, serpentin)
                    self.assertEqual(len(ordre), len(tout))
                    self.assertEqual(set(ordre), tout, (lignes, colonnes, depart, serpentin))

    def test_depart_invalide(self):
        with self.assertRaises(ValueError):
            cheminement.verifier_depart("xx")
        self.assertEqual(cheminement.verifier_depart("bg"), "bg")


class TestDessin(unittest.TestCase):
    def test_dessin_texte_lineaire_haut_droit(self):
        lignes = cheminement.dessin_texte("hd", False)
        self.assertEqual(len(lignes), 5)
        self.assertIn("5 ← 4 ← 3 ← 2 ← 1", lignes[0])
        self.assertIn("┄", lignes[1])
        self.assertIn("┄", lignes[3])

    def test_dessin_texte_serpentin_haut_gauche(self):
        lignes = cheminement.dessin_texte("hg", True)
        self.assertEqual(len(lignes), 5)
        self.assertIn("↓", lignes[1])
        self.assertIn("↓", lignes[3])
        self.assertIn("11 → 12 → 13 → 14 → 15", lignes[4])

    def test_dessin_texte_serpentin_sans_trait_de_retour(self):
        for depart in cheminement.COINS:
            lignes = cheminement.dessin_texte(depart, True)
            self.assertNotIn("┄", lignes[1] + lignes[3], depart)

    def test_dessin_svg(self):
        lineaire, serpentin = cheminement.dessin_svg("hg", False), cheminement.dessin_svg("hg", True)
        for svg in (lineaire, serpentin):
            self.assertEqual(svg.count("<rect"), 15)
            self.assertIn(">1<", svg)
            self.assertIn(">15<", svg)
        self.assertIn("stroke-dasharray", lineaire)
        self.assertNotIn("stroke-dasharray", serpentin)

    def test_resume(self):
        a, b = cheminement.resume("bg", False), cheminement.resume("hd", True)
        self.assertIn("bas gauche", a)
        self.assertIn("en remontant", a)
        self.assertNotIn("serpentin", a)
        self.assertIn("haut droit", b)
        self.assertIn("en descendant", b)
        self.assertIn("serpentin", b)


if __name__ == "__main__":
    unittest.main()
