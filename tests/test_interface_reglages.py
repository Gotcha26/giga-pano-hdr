"""Tests de interface.reglages : mémorisation des réglages et report automatique entre phases."""

import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from interface import reglages  # noqa: E402
from pilotage.arguments import Arg  # noqa: E402
from pilotage.catalogue import Tache  # noqa: E402
from pilotage.config import Panorama  # noqa: E402

ATTENDU = r"3_optimisation\pano_grille_opt.pto"


def _panorama(racine=r"D:\Pano\P"):
    return Panorama(T=os.path.dirname(racine), P=racine)


def _tache_geste():
    return Tache("g", 3, "3G", geste="…", attendu=ATTENDU, reporte={"maitre": "attendu"})


def _faux_mettre_a_jour(p, vus=None):
    """Remplaçant de config.mettre_a_jour sans disque : « relit » une copie de `p` et note (T, clés)."""
    def mettre_a_jour(T, /, **cles):
        if vus is not None:
            vus.append((T, dict(cles)))
        relu = replace(p, reglages=dict(p.reglages))
        if "reglages" in cles:
            r = cles.pop("reglages")
            relu.reglages = {**relu.reglages, **r} if r else {}
        for cle, v in cles.items():
            setattr(relu, cle, v)
        return relu
    return mettre_a_jour


def _rien(T, /, **cles):
    return None


class TestMemoriser(unittest.TestCase):
    def test_memorisables_ne_garde_que_les_arg_sans_config(self):
        args = [Arg("-Projet", "p", type="pto", config="maitre"), Arg("-Nom", "n")]
        self.assertEqual([a.nom for a in reglages.memorisables(args)], ["-Nom"])

    def test_memoriser_exclut_les_arg_relies_au_panorama_et_aux_outils(self):
        p = _panorama()
        args = [Arg("-Projet", "p", type="pto", config="maitre"), Arg("-Hugin", "h", config="outil:hugin"),
                Arg("-Nom", "n"), Arg("-BigTiff", "b", type="drapeau"), Arg("-Options", "o", type="liste")]
        ecrit = reglages.memoriser(p, "6C.4/rendre_projet.ps1", args,
                                   {"-Projet": "D:\\m.pto", "-Hugin": "C:\\H", "-Nom": "complet",
                                    "-BigTiff": True, "-Options": ""},
                                   mettre_a_jour=_faux_mettre_a_jour(p))
        self.assertEqual(ecrit, {"-Nom": "complet", "-BigTiff": True})
        self.assertEqual(p.reglages["6C.4/rendre_projet.ps1"], ecrit)

    def test_memoriser_enregistre_et_remplace_sans_fusionner(self):
        p = _panorama()
        p.reglages["x/y.py"] = {"-Ancien": "a"}
        vu = []
        reglages.memoriser(p, "x/y.py", [Arg("-Nom", "n")], {"-Nom": "b", "-Ancien": "a"},
                           mettre_a_jour=_faux_mettre_a_jour(p, vu))
        self.assertEqual(p.reglages["x/y.py"], {"-Nom": "b"})
        self.assertEqual(vu, [(p.T, {"reglages": {"x/y.py": {"-Nom": "b"}}})])

    def test_memoriser_drapeau_en_booleen_et_ignore_none(self):
        p = _panorama()
        args = [Arg("-Vite", "v", type="drapeau"), Arg("-Nom", "n")]
        ecrit = reglages.memoriser(p, "t", args, {"-Vite": 0, "-Nom": None}, mettre_a_jour=_faux_mettre_a_jour(p))
        self.assertEqual(ecrit, {"-Vite": False})

    def test_memoriser_conserve_ce_qui_a_change_sur_disque(self):
        from pilotage import config
        with tempfile.TemporaryDirectory() as d:
            p = Panorama(T=d, P=os.path.join(d, "P"), reglages={"autre/t.py": {"-X": "1"}})
            config.enregistrer_panorama(p)
            disque = config.charger_panorama(d)                 # modifié à la main (ou par un autre onglet)
            disque.pleine_res = r"E:\complet.tif"
            disque.reglages["tiers/t.py"] = {"-Y": "2"}
            config.enregistrer_panorama(disque)
            reglages.memoriser(p, "x/y.py", [Arg("-Nom", "n")], {"-Nom": "b"})
            relu = config.charger_panorama(d)
            self.assertEqual(relu.pleine_res, r"E:\complet.tif")
            self.assertEqual(relu.reglages, {"autre/t.py": {"-X": "1"}, "tiers/t.py": {"-Y": "2"},
                                             "x/y.py": {"-Nom": "b"}})
            self.assertEqual(p.reglages, relu.reglages)         # recopiés dans l'objet en mémoire


