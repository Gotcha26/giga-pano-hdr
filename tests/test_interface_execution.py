"""Tests de interface.execution : sous-processus en arrière-plan, sortie capturée ligne à ligne, arrêt de l'arbre."""

import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from interface import execution  # noqa: E402
from pilotage import lancer  # noqa: E402

DORMIR = [sys.executable, "-c", "import time; time.sleep(60)"]


class TestExecutionArrierePlan(unittest.TestCase):
    def setUp(self):
        self._lancees = []
        self.addCleanup(self._nettoyer)

    def _nettoyer(self):
        for ex in self._lancees:
            if ex.processus is not None and ex.processus.poll() is None:
                ex.processus.kill()
                ex.processus.wait(10)
            ex.fini.wait(10)
            if ex.processus is not None and ex.processus.stdout:
                ex.processus.stdout.close()
        execution.REGISTRE.clear()

    def _demarrer(self, identifiant, commande, **kw):
        ex = execution.demarrer(identifiant, commande, cwd=str(SCRIPTS), env=lancer.environnement_enfant(), **kw)
        self._lancees.append(ex)
        return ex

    def _attendre_fin(self, ex):
        self.assertTrue(ex.fini.wait(30))

    def test_capture_ligne_a_ligne_et_etat_terminee(self):
        vues = []
        ex = self._demarrer("t/x.py", [sys.executable, "-c", "print('un'); print('deux')"], sur_ligne=vues.append)
        self._attendre_fin(ex)
        self.assertEqual(ex.lignes, ["un", "deux"])
        self.assertEqual(vues, ["un", "deux"])
        self.assertEqual(ex.etat, "terminée")
        self.assertEqual(ex.code, 0)

    def test_sur_fin_appele_avec_l_execution_terminee(self):
        fin = threading.Event()
        vus = []
        ex = self._demarrer("t/x.py", [sys.executable, "-c", "pass"],
                            sur_fin=lambda e: (vus.append((e.etat, e.code)), fin.set()))
        self.assertTrue(fin.wait(30))
        self.assertEqual(vus, [("terminée", 0)])
        self.assertTrue(ex.fini.wait(5))

    def test_fins_de_ligne_windows_et_derniere_ligne_sans_saut(self):
        code = "import sys; sys.stdout.buffer.write(b'a\\r\\nb\\n\\nfin')"
        ex = self._demarrer("t/x.py", [sys.executable, "-c", code])
        self._attendre_fin(ex)
        self.assertEqual(ex.lignes, ["a", "b", "", "fin"])

    def test_erreurs_melangees_a_la_sortie(self):
        code = "import sys; sys.stderr.write('oups\\n')"
        ex = self._demarrer("t/x.py", [sys.executable, "-c", code])
        self._attendre_fin(ex)
        self.assertEqual(ex.lignes, ["oups"])

    def test_octets_non_utf8_decodes_dans_la_page_de_la_console(self):
        code = "import sys; sys.stdout.buffer.write(b'caf\\xe9 ok\\n')"
        with mock.patch.object(execution, "page_oem", return_value="cp1252"):
            ex = self._demarrer("t/x.py", [sys.executable, "-c", code])
            self._attendre_fin(ex)
        self.assertEqual(ex.lignes, ["café ok"])

    def test_sortie_utf8_decodee(self):
        ex = self._demarrer("t/x.py", [sys.executable, "-c", "print('café – ok')"])
        self._attendre_fin(ex)
        self.assertEqual(ex.lignes, ["café – ok"])

    def test_echec_code_non_nul(self):
        ex = self._demarrer("t/x.py", [sys.executable, "-c", "raise SystemExit(3)"])
        self._attendre_fin(ex)
        self.assertEqual((ex.code, ex.etat), (3, "échec"))

    def test_entree_standard_fermee_input_echoue_au_lieu_de_bloquer(self):
        ex = self._demarrer("t/x.py", [sys.executable, "-c", "input('? ')"])
        self._attendre_fin(ex)
        self.assertEqual(ex.etat, "échec")
        self.assertNotEqual(ex.code, 0)

    def test_code_130_interrompue(self):
        ex = self._demarrer("t/x.py", [sys.executable, "-c", "raise SystemExit(130)"])
        self._attendre_fin(ex)
        self.assertEqual((ex.code, ex.etat), (130, "interrompue"))

    def test_arreter_passe_par_taskkill_et_etat_interrompue(self):
        vu = []
        ex = self._demarrer("t/x.py", DORMIR)
        execution.arreter(ex, lancer=lambda c, **k: (vu.append(c), ex.processus.kill()))
        self._attendre_fin(ex)
        if sys.platform == "win32":
            self.assertEqual(vu[0][:4], ["taskkill", "/T", "/F", "/PID"])
            self.assertEqual(vu[0][4], str(ex.processus.pid))
        self.assertTrue(ex.arret_demande)
        self.assertEqual(ex.etat, "interrompue")

    @unittest.skipUnless(sys.platform == "win32", "taskkill n'existe que sous Windows")
    def test_arreter_reellement_avec_taskkill(self):
        ex = self._demarrer("t/x.py", DORMIR)
        execution.arreter(ex)
        self._attendre_fin(ex)
        self.assertIsNotNone(ex.processus.poll())
        self.assertEqual(ex.etat, "interrompue")

    @staticmethod
    def _pid_existe(pid):
        sortie = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"], capture_output=True,
                                text=True, errors="replace").stdout
        return f'"{pid}"' in sortie

    @unittest.skipUnless(sys.platform == "win32", "taskkill /T n'existe que sous Windows")
    def test_arreter_tue_aussi_les_descendants(self):
        parent = ("import subprocess, sys, time\n"
                  "e = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],"
                  " stdout=subprocess.DEVNULL)\n"
                  "print(e.pid, flush=True)\n"
                  "time.sleep(60)\n")
        ex = self._demarrer("t/arbre.py", [sys.executable, "-c", parent])
        limite = time.monotonic() + 20
        while not ex.lignes and time.monotonic() < limite:
            time.sleep(0.05)
        self.assertTrue(ex.lignes, "le parent n'a pas imprimé le PID de son enfant")
        enfant = int(ex.lignes[0])

        def tuer_l_enfant():                                    # même en cas d'échec : aucun processus résiduel
            subprocess.run(["taskkill", "/F", "/PID", str(enfant)], capture_output=True)
        self.addCleanup(tuer_l_enfant)
        self.assertTrue(self._pid_existe(enfant), "l'enfant devrait vivre avant l'arrêt")

        execution.arreter(ex)
        self._attendre_fin(ex)
        limite = time.monotonic() + 10
        while self._pid_existe(enfant) and time.monotonic() < limite:
            time.sleep(0.2)
        self.assertFalse(self._pid_existe(enfant), "taskkill /T doit emporter l'enfant du processus arrêté")

    def test_registre_et_en_cours(self):
        ex = self._demarrer("t/x.py", DORMIR)
        self.assertIs(execution.derniere("t/x.py"), ex)
        self.assertIn(ex, execution.en_cours())
        execution.arreter(ex)
        self._attendre_fin(ex)
        self.assertNotIn(ex, execution.en_cours())
        self.assertIs(execution.derniere("t/x.py"), ex)

    def test_derniere_inconnue(self):
        self.assertIsNone(execution.derniere("inconnu/x.py"))

    def test_une_nouvelle_execution_remplace_la_precedente(self):
        a = self._demarrer("t/x.py", [sys.executable, "-c", "pass"])
        self._attendre_fin(a)
        b = self._demarrer("t/x.py", [sys.executable, "-c", "pass"])
        self.assertIs(execution.derniere("t/x.py"), b)

    def test_sortie_python_lue_en_direct_sans_tampon(self):
        code = "import time; print('debut'); time.sleep(2); print('fin')"
        ex = self._demarrer("t/x.py", [sys.executable, "-c", code])
        time.sleep(1)
        self.assertEqual(ex.lignes, ["debut"])
        self._attendre_fin(ex)
        self.assertEqual(ex.lignes, ["debut", "fin"])

    def test_meme_tache_deja_en_cours_refusee(self):
        ex = self._demarrer("t/x.py", DORMIR)
        with self.assertRaisesRegex(execution.DejaEnCours, "tâche déjà en cours : t/x.py"):
            self._demarrer("t/x.py", [sys.executable, "-c", "pass"])
        self.assertIs(execution.derniere("t/x.py"), ex)
        autre = self._demarrer("t/y.py", [sys.executable, "-c", "pass"])     # une autre tâche, elle, démarre
        self._attendre_fin(autre)

    def test_exception_dans_un_rappel_ne_tue_pas_la_lecture(self):
        def casse(ligne):
            raise ValueError("boum")

        ex = self._demarrer("t/x.py", [sys.executable, "-c", "print('un'); print('deux')"], sur_ligne=casse)
        self._attendre_fin(ex)
        self.assertIn("un", ex.lignes)
        self.assertIn("deux", ex.lignes)
        self.assertEqual(ex.etat, "terminée")
        self.assertEqual(sum("boum" in l for l in ex.lignes), 2)

    def test_commande_introuvable_leve_oserror_sans_registre(self):
        with self.assertRaises(OSError):
            execution.demarrer("t/absent", ["commande-qui-n-existe-pas-xyz"], cwd=str(SCRIPTS), env=lancer.environnement_enfant())
        self.assertIsNone(execution.derniere("t/absent"))

    def test_repr_sans_processus(self):
        ex = self._demarrer("t/x.py", [sys.executable, "-c", "pass"])
        self._attendre_fin(ex)
        self.assertNotIn("processus", repr(ex))

    def test_un_enfant_qui_garde_la_sortie_ne_bloque_pas_la_fin(self):
        petit = "import time; time.sleep(2); print('tard', flush=True)"
        code = (f"import subprocess, sys; subprocess.Popen([sys.executable, '-c', {petit!r}], stdout=sys.stdout);"
                " print('parent fini', flush=True)")
        with mock.patch.object(execution, "DELAI_FIN", 0.3):
            ex = self._demarrer("t/x.py", [sys.executable, "-c", code])
            self.assertTrue(ex.fini.wait(1.8))          # avant la fin du petit-enfant (2 s)
        self.assertEqual((ex.etat, ex.code), ("terminée", 0))
        self.assertIn("parent fini", ex.lignes)
        self.assertTrue(any("un enfant garde la sortie" in l for l in ex.lignes))
        fin = time.time() + 10
        while "tard" not in ex.lignes and time.time() < fin:    # la suite arrive encore dans le journal
            time.sleep(0.1)
        self.assertIn("tard", ex.lignes)


