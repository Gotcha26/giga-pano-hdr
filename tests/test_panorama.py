"""Tests du lanceur : exécution des scripts (pilotage.lancer) et menus de panorama.py."""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from pilotage import config, lancer, outils  # noqa: E402
from pilotage.arguments import Arg  # noqa: E402
from pilotage.couleurs import Couleurs  # noqa: E402

C = Couleurs(forcer=False)
IMAGE, PROJET = r"D:\x.tif", r"D:\a.pto"     # le lanceur exige des chemins absolus


def saisies(*valeurs):
    it = iter(valeurs)
    return lambda _invite="": next(it)


def contexte(valeurs, executer=None, etats=None, poste=None, ecrire=None):
    return lancer.Contexte(poste=poste or config.Poste(), panorama=None, etats=etats or [], c=C,
                           lire=saisies(*valeurs), ecrire=ecrire or (lambda *a, **k: None), scripts=SCRIPTS,
                           executer=executer or (lambda *a, **k: SimpleNamespace(returncode=0)))


class TestConstruirePs(unittest.TestCase):
    def test_switch_et_valeurs(self):
        args = [Arg("-Projet", "p", type="pto"), Arg("-BigTiff", "b", type="drapeau"), Arg("-De", "d", type="entier"),
                Arg("-OptionsMultiblend", "o")]
        v = {"-Projet": PROJET, "-BigTiff": True, "-De": "0", "-OptionsMultiblend": "--cache-threshold=4G"}
        self.assertEqual(lancer.construire_ps(args, v),
                         ["-Projet", PROJET, "-BigTiff", "-De", "0", "-OptionsMultiblend", "--cache-threshold=4G"])
        with self.assertRaises(ValueError):
            lancer.construire_ps([Arg("sans_tiret", "x")], {"sans_tiret": "1"})


