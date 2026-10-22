"""Tests de interface.execution : sous-processus en arrière-plan, sortie capturée ligne à ligne, arrêt de l'arbre."""

import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

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
                ex.processus.wait()
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
        self.assertIsNotNone(ex)

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

    def test_octets_invalides_remplaces(self):
        code = "import sys; sys.stdout.buffer.write(b'caf\\xe9 ok\\n')"
        ex = self._demarrer("t/x.py", [sys.executable, "-c", code])
        self._attendre_fin(ex)
        self.assertEqual(ex.lignes, ["caf� ok"])

    def test_sortie_utf8_decodee(self):
        ex = self._demarrer("t/x.py", [sys.executable, "-c", "print('café – ok')"])
        self._attendre_fin(ex)
        self.assertEqual(ex.lignes, ["café – ok"])

    def test_echec_code_non_nul(self):
        ex = self._demarrer("t/x.py", [sys.executable, "-c", "raise SystemExit(3)"])
        self._attendre_fin(ex)
        self.assertEqual((ex.code, ex.etat), (3, "échec"))

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


class TestEnvironnementEtCommandes(unittest.TestCase):
    def test_environnement_enfant(self):
        env = lancer.environnement_enfant()
        self.assertEqual(env["GIGA_PANO_SANS_MENU"], "1")
        self.assertEqual(env["PYTHONIOENCODING"], "utf-8")

    def test_commande_python(self):
        ctx = type("C", (), {"scripts": SCRIPTS})()
        self.assertEqual(lancer.commande_python(ctx, "a.py", ["--x", "1"]), [sys.executable, str(SCRIPTS / "a.py"), "--x", "1"])

    def test_commande_powershell(self):
        ctx = type("C", (), {"scripts": SCRIPTS, "etats": []})()
        cmd = lancer.commande_powershell(ctx, "a.ps1", ["-Y"])
        self.assertEqual(cmd[1:], ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPTS / "a.ps1"), "-Y"])


if __name__ == "__main__":
    unittest.main()
