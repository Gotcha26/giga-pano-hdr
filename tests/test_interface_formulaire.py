"""Tests de interface.formulaire : champs d'une tâche, signalement des chemins hors panorama, ligne de commande."""

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from interface import formulaire  # noqa: E402
from pilotage import arguments as args_mod  # noqa: E402
from pilotage import catalogue, config, lancer  # noqa: E402
from pilotage.couleurs import Couleurs  # noqa: E402

RENDRE = "4A/rendre_projet.ps1"


def _tache(identifiant):
    return next(t for t in catalogue.TACHES if t.identifiant == identifiant)


def _contexte():
    return lancer.Contexte(poste=config.Poste(), panorama=None, etats=[], c=Couleurs(forcer=False), scripts=SCRIPTS)


class TestChamps(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.P = Path(self.tmp.name) / "T" / "Assemblage-Hugin"
        (self.P / "4_vue_centree").mkdir(parents=True)
        for nom in ("b.pto", "a.pto"):
            (self.P / "4_vue_centree" / nom).write_text("", encoding="utf-8")
        self.p = config.Panorama(T=str(self.P.parent), P=str(self.P), H=str(Path(self.tmp.name) / "RAW" / "HDR"))
        self.ctx = _contexte()

    def _champs(self, panorama=None):
        t = _tache(RENDRE)
        args, _, _ = formulaire.arguments_de(t, self.ctx)
        return {c.arg.nom: c for c in formulaire.champs(t, args, panorama or self.p, self.ctx)}

    def test_genres_et_choix_pto(self):
        ch = self._champs()
        dossier = self.P / "4_vue_centree"
        self.assertEqual(ch["-Projet"].genre, "pto")
        self.assertEqual(ch["-Projet"].choix, [str(dossier / "a.pto"), str(dossier / "b.pto"), "Autre…"])
        self.assertEqual(ch["-Projet"].depart, str(dossier))
        self.assertEqual(ch["-Sortie"].genre, "dossier")
        self.assertEqual(ch["-Sortie"].depart, str(self.P))
        self.assertEqual(ch["-BigTiff"].genre, "interrupteur")
        self.assertIs(ch["-BigTiff"].valeur, False)
        self.assertEqual(ch["-OptionsMultiblend"].genre, "texte")
        self.assertEqual(ch["-Nom"].valeur, "panorama")
        self.assertTrue(ch["-Projet"].obligatoire)
        self.assertFalse(ch["-Nom"].obligatoire)

    def test_valeur_prerempli_en_tete_des_choix_pto_sauf_si_dans_le_dossier(self):
        dossier = self.P / "4_vue_centree"
        self.p.reglages[RENDRE] = {"-Projet": r"E:\ailleurs\x.pto"}
        self.assertEqual(self._champs()["-Projet"].choix[0], r"E:\ailleurs\x.pto")
        self.p.reglages[RENDRE] = {"-Projet": str(dossier / "b.pto")}
        self.assertEqual(self._champs()["-Projet"].choix, [str(dossier / "a.pto"), str(dossier / "b.pto"), "Autre…"])

    def test_dossier_de_phase_absent_ou_sans_panorama(self):
        autre = config.Panorama(T=r"Z:\inexistant", P=r"Z:\inexistant\P")
        ch = self._champs(autre)
        self.assertEqual(ch["-Projet"].choix, ["Autre…"])
        self.assertEqual(ch["-Projet"].depart, r"Z:\inexistant\P")
        t = _tache(RENDRE)
        args, _, _ = formulaire.arguments_de(t, self.ctx)
        sans = {c.arg.nom: c for c in formulaire.champs(t, args, None, self.ctx)}
        self.assertEqual(sans["-Projet"].choix, ["Autre…"])
        self.assertEqual(sans["-Projet"].depart, "")
        self.assertFalse(sans["-Sortie"].hors_panorama)

    def test_memorise_prime_et_hors_panorama_signale(self):
        self.p.reglages[RENDRE] = {"-Nom": "vue"}
        ch = self._champs()
        self.assertEqual(ch["-Nom"].valeur, "vue")
        self.assertTrue(replace(ch["-Sortie"], valeur=r"E:\ailleurs").hors_panorama)
        for sous in (self.p.T, str(self.P / "6_pleine_res"), self.p.H):
            self.assertFalse(replace(ch["-Sortie"], valeur=sous.upper()).hors_panorama, sous)
        self.assertFalse(replace(ch["-Sortie"], valeur="").hors_panorama)
        self.assertFalse(replace(ch["-Sortie"], valeur="relatif").hors_panorama)
        self.assertFalse(replace(ch["-Nom"], valeur=r"E:\ailleurs").hors_panorama)    # pas un chemin
        self.assertTrue(replace(ch["-Sortie"], valeur=self.p.T + "-voisin").hors_panorama)

    def test_h_vide_ignore(self):
        self.p.H = ""
        ch = self._champs()
        self.assertTrue(replace(ch["-Sortie"], valeur=r"E:\ailleurs").hors_panorama)

    def test_arguments_de_python_et_powershell(self):
        args, ecrit, doc = formulaire.arguments_de(_tache(RENDRE), self.ctx)
        self.assertEqual(args[0].nom, "-Projet")
        self.assertIn("rendu", ecrit)
        self.assertTrue(doc)
        t_py = next(t for t in catalogue.TACHES if t.script == "tiffinfo.py")
        args, ecrit, doc = formulaire.arguments_de(t_py, self.ctx)
        self.assertEqual([a.nom for a in args], ["image.tif"])
        self.assertIsNone(ecrit)
        self.assertTrue(doc)

    def test_toutes_les_taches_a_script_donnent_des_champs(self):
        genres = set(formulaire.GENRES.values())
        taches = [t for t in catalogue.TACHES if t.script]
        self.assertTrue(taches)
        for t in taches:
            with self.subTest(tache=t.identifiant):
                args, _, _ = formulaire.arguments_de(t, self.ctx)
                for c in formulaire.champs(t, args, self.p, self.ctx):
                    self.assertIn(c.genre, genres)

    def test_tache_sans_script_et_type_inconnu_levent_une_erreur_explicite(self):
        sans = next(t for t in catalogue.TACHES if not t.script)
        with self.assertRaisesRegex(ValueError, "tâche sans script"):
            formulaire.arguments_de(sans, self.ctx)
        a = args_mod.Arg("--x", "x")
        a.type = "inconnu"
        with self.assertRaisesRegex(ValueError, "sans genre de champ"):
            formulaire.champs(_tache(RENDRE), [a], self.p, self.ctx)

    def test_valeur_preremplie_de_casse_differente_pas_dupliquee(self):
        dossier = self.P / "4_vue_centree"
        self.p.reglages[RENDRE] = {"-Projet": str(dossier / "A.PTO").upper()}
        self.assertEqual(len(self._champs()["-Projet"].choix), 3)

    def test_commande_py_et_ps1(self):
        t_py = next(t for t in catalogue.TACHES if t.script == "tiffinfo.py")
        self.assertEqual(formulaire.commande(t_py, self.ctx, {"image.tif": r"D:\x.tif"})[1:],
                         [str(SCRIPTS / "tiffinfo.py"), r"D:\x.tif"])
        cmd = formulaire.commande(_tache(RENDRE), self.ctx, {"-Projet": r"D:\a.pto", "-Sortie": r"D:\r", "-BigTiff": True})
        self.assertIn("-File", cmd)
        self.assertEqual(cmd[cmd.index("-File") + 1], str(SCRIPTS / "rendre_projet.ps1"))
        self.assertEqual(cmd[cmd.index("-File") + 2:], ["-Projet", r"D:\a.pto", "-Sortie", r"D:\r", "-BigTiff"])


if __name__ == "__main__":
    unittest.main()
