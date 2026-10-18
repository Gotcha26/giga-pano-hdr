"""Tests de controle_reglages_export.py et ecart_paires.py (fonctions pures, sans exiftool ni vips).

Lancer depuis la racine du dépôt :
    python -I -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import controle_reglages_export as ctrl  # noqa: E402
import ecart_paires as ecart  # noqa: E402


def ligne(fichier, raw, **reglages):
    base = {"SourceFile": fichier, "RawFileName": raw, "ImageWidth": "3456", "ImageHeight": "5184",
            "ProfileDescription": "Adobe RGB (1998)", "Dehaze": "0", "Exposure2012": "0.00", "Contrast2012": "0",
            "Highlights2012": "0", "Shadows2012": "0", "Whites2012": "0", "Blacks2012": "0",
            "WhiteBalance": "Custom", "Vibrance": "+15", "PointColors": "-1.0"}
    base.update(reglages)
    return base


class TestControleReglages(unittest.TestCase):
    def setUp(self):
        self.lignes = [ligne(f"D:/x/Pano_E0-{i:02d}.tif", f"r{i}.CR2") for i in range(1, 5)]
        self.table = {f"r{i}.CR2": f"L0_C0{i}_E0" for i in range(1, 5)}
        self.table["r9.CR2"] = "L0_C09_E1"        # une exposition autre que E0 : ne compte pas dans la couverture

    def test_nom_image(self):
        self.assertEqual(ctrl.nom_image(ligne("D:/x/L3_C06_E0.tif", "r1.CR2")), "L3_C06_E0")
        self.assertEqual(ctrl.nom_image(self.lignes[0], self.table), "L0_C01_E0")
        self.assertEqual(ctrl.nom_image(self.lignes[0]), "Pano_E0-01.tif")

    def test_lot_uniforme(self):
        self.assertEqual(ctrl.divergences(self.lignes), {})
        self.assertEqual(ctrl.avertissements(self.lignes), [])

    def test_divergence_detectee_et_images_en_minorite(self):
        self.lignes[2]["PointColors"] = "3.4, 0.4"
        div = ctrl.divergences(self.lignes)
        self.assertEqual(list(div), ["PointColors"])
        self.assertEqual(ctrl.images_en_minorite(self.lignes, "PointColors", self.table), ["L0_C03_E0"])

    def test_filtre_et_retouches_ignores(self):
        self.lignes[0]["RetouchAreaSpotType"] = "heal_patchmatch"
        self.lignes[1]["FilterListFiltersName"] = "Dust Removal"
        self.lignes[0]["AllowFilters"] = "1"
        self.assertEqual(ctrl.divergences(self.lignes), {})

    def test_ignorer_un_prefixe(self):
        self.lignes[2]["PointColors"] = "3.4"
        self.assertEqual(ctrl.divergences(self.lignes, ignorer=("PointColors",)), {})

    def test_tonalite_non_nulle_signalee_meme_si_uniforme(self):
        for l in self.lignes:
            l["Dehaze"] = "+24"
            l["Contrast2012"] = "+25"
        avert = ctrl.avertissements(self.lignes)
        self.assertEqual(len(avert), 2)
        self.assertTrue(any("Dehaze" in m for m in avert) and any("Contrast2012" in m for m in avert))

    def test_balance_des_blancs_mobile_signalee(self):
        for l in self.lignes:
            l["WhiteBalance"] = "As Shot"
        self.assertEqual(len(ctrl.avertissements(self.lignes)), 1)

    def test_couverture(self):
        manquants, en_trop = ctrl.couverture(self.lignes[:3], self.table)
        self.assertEqual(manquants, ["r4.CR2"])
        self.assertEqual(en_trop, [])
        self.lignes.append(ligne("D:/x/Pano_E0-99.tif", "inconnu.CR2"))
        self.assertEqual(ctrl.couverture(self.lignes, self.table), ([], ["inconnu.CR2"]))


PTO = (
    'p f1 w6000 h1500 v185 k0\n'
    'i w3456 h5184 f0 v6.867 r0 p14.5 y90 a0 b0 c0 n"a.tif"\n'
    'i w3456 h5184 f0 v=0 r0.6 p14.4 y85 a=0 b=0 c=0 n"b.tif"\n'
)


class TestEcartPaires(unittest.TestCase):
    def test_lire_projet(self):
        pos, fov, w, h = ecart.lire_projet(PTO)
        self.assertEqual((fov, w, h), (6.867, 3456, 5184))
        self.assertEqual(pos[0], (90.0, 14.5, 0.0))
        self.assertEqual(pos[1], (85.0, 14.4, 0.6))

    def test_lire_projet_vide(self):
        with self.assertRaises(ValueError):
            ecart.lire_projet("p f1 w6000 h1500 v185\n")

    def test_zone_commune_multiple_du_pas(self):
        pos, fov, w, h = ecart.lire_projet(PTO)
        x, y, lg, ht, dx, dy = ecart.zone_commune(pos[0], pos[1], w / fov, w, h)
        self.assertEqual(dx, round(5 * w / fov))
        self.assertEqual((lg % ecart.PAS, ht % ecart.PAS), (0, 0))
        self.assertGreater(lg, 0)
        # la zone et son homologue décalée restent dans l'image
        self.assertLessEqual(x + lg, w)
        self.assertLessEqual(x + dx + lg, w)

    def test_zone_commune_trop_petite(self):
        pos, fov, w, h = ecart.lire_projet(PTO)
        far = (pos[0][0] - 6.5, pos[0][1], 0.0)    # recouvrement presque nul
        self.assertIsNone(ecart.zone_commune(pos[0], far, w / fov, w, h))

    def test_rapports_tuiles_ecarte_sombres_et_saturees(self):
        ga, gb = [10000, 10000, 100, 65000], [10100, 9000, 100, 65000]
        ba, bb = [20000, 20000, 20000, 20000], [20000, 20000, 20000, 20000]
        rg, rb = ecart.rapports_tuiles(ga, gb, ba, bb)
        self.assertEqual(len(rg), 2)
        self.assertAlmostEqual(rg[0], 1.0)
        self.assertAlmostEqual(rg[1], -10.0)
        self.assertEqual(rb, [0.0, 0.0])

    def test_mediane_et_bruit(self):
        m, bruit = ecart.mediane_et_bruit([1.0, 2.0, 3.0, 4.0, 100.0])
        self.assertEqual(m, 3.0)
        self.assertEqual(bruit, 1.0)

    def test_hors_lot(self):
        v = [0.5, 0.6, 0.4, 0.5, 0.6, -6.0, 0.5, 0.55]
        self.assertEqual(ecart.hors_lot(v), [5])
        self.assertEqual(ecart.hors_lot([0.5, 0.6, 0.4, 0.5, 0.6, 0.5]), [])

    def test_hors_lot_ignore_les_ecarts_sous_le_seuil(self):
        v = [0.0, 0.0, 0.0, 0.0, 0.0, 0.5]    # 0,5 % sort statistiquement du lot mais reste sous le seuil de 0,8 %
        self.assertEqual(ecart.hors_lot(v), [])


if __name__ == "__main__":
    unittest.main()