class TestExecution(unittest.TestCase):
    def test_python_annule(self):
        ctx = contexte(["0"], executer=lambda *a, **k: self.fail("ne doit pas exécuter"))
        self.assertIsNone(lancer.python(ctx, "tiffinfo.py", [Arg("image.tif", "i", type="chemin")], None))

    def test_python_lance_et_interruption(self):
        vu = {}

        def executer(cmd, **k):
            vu["cmd"] = cmd
            return SimpleNamespace(returncode=0)
        ctx = contexte(["1", IMAGE, "L"], executer)
        self.assertEqual(lancer.python(ctx, "tiffinfo.py", [Arg("image.tif", "i", type="chemin")], None), 0)
        self.assertEqual(vu["cmd"][1:], [str(SCRIPTS / "tiffinfo.py"), IMAGE])

        def interrompre(cmd, **k):
            raise KeyboardInterrupt
        ctx2 = contexte(["1", IMAGE, "L"], interrompre)
        self.assertEqual(lancer.python(ctx2, "tiffinfo.py", [Arg("image.tif", "i", type="chemin")], None), 130)

    def test_echec_revient_au_menu_avec_les_reglages(self):
        vu = []

        def executer(cmd, **k):
            vu.append(cmd)
            return SimpleNamespace(returncode=1 if len(vu) == 1 else 0)
        lignes = []
        # saisie, lancement (échec), Entrée de la pause, relance sans rien ressaisir
        ctx = contexte(["1", IMAGE, "L", "", "L"], executer, ecrire=lignes.append)
        self.assertEqual(lancer.python(ctx, "tiffinfo.py", [Arg("image.tif", "i", type="chemin")], None), 0)
        self.assertEqual([cmd[-1] for cmd in vu], [IMAGE, IMAGE])
        self.assertTrue(any("réglages conservés" in str(l) for l in lignes))

    def test_essai_a_blanc_puis_apply_sans_ressaisir(self):
        vu = []

        def executer(cmd, **k):
            vu.append(cmd)
            return SimpleNamespace(returncode=0)
        args = [Arg("DOSSIER", "d", type="dossier"), Arg("--apply", "a", type="drapeau")]
        # saisie, essai à blanc, Entrée de la pause, bascule --apply, relance, Entrée, retour au lanceur
        ctx = contexte(["1", r"D:\X", "L", "", "2", "L", "", "0"], executer)
        self.assertEqual(lancer.python(ctx, "renommer_pano.py", args, None), 0)
        self.assertEqual([cmd[2:] for cmd in vu], [[r"D:\X"], [r"D:\X", "--apply"]])

    def test_chemin_relatif_ou_abrege_refuse_avant_lancement(self):
        for saisie in [r"…\6_pleine_res\apercu\rendu", "rendu", r"D:\T\...\rendu"]:
            with self.subTest(saisie):
                lignes = []
                ctx = contexte(["1", saisie, "L", "", "0"], lambda *a, **k: self.fail("ne doit pas exécuter"),
                               ecrire=lignes.append)
                self.assertIsNone(lancer.python(ctx, "tiffinfo.py", [Arg("DOSSIER", "d", type="dossier")], None))
                self.assertTrue(any("Chemin à saisir en entier" in str(l) for l in lignes))

    def test_echec_puis_annulation_rend_le_code(self):
        ctx = contexte(["1", IMAGE, "L", "", "0"], lambda *a, **k: SimpleNamespace(returncode=2))
        self.assertEqual(lancer.python(ctx, "tiffinfo.py", [Arg("image.tif", "i", type="chemin")], None), 2)

    def test_python_lit_la_declaration_du_script(self):
        vu = {}

        def executer(cmd, **k):
            vu["cmd"] = cmd
            return SimpleNamespace(returncode=0)
        ctx = contexte(["1", IMAGE, "L"], executer)
        self.assertEqual(lancer.python(ctx, "tiffinfo.py"), 0)
        self.assertEqual(vu["cmd"][-1], IMAGE)

    def test_powershell_commande(self):
        vu = {}

        def executer(cmd, **k):
            vu["cmd"] = cmd
            return SimpleNamespace(returncode=0)
        pwsh = next(o for o in outils.OUTILS if o.cle == "pwsh")
        ctx = contexte(["1", PROJET, "L"], executer, etats=[outils.Etat(pwsh, r"C:\pwsh.exe", "7.6")])
        lancer.powershell(ctx, "nona_images.ps1", [Arg("-Projet", "p", type="pto")], "le dossier de rendu")
        self.assertEqual(vu["cmd"][:5], [r"C:\pwsh.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"])
        self.assertEqual(vu["cmd"][6:], ["-Projet", PROJET])

    def test_powershell_prerempli_depuis_les_outils_du_poste(self):
        vu = {}

        def executer(cmd, **k):
            vu["cmd"] = cmd
            return SimpleNamespace(returncode=0)
        ctx = contexte(["L"], executer, poste=config.Poste(outils={"vips": r"D:\O\vips.exe"}))
        lancer.powershell(ctx, "rendre_lisible.ps1", [Arg("-Vips", "v", type="chemin", config="outil:vips")], None)
        self.assertEqual(vu["cmd"][-2:], ["-Vips", r"D:\O\vips.exe"])


class TestConsole(unittest.TestCase):
    def test_console_cp1252_sans_plantage(self):
        import os
        import subprocess
        env = dict(os.environ, PYTHONIOENCODING="cp1252", NO_COLOR="1")
        r = subprocess.run([sys.executable, "-I", str(SCRIPTS / "panorama.py")], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=60, env=env, cwd=SCRIPTS)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("LANCEUR", r.stdout)


