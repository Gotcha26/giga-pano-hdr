"""Tests de renommer_pano.py : nombre de fichiers, vues centrées seules, motif d'exposition (sous-processus).

Les images sont de vrais TIFF minuscules (Pillow) dont exiftool écrit la compensation d'exposition ; sans exiftool
dans le PATH, les tests sont sautés.
"""

import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "renommer_pano.py"
HDR = [0, -1, 1]                  # motif d'une rafale de 3, la référence en tête


def _tiff_1px():
    """TIFF minimal valide : 1 x 1 pixel, niveaux de gris 8 bits, sans compression."""
    entrees = [(256, 3, 1), (257, 3, 1), (258, 3, 8), (259, 3, 1), (262, 3, 1), (273, 4, 110), (278, 3, 1), (279, 4, 1)]
    ifd = struct.pack("<H", len(entrees)) + b"".join(struct.pack("<HHII", t, typ, 1, v) for t, typ, v in entrees)
    return b"II*\x00" + struct.pack("<I", 8) + ifd + struct.pack("<I", 0) + b"\x80"


TIFF_1PX = _tiff_1px()


def lancer(dossier, *args):
    env = dict(os.environ, GIGA_PANO_SANS_MENU="1", PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, str(SCRIPT), str(dossier), "--lignes", "2", "--colonnes", "3", *args],
                          capture_output=True, text=True, encoding="utf-8", env=env, stdin=subprocess.DEVNULL)


def export(dossier, compensations, prefixe="Pano-", debut=1):
    """<prefixe>1.tif … <prefixe>N.tif, l'image i portant la compensation compensations[i - 1]."""
    par_valeur = {}
    for i, v in enumerate(compensations, debut):
        chemin = Path(dossier) / f"{prefixe}{i:02d}.tif"
        chemin.write_bytes(TIFF_1PX)
        par_valeur.setdefault(v, []).append(str(chemin))
    for v, chemins in par_valeur.items():
        subprocess.run(["exiftool", "-q", "-overwrite_original", f"-ExposureCompensation={v}", *chemins], check=True)


def noms(dossier):
    return sorted(p.name for p in Path(dossier).glob("*.tif"))


@unittest.skipUnless(shutil.which("exiftool"), "exiftool absent du PATH")
class TestRenommerPano(unittest.TestCase):
    def test_vues_centrees_seules_nommees_e0(self):
        with tempfile.TemporaryDirectory() as d:
            export(d, [0.7] * 6)            # la référence n'est pas forcément 0 IL
            r = lancer(d, "--expos", "7", "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("vues centrées seules", r.stdout)
            self.assertIn("Exposition identique sur les 6 vues", r.stdout)
            self.assertNotIn("table RAW", r.stdout)      # un export de vues centrées ne fait pas la table
            self.assertEqual(noms(d), sorted(f"L{l}_C{c:02d}_E0.tif" for l in range(2) for c in range(3)))

    def test_rafales_completes(self):
        with tempfile.TemporaryDirectory() as d:
            export(d, HDR * 6)
            r = lancer(d, "--expos", "3", "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("identique sur les 6 rafales", r.stdout)
            self.assertTrue((Path(d) / "L1_C02_E2.tif").exists())
            self.assertIn("table RAW -> L_C_E", r.stdout)       # rappel de l'étape suivante (2F)

    def test_nombre_faux_bloque(self):
        with tempfile.TemporaryDirectory() as d:
            export(d, HDR * 3 + [0])
            r = lancer(d, "--expos", "3")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("nombre de fichiers différent", r.stderr)

    def test_intruse_parmi_les_vues_centrees_bloque_sans_rien_modifier(self):
        with tempfile.TemporaryDirectory() as d:
            export(d, [-2] + [0] * 5)       # l'intruse en tête : la référence reste la valeur majoritaire
            avant = noms(d)
            r = lancer(d, "--expos", "7", "--apply")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("Pano-01.tif : -2 IL, attendu +0 IL", r.stdout)
            self.assertIn("1 anomalie(s)", r.stderr)
            self.assertEqual(noms(d), avant)

    def test_rafale_hdr_rompue_bloque_sans_rien_modifier(self):
        with tempfile.TemporaryDirectory() as d:
            export(d, HDR * 4 + [0, 1, -1] + HDR)     # deux expositions inversées dans la 5e rafale
            avant = noms(d)
            r = lancer(d, "--expos", "3", "--apply")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("2 anomalie(s)", r.stderr)
            self.assertEqual(noms(d), avant)

    def test_force_ne_leve_pas_le_controle_du_motif(self):
        with tempfile.TemporaryDirectory() as d:
            export(d, HDR * 5 + [0, 1, -1])
            r = lancer(d, "--expos", "3", "--apply", "--force")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("anomalie(s) du motif", r.stderr)

    def test_reference_hors_tete_bloque(self):
        with tempfile.TemporaryDirectory() as d:
            export(d, [-1, 0, 1] * 6)       # répétitif, mais la première image n'est pas la référence
            r = lancer(d, "--expos", "3", "--apply")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("ne peut pas être nommée _E0", r.stdout)

    def test_prefixe_e0_impose_les_vues_centrees(self):
        with tempfile.TemporaryDirectory() as d:
            export(d, [0] * 6, prefixe="Pano_E0-")
            r = lancer(d, "--expos", "7", "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("export Pano_E0-, vues centrées seules", r.stdout)
            self.assertTrue((Path(d) / "L1_C02_E0.tif").exists())

    def test_prefixe_e0_en_nombre_faux_bloque(self):
        with tempfile.TemporaryDirectory() as d:
            export(d, [0] * 18, prefixe="Pano_E0-")       # le compte d'un export L sous le préfixe de l'export H
            r = lancer(d, "--expos", "3")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("nombre de fichiers différent", r.stderr)

    def test_prefixe_hdr_ne_se_prend_pas_pour_des_vues_centrees(self):
        with tempfile.TemporaryDirectory() as d:
            export(d, [0] * 6, prefixe="Pano_HDR-")
            r = lancer(d, "--expos", "3")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("nombre de fichiers différent", r.stderr)

    def test_exports_melanges_bloque_sans_rien_modifier(self):
        with tempfile.TemporaryDirectory() as d:
            export(d, [0] * 5, prefixe="Pano_E0-")
            export(d, [0], prefixe="Pano_HDR-", debut=6)
            avant = noms(d)
            r = lancer(d, "--apply", "--force")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("plusieurs exports mélangés", r.stderr)
            self.assertEqual(noms(d), avant)

    def test_expositions_identiques_dans_la_rafale_bloque(self):
        with tempfile.TemporaryDirectory() as d:
            export(d, [0] * 18)             # 18 vues identiques déclarées en rafales de 3 : pas un HDR
            r = lancer(d, "--expos", "3", "--apply")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("pas un motif HDR", r.stdout)


if __name__ == "__main__":
    unittest.main()