class _FauxProcessus:
    """Processus factice : sortie fournie d'avance, lecture retenue jusqu'à `liberer`, wait/poll pilotables."""

    def __init__(self, sortie=b"", code=0, retenir=False, delais_depasses=0):
        self.pid = 4242
        self._sortie, self._code = sortie, code
        self._libre = threading.Event()
        if not retenir:
            self._libre.set()
        self.delais_depasses = delais_depasses
        self.attentes = []
        self.stdout = self

    def read(self, n):
        self._libre.wait(10)
        bloc, self._sortie = self._sortie, b""
        return bloc

    def liberer(self):
        self._libre.set()

    def wait(self, timeout=None):
        self.attentes.append(timeout)
        if timeout is not None and self.delais_depasses:
            self.delais_depasses -= 1
            raise subprocess.TimeoutExpired("faux", timeout)
        return self._code

    def poll(self):
        return self._code

    def kill(self):
        pass


class TestExecutionFactice(unittest.TestCase):
    def setUp(self):
        self.addCleanup(execution.REGISTRE.clear)

    def _demarrer(self, proc, plateforme=None, **kw):
        vu = {}

        def Popen(cmd, **k):
            vu.update(k)
            return proc
        if plateforme:
            with mock.patch.object(execution.sys, "platform", plateforme):
                ex = execution.demarrer("t/f.py", ["x"], cwd=".", env={}, Popen=Popen, **kw)
        else:
            ex = execution.demarrer("t/f.py", ["x"], cwd=".", env={}, Popen=Popen, **kw)
        return ex, vu

    def test_arreter_un_processus_deja_fini_garde_l_etat_terminee(self):
        proc = _FauxProcessus(b"ok\n", code=0, retenir=True)
        ex, _ = self._demarrer(proc)
        vu = []
        execution.arreter(ex, lancer=lambda c, **k: vu.append(c))
        proc.liberer()
        self.assertTrue(ex.fini.wait(5))
        self.assertEqual((ex.etat, ex.code, ex.arret_demande, vu), ("terminée", 0, False, []))

    def test_popen_et_taskkill_sans_fenetre_sous_windows(self):
        proc = _FauxProcessus(retenir=True)
        proc.poll = lambda: None                    # tourne encore
        ex, vu = self._demarrer(proc, plateforme="win32")
        self.assertTrue(vu["creationflags"] & execution.SANS_FENETRE)
        appels = []
        with mock.patch.object(execution.sys, "platform", "win32"):
            execution.arreter(ex, lancer=lambda c, **k: appels.append(k))
        self.assertTrue(appels[0]["creationflags"] & execution.SANS_FENETRE)
        proc.liberer()
        self.assertTrue(ex.fini.wait(5))

    def test_pas_de_creationflags_hors_windows(self):
        ex, vu = self._demarrer(_FauxProcessus(), plateforme="linux")
        self.assertNotIn("creationflags", vu)
        self.assertTrue(ex.fini.wait(5))

    def test_sortie_fermee_processus_encore_vivant_puis_fini(self):
        proc = _FauxProcessus(b"un\n", code=0, delais_depasses=1)
        vues = []
        ex, _ = self._demarrer(proc, sur_ligne=vues.append)
        self.assertTrue(ex.fini.wait(5))
        self.assertEqual((ex.etat, ex.code), ("terminée", 0))
        self.assertIn(execution.DELAI_FIN, proc.attentes)
        self.assertTrue(any(l.startswith("[interface] sortie fermée") for l in ex.lignes))
        self.assertEqual(vues, ex.lignes)              # les lignes [interface] passent aussi par sur_ligne

    def test_rappel_qui_leve_sur_une_ligne_interface_n_en_ajoute_pas(self):
        def casse(ligne):
            raise ValueError("boum")
        proc = _FauxProcessus(b"un\n", code=0, delais_depasses=1)
        ex, _ = self._demarrer(proc, sur_ligne=casse)
        self.assertTrue(ex.fini.wait(5))
        # « un » -> une erreur de rappel ; l'erreur et la ligne « sortie fermée » ne produisent rien de plus
        self.assertEqual(len(ex.lignes), 3)
        self.assertEqual(sum("boum" in l for l in ex.lignes), 1)

    def test_note_de_l_enfant_seulement_si_la_surveillance_clot(self):
        vues = []
        ex = execution.Execution("t/f.py", ["x"], processus=_FauxProcessus())
        ex.conclue = True                                   # la lecture a déjà conclu (sur_fin encore en cours)
        execution._conclure(ex, vues.append, None, code=0, note=execution.NOTE_ENFANT)
        self.assertEqual((ex.lignes, vues), ([], []))
        ex = execution.Execution("t/f.py", ["x"], processus=_FauxProcessus())
        execution._conclure(ex, vues.append, None, code=0, note=execution.NOTE_ENFANT)
        self.assertEqual((ex.lignes, vues, ex.etat), ([execution.NOTE_ENFANT], [execution.NOTE_ENFANT], "terminée"))

    def test_deja_en_cours_est_une_runtime_error(self):
        self.assertTrue(issubclass(execution.DejaEnCours, RuntimeError))