class TestLanceur(unittest.TestCase):
    def test_menu_principal_et_quitter(self):
        import panorama
        lignes = []
        ctx = contexte(["0"], ecrire=lignes.append)
        self.assertEqual(len(panorama.menu_principal(ctx)), 7)
        panorama.boucle_principale(ctx, effacer=lambda: None)
        self.assertIn("Aucun panorama courant", "\n".join(lignes))

    def test_nouveau_panorama_cree_et_rend_courant(self):
        import panorama
        with tempfile.TemporaryDirectory() as d:
            T = str(Path(d) / "pano")
            chemin_poste = Path(d) / "config.json"
            # date, focale, $T, dossier des RAW, $H, puis la grille et les pas
            ctx = contexte(["2026-06-19", "200", T, "", "", "6", "37", "7", "24", "5", "5.8", "20000", "90112"])
            with mock.patch.object(config, "chemin_poste", lambda: chemin_poste):
                panorama.nouveau_panorama(ctx)
            self.assertTrue((Path(T) / "Assemblage-Hugin" / "3_grille").is_dir())
            self.assertEqual(config.charger_panorama(T).pas_v, 5.8)
            self.assertEqual(config.charger_poste(chemin_poste).courant, T)
            self.assertEqual(ctx.panorama.colonnes, 37)

    def test_nouveau_panorama_propose_les_valeurs_du_panorama_courant_et_les_chemins_du_guide(self):
        import panorama
        with tempfile.TemporaryDirectory() as d:
            racine, raws = Path(d) / "Panoramas", Path(d) / "RAW" / "2026-07-01"
            invites = []
            reponses = iter(["2026-07-01", "y", "y", str(raws), "y", "y", "y", "", "y", "y", "6.2", "y", "y"])

            def lire(invite=""):
                invites.append(invite)
                return next(reponses)
            ctx = lancer.Contexte(poste=config.Poste(), panorama=None, etats=[], c=C, lire=lire, ecrire=lambda *a: None)
            ctx.panorama = config.Panorama(T=str(racine / "2026-06-19" / "200mm"), P="", H=str(Path(d) / "ancien" / "HDR"),
                                           lignes=6, colonnes=37, expos=7, focale=200.0, largeur_mm=24.0, pas_h=5.0,
                                           pas_v=5.8, largeur_hdr=20000, largeur_pleine=90112)
            with mock.patch.object(config, "chemin_poste", lambda: Path(d) / "config.json"):
                panorama.nouveau_panorama(ctx)
            T = str(racine / "2026-07-01" / "200mm")                 # 0D : <racine>\<date>\<focale>
            self.assertIn(f"[{T}]", invites[2])
            self.assertIn(f"[{raws / 'HDR'}]", invites[4])            # 0D : <dossier des RAW>\HDR, jamais l'ancien $H
            p = config.charger_panorama(T)
            self.assertEqual(p.H, str(raws / "HDR"))
            self.assertEqual((p.lignes, p.colonnes, p.expos, p.focale, p.pas_v, p.largeur_pleine), (6, 37, 7, 200.0, 6.2, 90112))

    def test_nouveau_panorama_reprend_le_panorama_json_existant(self):
        import panorama
        with tempfile.TemporaryDirectory() as d:
            T, H = str(Path(d) / "pano"), str(Path(d) / "RAW" / "HDR")    # $H est créé : jamais hors du dossier de test
            config.enregistrer_panorama(config.Panorama(T=T, P="", H=H, lignes=4, colonnes=20, expos=5,
                                                        maitre=r"3_optimisation\m.pto"))
            ctx = contexte(["y", "", T, "y", "y"] + ["y"] * 8)    # date, focale, $T, RAW et $H repris, puis le reste
            with mock.patch.object(config, "chemin_poste", lambda: Path(d) / "config.json"):
                panorama.nouveau_panorama(ctx)
            p = config.charger_panorama(T)
            self.assertEqual((p.H, p.lignes, p.colonnes, p.expos, p.largeur_mm, p.largeur_hdr), (H, 4, 20, 5, 24.0, 20000))
            self.assertTrue((Path(H) / "TIFF").is_dir())
            self.assertEqual(p.maitre, r"3_optimisation\m.pto")   # conservé, bien que non demandé

    def test_nouveau_panorama_x_annule_sans_rien_ecrire_et_nombre_invalide_redemande(self):
        import panorama
        with tempfile.TemporaryDirectory() as d:
            T = Path(d) / "pano"
            lignes = []
            ctx = contexte(["y", "", str(T), "", "", "six", "6", "x"], ecrire=lignes.append)
            with mock.patch.object(config, "chemin_poste", lambda: Path(d) / "config.json"):
                panorama.nouveau_panorama(ctx)
            self.assertIn("nombre entier attendu", "\n".join(map(str, lignes)))
            self.assertIn("rien n'a été écrit", "\n".join(map(str, lignes)))
            self.assertFalse(T.exists())

    def test_versions_affiche_un_tableau(self):
        import panorama
        lignes = []
        hugin = next(o for o in outils.OUTILS if o.cle == "hugin")
        ctx = contexte([], etats=[outils.Etat(hugin, r"C:\H\nona.exe", "2025.0.1"),
                                  outils.Etat(outils.OUTILS[3], None, None)], ecrire=lignes.append)
        panorama.versions(ctx)
        texte = "\n".join(lignes)
        self.assertIn("2025.0.1", texte)
        self.assertIn("ABSENT", texte)

    def test_installer_affiche_la_commande_et_n_execute_pas_sans_accord(self):
        import panorama
        lignes = []
        exif = next(o for o in outils.OUTILS if o.cle == "exiftool")
        ctx = contexte([""], executer=lambda *a, **k: self.fail("refusé"), etats=[outils.Etat(exif, None, None)],
                       ecrire=lignes.append)
        panorama.installer(ctx)
        self.assertIn("winget install --id OliverBetz.ExifTool", "\n".join(lignes))


