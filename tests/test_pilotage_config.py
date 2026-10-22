"""Tests de pilotage.config : configuration du poste et du panorama courant (JSON hors dépôt)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pilotage import config  # noqa: E402


class TestChemins(unittest.TestCase):
    def test_localappdata(self):
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": r"C:\LA"}):
            self.assertEqual(config.chemin_poste(), Path(r"C:\LA") / "giga-pano-hdr" / "config.json")

    def test_sans_localappdata(self):
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": ""}):
            self.assertEqual(config.chemin_poste(), Path.home() / ".giga-pano-hdr" / "config.json")


class TestPoste(unittest.TestCase):
    def test_aller_retour_et_absent(self):
        with tempfile.TemporaryDirectory() as d:
            chemin = Path(d) / "sous" / "config.json"
            self.assertEqual(config.charger_poste(chemin), config.Poste())
            p = config.Poste(outils={"vips": r"D:\Outils\vips.exe"}, panoramas=[r"D:\P\a"], courant=r"D:\P\a")
            config.enregistrer_poste(p, chemin)
            self.assertEqual(config.charger_poste(chemin), p)

    def test_json_invalide(self):
        with tempfile.TemporaryDirectory() as d:
            chemin = Path(d) / "config.json"
            chemin.write_text("{oops", encoding="utf-8")
            self.assertEqual(config.charger_poste(chemin), config.Poste())


class TestPanorama(unittest.TestCase):
    def test_aller_retour_cles_manquantes_et_inconnues(self):
        with tempfile.TemporaryDirectory() as d:
            T = Path(d) / "pano"
            T.mkdir()
            p = config.Panorama(T=str(T), P=str(T / "Assemblage-Hugin"), lignes=6, colonnes=37, expos=7,
                                pas_h=5.0, pas_v=5.8, maitre=r"3_optimisation\pano_grille_opt4.pto")
            config.enregistrer_panorama(p)
            self.assertEqual(config.charger_panorama(T), p)
            (T / "panorama.json").write_text(json.dumps({"T": str(T), "P": "x", "inconnue": 1}), encoding="utf-8")
            q = config.charger_panorama(T)
            self.assertEqual((q.P, q.lignes, q.export_l), ("x", None, "Export-TIFF-L"))
            self.assertIsNone(config.charger_panorama(Path(d) / "absent"))

    def test_arborescence(self):
        with tempfile.TemporaryDirectory() as d:
            T = Path(d) / "pano"
            p = config.Panorama(T=str(T), P=str(T / "Assemblage-Hugin"))
            crees = config.creer_arborescence(p)
            self.assertTrue((T / "Export-TIFF-L").is_dir())
            self.assertTrue((T / "Assemblage-Hugin" / "7_tuiles").is_dir())
            self.assertTrue((T / "Assemblage-Hugin" / "7_galerie").is_dir())
            self.assertEqual(len(crees), 4 + len(config.DOSSIERS_PHASE))   # T, L, H, P + phases
            self.assertEqual(config.creer_arborescence(p), [])

    def test_arborescence_avec_dossier_hdr(self):
        with tempfile.TemporaryDirectory() as d:
            T, H = Path(d) / "pano", Path(d) / "RAW" / "HDR"
            p = config.Panorama(T=str(T), P=str(T / "Assemblage-Hugin"), H=str(H))
            crees = config.creer_arborescence(p)
            self.assertTrue((H / "TIFF").is_dir())
            self.assertEqual(len(crees), 4 + len(config.DOSSIERS_PHASE) + 2)   # + $H et $H\TIFF

    def test_valeur(self):
        p = config.Panorama(T=r"D:\T", P=r"D:\T\A", pas_v=5.8, maitre=r"3_optimisation\m.pto")
        self.assertEqual(config.valeur(p, "export_h"), r"D:\T\Export-TIFF-H")
        self.assertEqual(config.valeur(p, "maitre"), r"D:\T\A\3_optimisation\m.pto")
        self.assertEqual(config.valeur(p, "table"), r"D:\T\A\table_raw_LCE.csv")
        self.assertEqual(config.valeur(p, "cp_pto"), r"D:\T\A\3_grille\pano_grille_cp.pto")
        self.assertEqual(config.valeur(p, "pas_v"), "5.8")
        self.assertIsNone(config.valeur(p, "pas_h"))
        self.assertIsNone(config.valeur(None, "T"))
        self.assertIsNone(config.valeur(config.Panorama(T="a", P="b"), "maitre"))
        self.assertEqual(config.dossier_phase(p, "3_grille"), Path(r"D:\T\A\3_grille"))
        self.assertIsNone(config.dossier_phase(None, "3_grille"))


class TestClesReportees(unittest.TestCase):
    def test_ancien_fichier_sans_nouvelles_cles(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "panorama.json").write_text(json.dumps({"T": d, "P": "x"}), encoding="utf-8")
            p = config.charger_panorama(d)
            self.assertEqual(p.reglages, {})
            self.assertEqual(p.pleine_res, "")
            self.assertIsNone(config.valeur(p, "pleine_res"))

    def test_aller_retour_des_nouvelles_cles(self):
        with tempfile.TemporaryDirectory() as d:
            p = config.Panorama(T=d, P=str(Path(d) / "P"), hdr_pto=r"5_hdr\pano_HDR.pto",
                                reglages={"6C.4/rendre_projet.ps1": {"-Nom": "vue"}})
            config.enregistrer_panorama(p)
            self.assertEqual(config.charger_panorama(d), p)

    def test_ranger_chemin_relatif_sous_P_sinon_absolu(self):
        p = config.Panorama(T=r"D:\Panos\x", P=r"D:\Panos\x\Assemblage-Hugin")
        self.assertEqual(config.ranger_chemin(p, r"d:\panos\x\assemblage-hugin\5_hdr\pano_HDR.pto"),
                         r"5_hdr\pano_HDR.pto")
        self.assertEqual(config.ranger_chemin(p, r"E:\Rendus\complet"), r"E:\Rendus\complet")
        self.assertEqual(config.ranger_chemin(p, ""), "")

    def test_valeur_recompose_relatif_et_garde_absolu(self):
        p = config.Panorama(T=r"D:\x", P=r"D:\x\P", hdr_pto=r"5_hdr\pano_HDR.pto", pleine_res=r"E:\R\c.tif")
        self.assertEqual(config.valeur(p, "hdr_pto"), r"D:\x\P\5_hdr\pano_HDR.pto")
        self.assertEqual(config.valeur(p, "pleine_res"), r"E:\R\c.tif")
        self.assertIsNone(config.valeur(p, "rendu_hdr"))


if __name__ == "__main__":
    unittest.main()
