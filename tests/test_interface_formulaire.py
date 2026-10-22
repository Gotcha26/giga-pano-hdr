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

    def test_nona_5b_prerempli_le_projet_depuis_hdr_pto(self):
        t = _tache("5B/nona_images.ps1")
        self.p.hdr_pto = r"5_hdr\pano_hdr.pto"            # forme stockée : relative à $P
        self.p.reglages[t.identifiant] = {"-Projet": r"D:\ancien.pto", "-A": "41"}
        args, _, _ = formulaire.arguments_de(t, self.ctx)
        champs = {c.arg.nom: c for c in formulaire.champs(t, args, self.p, self.ctx)}
        self.assertEqual(champs["-Projet"].valeur, str(self.P / "5_hdr" / "pano_hdr.pto"))
        self.assertEqual(champs["-A"].valeur, "41")         # un argument propre garde sa valeur mémorisée
        self.assertEqual(next(a for a in args if a.nom == "-Projet").config, "hdr_pto")   # donc jamais mémorisé

    def test_lit_ne_touche_pas_la_declaration_partagee_ni_les_autres_reperes(self):
        from pilotage import declarations_ps
        formulaire.arguments_de(_tache("5B/nona_images.ps1"), self.ctx)
        self.assertIsNone(next(a for a in declarations_ps.PS["nona_images.ps1"][0] if a.nom == "-Projet").config)
        self.p.hdr_pto = r"5_hdr\pano_hdr.pto"
        t = _tache("6B/nona_images.ps1")
        args, _, _ = formulaire.arguments_de(t, self.ctx)
        self.assertEqual({c.arg.nom: c for c in formulaire.champs(t, args, self.p, self.ctx)}["-Projet"].valeur, "")

    def test_fusion_5b_et_tuilage_7a_lisent_le_rendu_hdr_et_la_pleine_resolution(self):
        self.p.rendu_hdr, self.p.pleine_res = r"5_hdr\rendu", r"E:\complet\complet.tif"
        for identifiant, nom, attendu in (("5B/fusionner_par_exposition.ps1", "-Rendu", str(self.P / "5_hdr" / "rendu")),
                                          ("7A/tuiler.ps1", "-Image", r"E:\complet\complet.tif")):
            with self.subTest(identifiant):
                t = _tache(identifiant)
                args, _, _ = formulaire.arguments_de(t, self.ctx)
                self.assertEqual({c.arg.nom: c for c in formulaire.champs(t, args, self.p, self.ctx)}[nom].valeur,
                                 attendu)

    def test_lit_d_un_argument_non_declare_leve_une_erreur(self):
        t = replace(_tache("7A/tuiler.ps1"), lit={"-Inconnu": "pleine_res"})
        with self.assertRaises(ValueError):
            formulaire.arguments_de(t, self.ctx)

    def test_cpclean_formulaire_et_commande_partages_avec_la_console(self):
        from pilotage import outils
        t = _tache("3C.1/cpclean")
        self.assertTrue(formulaire.a_un_formulaire(t))
        self.assertFalse(formulaire.a_un_formulaire(_tache("3B/geste")))
        args, ecrit, _ = formulaire.arguments_de(t, self.ctx)
        self.assertEqual(args[0].config, "cp_pto")
        self.assertEqual([a.nom for a in args], [a.nom for a in catalogue.ARGS_CPCLEAN])
        self.assertIn("ABSOLUS", ecrit)
        champs = {c.arg.nom: c for c in formulaire.champs(t, args, self.p, self.ctx)}
        self.assertEqual(champs["entree.pto"].valeur, str(self.P / "3_grille" / "pano_grille_cp.pto"))
        valeurs = {"entree.pto": r"D:\P\3_grille\cp.pto", "sortie.pto": r"D:\P\3_optimisation\cp_clean.pto"}
        with self.assertRaises(LookupError):                 # Hugin absent
            formulaire.commande(t, self.ctx, valeurs)
        hugin = next(o for o in outils.OUTILS if o.cle == "hugin")
        self.ctx.etats = [outils.Etat(hugin, r"C:\Hugin\bin\nona.exe", "2025")]
        attendu = [r"C:\Hugin\bin\cpclean.exe", "-p", "-n", "2", "-o", r"D:\P\3_optimisation\cp_clean.pto",
                   r"D:\P\3_grille\cp.pto"]
        self.assertEqual(formulaire.commande(t, self.ctx, valeurs), attendu)
        self.assertEqual(lancer.commande_cpclean(self.ctx, [valeurs["entree.pto"], valeurs["sortie.pto"]]), attendu)

    def test_une_seule_boite_parcourir_a_la_fois(self):
        import threading
        verrou, vus = threading.Lock(), []

        def boite(genre, depart):
            vus.append((genre, depart))
            return r"D:\choisi"
        self.assertEqual(formulaire.boite_exclusive("dossier", r"D:\x", boite=boite, verrou=verrou), (True, r"D:\choisi"))
        with verrou:                                         # une boîte est ouverte
            self.assertEqual(formulaire.boite_exclusive("pto", "", boite=boite, verrou=verrou), (False, None))
        self.assertEqual(vus, [("dossier", r"D:\x")])
        self.assertFalse(verrou.locked())                    # libéré après usage

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