class TestCheminementConsole(unittest.TestCase):
    def _contexte(self, d, valeurs, lignes=None):
        ctx = contexte(valeurs, ecrire=(lignes.append if lignes is not None else None))
        ctx.panorama = config.Panorama(T=d, P=str(Path(d) / "P"))
        config.enregistrer_panorama(ctx.panorama)
        return ctx

    def test_cheminement_ecrit_depart_et_serpentin(self):
        import panorama
        with tempfile.TemporaryDirectory() as d:
            ctx = self._contexte(d, ["bg", "s", "v"])
            panorama.cheminement(ctx)
            p = config.charger_panorama(d)
            self.assertEqual((p.depart, p.serpentin), ("bg", True))
            self.assertEqual((ctx.panorama.depart, ctx.panorama.serpentin), ("bg", True))

    def test_cheminement_annule(self):
        import panorama
        with tempfile.TemporaryDirectory() as d:
            ctx = self._contexte(d, ["bd", "x"])
            panorama.cheminement(ctx)
            p = config.charger_panorama(d)
            self.assertEqual((p.depart, p.serpentin), ("hd", False))

    def test_cheminement_saisie_invalide_redemande(self):
        import panorama
        lignes = []
        with tempfile.TemporaryDirectory() as d:
            ctx = self._contexte(d, ["zz", "x"], lignes)
            panorama.cheminement(ctx)
            self.assertIn("zz", "\n".join(map(str, lignes)))
            self.assertEqual(config.charger_panorama(d).depart, "hd")

    def test_cheminement_depart_inconnu_dans_le_panorama_json_ne_plante_pas(self):
        import panorama
        lignes = []
        with tempfile.TemporaryDirectory() as d:
            ctx = self._contexte(d, ["bg", "v"], lignes)
            config.mettre_a_jour(d, depart="zz")
            ctx.panorama = config.charger_panorama(d)
            panorama.cheminement(ctx)
            self.assertIn("zz", "\n".join(map(str, lignes)))
            self.assertEqual(config.charger_panorama(d).depart, "bg")      # l'utilisateur répare en validant

    def test_cheminement_affiche_le_dessin_et_le_resume(self):
        import panorama
        lignes = []
        with tempfile.TemporaryDirectory() as d:
            panorama.cheminement(self._contexte(d, ["x"], lignes))
        texte = "\n".join(map(str, lignes))
        self.assertIn("5 ← 4 ← 3 ← 2 ← 1", texte)
        self.assertIn("Départ haut droit", texte)

    def test_cheminement_sans_panorama(self):
        import panorama
        lignes = []
        ctx = contexte([], ecrire=lignes.append)
        panorama.cheminement(ctx)
        self.assertIn("Aucun panorama courant", "\n".join(map(str, lignes)))

    def test_menu_phase0_propose_le_cheminement(self):
        import panorama
        from pilotage import menu
        ctx = contexte([])
        entrees = panorama.menu_phase0(ctx)
        e = next(x for x in entrees if x.tete_texte(ctx) == "Cheminement de la prise de vue")
        self.assertEqual((e.section, e.effet), ("PANORAMA", "panorama.json"))
        self.assertIsNotNone(menu.numeroter(entrees, ctx)[entrees.index(e)])


VERBES_ECRITURE = ("Renommer", "Rendre", "Tuiler", "Fusionner", "Reprojeter", "Générer", "Écrire", "Appliquer",
                   "Filtrer", "Replacer", "Affiner", "Reporter", "Extraire", "Rattacher", "Ranger", "Préparer",
                   "Remettre", "Redimensionner", "Nettoyer", "Cadrer", "Recadrer", "Rehausser", "Copier")