class TestDecodage(unittest.TestCase):
    def test_utf8_d_abord(self):
        self.assertEqual(execution._decoder("café".encode("utf-8")), "café")

    def test_repli_sur_la_page_de_la_console(self):
        with mock.patch.object(execution, "page_oem", return_value="cp850"):
            self.assertEqual(execution._decoder(b"caf\x82"), "café")
        with mock.patch.object(execution, "page_oem", return_value="cp1252"):
            self.assertEqual(execution._decoder(b"caf\xe9"), "café")

    def test_page_utf8_ou_inconnue_remplace(self):
        for page in ("cp65001", "cp-inconnue"):
            with mock.patch.object(execution, "page_oem", return_value=page):
                self.assertEqual(execution._decoder(b"caf\xe9"), "caf�", page)

    @unittest.skipUnless(sys.platform == "win32", "page OEM de Windows")
    def test_page_oem_systeme_et_non_celle_de_la_console(self):
        import ctypes
        with mock.patch.object(ctypes.windll.kernel32, "GetOEMCP", return_value=437, create=True), \
                mock.patch.object(ctypes.windll.kernel32, "GetConsoleOutputCP", return_value=65001, create=True):
            self.assertEqual(execution.page_oem(), "cp437")

    def test_page_oem_hors_windows(self):
        with mock.patch.object(execution.sys, "platform", "linux"):
            self.assertEqual(execution.page_oem(), "cp850")


class TestEnvironnementEtCommandes(unittest.TestCase):
    def test_environnement_enfant(self):
        env = lancer.environnement_enfant()
        self.assertEqual(env["GIGA_PANO_SANS_MENU"], "1")
        self.assertEqual(env["PYTHONIOENCODING"], "utf-8")
        self.assertEqual(env["PYTHONUNBUFFERED"], "1")

    def test_commande_python(self):
        ctx = type("C", (), {"scripts": SCRIPTS})()
        self.assertEqual(lancer.commande_python(ctx, "a.py", ["--x", "1"]), [sys.executable, str(SCRIPTS / "a.py"), "--x", "1"])

    def test_commande_powershell(self):
        ctx = type("C", (), {"scripts": SCRIPTS, "etats": []})()
        cmd = lancer.commande_powershell(ctx, "a.ps1", ["-Y"])
        self.assertEqual(cmd[1:], ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPTS / "a.ps1"), "-Y"])


if __name__ == "__main__":
    unittest.main()
