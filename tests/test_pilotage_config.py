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


class TestMettreAJour(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.T = self.tmp.name
        self.p = config.Panorama(T=self.T, P=str(Path(self.T) / "P"), reglages={"a/x.py": {"-A": "1"}})
        config.enregistrer_panorama(self.p)

    def _modifier_a_la_main(self, **cles):
        donnees = json.loads((Path(self.T) / "panorama.json").read_text(encoding="utf-8"))
        donnees.update(cles)
        (Path(self.T) / "panorama.json").write_text(json.dumps(donnees), encoding="utf-8")

    def test_une_cle_modifiee_sur_disque_entre_chargement_et_mise_a_jour_est_conservee(self):
        self._modifier_a_la_main(maitre=r"3_optimisation\pano_grille_opt.pto", lignes=6)
        relu = config.mettre_a_jour(self.p.T, rendu_hdr=r"5_hdr\rendu")
        self.assertEqual((relu.maitre, relu.lignes, relu.rendu_hdr),
                         (r"3_optimisation\pano_grille_opt.pto", 6, r"5_hdr\rendu"))
        self.assertEqual(config.charger_panorama(self.T), relu)
        self.assertEqual(self.p.maitre, "")                     # l'objet en mémoire n'est pas touché

    def test_reglages_remplace_l_identifiant_donne_et_vide_avec_un_dict_vide(self):
        self._modifier_a_la_main(reglages={"a/x.py": {"-A": "1"}, "b/y.py": {"-B": "2"}})
        relu = config.mettre_a_jour(self.T, reglages={"a/x.py": {"-A": "3"}})
        self.assertEqual(relu.reglages, {"a/x.py": {"-A": "3"}, "b/y.py": {"-B": "2"}})
        self.assertEqual(config.mettre_a_jour(self.T, reglages={}).reglages, {})
        self.assertEqual(config.charger_panorama(self.T).reglages, {})

    def test_panorama_absent_ou_cle_inconnue(self):
        with self.assertRaises(FileNotFoundError):
            config.mettre_a_jour(str(Path(self.T) / "absent"), maitre="m.pto")
        with self.assertRaises(TypeError):
            config.mettre_a_jour(self.T, inconnue=1)

    def test_changer_T_enregistre_dans_le_nouveau_dossier(self):
        nouveau = Path(self.T) / "ailleurs"
        nouveau.mkdir()
        config.mettre_a_jour(self.T, T=str(nouveau))
        self.assertEqual(config.charger_panorama(nouveau).reglages, {"a/x.py": {"-A": "1"}})

    def test_reglages_corrompus_ignores_au_chargement(self):
        self._modifier_a_la_main(reglages=None)
        self.assertEqual(config.charger_panorama(self.T).reglages, {})
        self._modifier_a_la_main(reglages=["x"])
        self.assertEqual(config.mettre_a_jour(self.T, reglages={"a/x.py": {}}).reglages, {"a/x.py": {}})


class TestNouveauPanorama(unittest.TestCase):
    def test_propositions_nouveau_reprend_le_courant_et_les_chemins_du_guide(self):
        courant = config.Panorama(T=r"D:\Panoramas\2026-07-01\35mm", P=r"D:\Panoramas\2026-07-01\35mm\Assemblage-Hugin",
                                  focale=35, lignes=6, colonnes=14)
        prop = config.propositions_nouveau(courant, "2026-10-22", 35.0, None, None)
        self.assertEqual(prop["T"], r"D:\Panoramas\2026-10-22\35mm")
        self.assertEqual((prop["lignes"], prop["colonnes"], prop["largeur_hdr"], prop["largeur_mm"]), (6, 14, 20000, 24))
        self.assertIsNone(prop["expos"])
        self.assertIsNone(prop["existant"])
        self.assertEqual((prop["raws"], prop["H"]), ("", ""))
        for cle, _, _ in config.QUESTIONS:
            self.assertIn(cle, prop)

    def test_propositions_nouveau_sans_courant_racine_du_guide_et_H_sous_les_raw(self):
        prop = config.propositions_nouveau(None, "2026-10-22", None, None, r"D:\RAW\jour")
        self.assertEqual(prop["T"], str(Path(config.RACINE_GUIDE, "2026-10-22")))
        self.assertEqual(prop["H"], str(Path(r"D:\RAW\jour", "HDR")))
        self.assertEqual(config.propositions_nouveau(None, "d", 200.0, r"E:\T", None)["T"], r"E:\T")

    def test_propositions_nouveau_prefere_le_panorama_json_existant(self):
        with tempfile.TemporaryDirectory() as d:
            T, H = str(Path(d) / "pano"), str(Path(d) / "RAW" / "HDR")
            config.enregistrer_panorama(config.Panorama(T=T, P="", H=H, lignes=4, colonnes=20))
            courant = config.Panorama(T=r"D:\a\b\c", P="", lignes=9, colonnes=9, expos=3)
            prop = config.propositions_nouveau(courant, "2026-10-22", None, T, None)
            self.assertEqual((prop["lignes"], prop["colonnes"], prop["expos"]), (4, 20, None))
            self.assertEqual((prop["raws"], prop["H"]), (str(Path(H).parent), H))
            self.assertEqual(prop["existant"].lignes, 4)

    def test_creer_nouveau_conserve_le_maitre_et_rend_courant(self):
        with tempfile.TemporaryDirectory() as d:
            T, H = str(Path(d) / "pano"), str(Path(d) / "RAW" / "HDR")
            config.enregistrer_panorama(config.Panorama(
                T=T, P="", maitre=r"3_optimisation\m.pto", export_l="L2", export_h="H2", hdr_pto=r"5_hdr\x.pto",
                reglages={"id": {"-Nom": "vue"}}))
            poste = config.Poste(panoramas=[T])
            chemin_poste = Path(d) / "config.json"
            valeurs = {"T": T, "H": H, "focale": 35.0, "lignes": 6, "colonnes": 14, "expos": None, "largeur_mm": 24,
                       "pas_h": None, "pas_v": None, "largeur_hdr": 20000, "largeur_pleine": None}
            with mock.patch.object(config, "chemin_poste", lambda: chemin_poste):
                p, crees = config.creer_nouveau(poste, valeurs)
            self.assertEqual((p.maitre, p.export_l, p.export_h, p.hdr_pto), (r"3_optimisation\m.pto", "L2", "H2", r"5_hdr\x.pto"))
            self.assertEqual(p.reglages, {"id": {"-Nom": "vue"}})
            self.assertEqual((p.P, p.H, p.focale, p.lignes), (os.path.join(T, "Assemblage-Hugin"), H, 35.0, 6))
            self.assertEqual(config.charger_panorama(T), p)
            self.assertTrue((Path(T) / "Assemblage-Hugin" / "3_grille").is_dir())
            self.assertIn(Path(H) / "TIFF", crees)
            self.assertEqual(poste.panoramas, [T])
            self.assertEqual(config.charger_poste(chemin_poste).courant, T)

    def test_creer_nouveau_ajoute_aux_panoramas_connus(self):
        with tempfile.TemporaryDirectory() as d:
            T = str(Path(d) / "pano")
            poste = config.Poste()
            with mock.patch.object(config, "chemin_poste", lambda: Path(d) / "config.json"):
                p, _ = config.creer_nouveau(poste, {"T": T, "H": "", "focale": None})
            self.assertEqual((poste.panoramas, poste.courant, p.H, p.maitre), ([T], T, "", ""))


if __name__ == "__main__":
    unittest.main()