class TestSousMenus(unittest.TestCase):
    def test_tous_les_sous_menus_se_rendent_sans_panorama_ni_outil(self):
        import panorama
        from pilotage import menu
        ctx = contexte([])
        self.assertEqual(set(panorama.SOUS_MENUS), {"phase0", "phase2", "phase3", "rendus", "mesures", "phase7", "configuration"})
        for nom, constructeur in panorama.SOUS_MENUS.items():
            with self.subTest(nom):
                lignes = []
                table = menu.rendre(constructeur(ctx), ctx, C, ecrire=lignes.append)
                self.assertTrue(table, "au moins une entrée sélectionnable")

    def test_entrees_powershell_et_outils_grisees_sans_outil(self):
        import panorama
        ctx = contexte([])
        e = next(x for x in panorama.menu_rendus(ctx) if "rendre_projet.ps1" in x.sous_titre)
        self.assertFalse(e.disponible(ctx))
        self.assertIn("absent", e.raison(ctx) if callable(e.raison) else e.raison)
        hugin = next(o for o in outils.OUTILS if o.cle == "hugin")
        ctx2 = contexte([], etats=[outils.Etat(hugin, r"C:\H\nona.exe", "2025")])
        e2 = next(x for x in panorama.menu_phase3(ctx2) if "cpclean" in x.sous_titre)
        self.assertTrue(e2.disponible(ctx2))

    def test_garde_la_promesse_lecture_seule(self):
        """Une entrée sans effet déclaré ne porte pas un verbe d'écriture. Cette garde lit les libellés, pas le
        code des handlers : une action qui écrirait sans le déclarer y passerait."""
        import panorama
        ctx = contexte([])
        for nom, constructeur in panorama.SOUS_MENUS.items():
            for e in constructeur(ctx):
                if e.action is not None and e.effet is None:
                    self.assertFalse(e.tete_texte(ctx).startswith(VERBES_ECRITURE), f"{nom} : {e.tete_texte(ctx)}")
        # contre-témoin : la convention est en usage
        self.assertTrue(any(e.effet for e in panorama.menu_phase3(ctx)))

    def test_entree_console_5b_nona_lit_le_projet_hdr(self):
        import panorama
        from pilotage import catalogue, declarations_ps
        ctx = contexte([])
        tache = next(t for t in catalogue.console("rendus") if t.script == "nona_images.ps1")
        self.assertEqual(tache.repere, "5B")              # la seule entrée console des trois repères
        vu = []
        with mock.patch.object(panorama.lancer, "powershell", lambda ctx, script, args, ecrit: vu.append(args)):
            panorama.entree_depuis(tache).action(ctx)
        projet = next(a for a in vu[0] if a.nom == "-Projet")
        self.assertEqual(projet.config, "hdr_pto")
        declare = next(a for a in declarations_ps.PS["nona_images.ps1"][0] if a.nom == "-Projet")
        self.assertIsNone(declare.config)                 # la déclaration partagée reste intacte

    def test_entree_console_python_avec_lit(self):
        import panorama
        from pilotage.catalogue import Tache
        ctx = contexte([])
        t = Tache("x", 2, "2", "tiffinfo.py", lit={"image.tif": "pleine_res"}, groupe_console="phase2")
        vu = []
        with mock.patch.object(panorama.lancer, "python", lambda ctx, script, args, ecrit: vu.append(args)):
            panorama.entree_depuis(t).action(ctx)
        self.assertEqual(next(a for a in vu[0] if a.nom == "image.tif").config, "pleine_res")

    def test_action_sans_powershell_raison_de_l_outil(self):
        import panorama
        ctx = contexte([])
        e = next(x for x in panorama.menu_phase3(ctx) if "cpclean" in x.sous_titre)
        with mock.patch.object(panorama.lancer, "powershell_disponible", return_value=False):
            self.assertFalse(e.disponible(ctx))
            self.assertEqual(e.raison(ctx), "Hugin absent")    # cpclean ne dépend pas de PowerShell

    def test_gestes_hugin_et_lightroom_informatifs(self):
        import panorama
        ctx = contexte([])
        informatives = [e for e in panorama.menu_phase3(ctx) if e.action is None]
        self.assertTrue(any("3B" in e.tete_texte(ctx) for e in informatives))


class TestDeclarationsPs(unittest.TestCase):
    def test_un_script_powershell_sur_deux_declare(self):
        from pilotage import declarations_ps
        ps1 = {p.name for p in SCRIPTS.glob("*.ps1")} - {"enblend_vers_multiblend.ps1"}
        self.assertEqual(set(declarations_ps.PS), ps1)
        for nom, (args, ecrit) in declarations_ps.PS.items():
            with self.subTest(nom):
                self.assertTrue(args)
                for a in args:
                    self.assertTrue(a.nom.startswith("-"), a.nom)
                self.assertTrue(ecrit is None or isinstance(ecrit, str))


if __name__ == "__main__":
    unittest.main()