class TestResoudre(unittest.TestCase):
    def test_resoudre_argument_gabarit_et_attendu(self):
        p = _panorama()
        t = Tache("x", 6, "6C.4", script="rendre_projet.ps1", reporte={"pleine_res": "{-Sortie}\\{-Nom}.tif"})
        self.assertEqual(reglages.resoudre(t, {"-Sortie": r"E:\R", "-Nom": "complet"}, p),
                         {"pleine_res": r"E:\R\complet.tif"})
        self.assertEqual(reglages.resoudre(t, {"-Sortie": "", "-Nom": "complet"}, p), {})
        self.assertEqual(reglages.resoudre(t, {"-Nom": "complet"}, p), {})
        self.assertEqual(reglages.resoudre(t, {"-Sortie": "E:\\R\\", "-Nom": "complet"}, p),    # « \ » final
                         {"pleine_res": r"E:\R\complet.tif"})
        g = _tache_geste()
        self.assertEqual(reglages.resoudre(g, {}, p), {"maitre": ATTENDU})

    def test_resoudre_nom_d_argument_range_sous_p_et_omet_le_vide(self):
        p = _panorama()
        t = Tache("x", 5, "5B", script="nona_images.ps1", reporte={"rendu_hdr": "-Sortie"})
        self.assertEqual(reglages.resoudre(t, {"-Sortie": os.path.join(p.P, "5_hdr", "rendu")}, p),
                         {"rendu_hdr": r"5_hdr\rendu"})
        self.assertEqual(reglages.resoudre(t, {"-Sortie": None}, p), {})

    def test_resoudre_cle_hors_chemins_gardee_telle_quelle(self):
        p = _panorama()
        t = Tache("x", 5, "5B", script="s.py", reporte={"export_l": "-Nom"})
        self.assertEqual(reglages.resoudre(t, {"-Nom": os.path.join(p.P, "a")}, p),
                         {"export_l": os.path.join(p.P, "a")})


class TestReporterApresExecution(unittest.TestCase):
    def test_reporter_apres_execution_ecrit_et_annonce(self):
        p = _panorama()
        t = Tache("x", 5, "5B", script="nona_images.ps1", reporte={"rendu_hdr": "-Sortie"})
        vu = []
        self.assertEqual(reglages.reporter_apres_execution(
            t, {"-Sortie": os.path.join(p.P, "5_hdr", "rendu")}, p, mettre_a_jour=_faux_mettre_a_jour(p, vu)),
            [("rendu_hdr", r"5_hdr\rendu")])
        self.assertEqual(p.rendu_hdr, r"5_hdr\rendu")
        self.assertEqual(vu, [(p.T, {"rendu_hdr": r"5_hdr\rendu"})])

    def test_sans_changement_n_enregistre_pas(self):
        p = _panorama()
        t = Tache("x", 5, "5B", script="nona_images.ps1", reporte={"rendu_hdr": "-Sortie"})
        vu = []
        self.assertEqual(reglages.reporter_apres_execution(t, {"-Sortie": ""}, p,
                                                           mettre_a_jour=_faux_mettre_a_jour(p, vu)), [])
        self.assertEqual(vu, [])

    def test_report_conserve_les_autres_cles_modifiees_sur_disque(self):
        from pilotage import config
        with tempfile.TemporaryDirectory() as d:
            p = Panorama(T=d, P=os.path.join(d, "P"))
            config.enregistrer_panorama(p)
            disque = config.charger_panorama(d)
            disque.maitre = r"3_optimisation\pano_grille_opt.pto"
            config.enregistrer_panorama(disque)
            t = Tache("x", 5, "5B", script="nona_images.ps1", reporte={"rendu_hdr": "-Sortie"})
            reglages.reporter_apres_execution(t, {"-Sortie": os.path.join(p.P, "5_hdr", "rendu")}, p)
            relu = config.charger_panorama(d)
            self.assertEqual((relu.maitre, relu.rendu_hdr), (r"3_optimisation\pano_grille_opt.pto", r"5_hdr\rendu"))


class TestGeste(unittest.TestCase):
    def test_etat_geste(self):
        with tempfile.TemporaryDirectory() as d:
            p = Panorama(T=d, P=d)
            g = _tache_geste()
            self.assertEqual(reglages.etat_geste(g, p), (False, os.path.join(d, ATTENDU)))
            self._ecrire(os.path.join(d, ATTENDU), 100)
            self.assertEqual(reglages.etat_geste(g, p), (True, os.path.join(d, ATTENDU)))
        self.assertEqual(reglages.etat_geste(Tache("a", 1, "1A", geste="…"), p), (False, ""))
        self.assertEqual(reglages.etat_geste(g, None), (False, ""))

    @staticmethod
    def _ecrire(chemin, mtime):
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with open(chemin, "w", encoding="utf-8") as f:
            f.write("x")
        os.utime(chemin, (mtime, mtime))

    def test_geste_ne_remplace_que_si_plus_recent(self):
        with tempfile.TemporaryDirectory() as d:
            p = Panorama(T=d, P=d)
            g = _tache_geste()
            attendu = os.path.join(d, ATTENDU)
            autre = os.path.join(d, r"3_optimisation\autre.pto")
            rien = _rien
            self.assertIsNone(reglages.reporter_geste(g, p, mettre_a_jour=rien))           # fichier absent
            self._ecrire(attendu, 100)
            self.assertEqual(reglages.reporter_geste(g, p, mettre_a_jour=rien), ATTENDU)    # valeur vide
            self.assertEqual(p.maitre, ATTENDU)
            p.maitre = r"3_optimisation\autre.pto"
            self.assertEqual(reglages.reporter_geste(g, p, mettre_a_jour=rien), ATTENDU)    # désigne un fichier absent
            self._ecrire(autre, 200)
            p.maitre = r"3_optimisation\autre.pto"
            self.assertIsNone(reglages.reporter_geste(g, p, mettre_a_jour=rien))            # maître désigné plus récent
            self._ecrire(attendu, 300)
            self.assertEqual(reglages.reporter_geste(g, p, mettre_a_jour=rien), ATTENDU)

    def test_geste_enregistre_quand_il_reporte(self):
        with tempfile.TemporaryDirectory() as d:
            p = Panorama(T=d, P=d)
            self._ecrire(os.path.join(d, ATTENDU), 100)
            vu = []
            reglages.reporter_geste(_tache_geste(), p, mettre_a_jour=_faux_mettre_a_jour(p, vu))
            self.assertEqual(vu, [(d, {"maitre": ATTENDU})])


if __name__ == "__main__":
    unittest.main()
