"""Tests de renommer_pano.py : nombre de fichiers, vues centrées seules, motif d'exposition, table RAW -> L_C_E.

Les images sont de vrais TIFF minuscules, écrits à la main, dont exiftool écrit la compensation d'exposition et le RAW
d'origine (XMP-crs:RawFileName) ; sans exiftool dans le PATH, les tests sont sautés. Lancés en sous-processus.
"""

import csv
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


def export(dossier, compensations, prefixe="Pano-", debut=1, raws=None):
    """<prefixe>1.tif … <prefixe>N.tif, l'image i portant la compensation compensations[i - 1] et, si raws est donné,
    le RAW d'origine raws[i - 1] (None : aucun). Un seul exiftool, une commande par image (-execute)."""
    lignes = []
    for k, v in enumerate(compensations):
        chemin = Path(dossier) / f"{prefixe}{k + debut:02d}.tif"
        chemin.write_bytes(TIFF_1PX)
        lignes += ["-q", "-overwrite_original", f"-ExposureCompensation={v}"]
        if raws and raws[k]:
            lignes.append(f"-XMP-crs:RawFileName={raws[k]}")
        lignes += [str(chemin), "-execute"]
    arguments = Path(dossier) / "_exiftool_args.txt"
    arguments.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    subprocess.run(["exiftool", "-charset", "filename=utf8", "-@", str(arguments)], check=True, capture_output=True)
    arguments.unlink()


def rafales_avec_raws(n_positions=6):
    """Compensations et RAW d'un export complet en rafales de 3 : le RAW n° k pour la k-ième image."""
    comp = HDR * n_positions
    return comp, [f"IMG_{k:04d}.CR2" for k in range(1, len(comp) + 1)]


def lire_table(chemin):
    with open(chemin, newline="", encoding="utf-8") as f:
        return [(r["raw"], r["lce"]) for r in csv.DictReader(f)]


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
            self.assertNotIn("Table RAW -> L_C_E écrite", r.stdout)
            self.assertEqual(noms(d), sorted(f"L{l}_C{c:02d}_E0.tif" for l in range(2) for c in range(3)))

    def test_rafales_completes(self):
        with tempfile.TemporaryDirectory() as d:
            export(d, HDR * 6)
            r = lancer(d, "--expos", "3", "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("identique sur les 6 rafales", r.stdout)
            self.assertTrue((Path(d) / "L1_C02_E2.tif").exists())
            self.assertIn("Sans --table", r.stdout)

    def test_export_complet_ecrit_la_table(self):
        with tempfile.TemporaryDirectory() as d:
            comp, raws = rafales_avec_raws()
            export(d, comp, prefixe="Pano_HDR-", raws=raws)
            table = Path(d) / "P" / "table_raw_LCE.csv"
            essai = lancer(d, "--expos", "3", "--table", str(table))
            self.assertIn("sera écrite", essai.stdout)
            self.assertFalse(table.exists())                       # essai à blanc : rien d'écrit
            r = lancer(d, "--expos", "3", "--apply", "--table", str(table))
            self.assertEqual(r.returncode, 0, r.stderr)
            t = lire_table(table)
            self.assertEqual(len(t), 18)
            self.assertEqual(t[0], ("IMG_0001.CR2", "L0_C00_E0.tif"))
            self.assertIn(("IMG_0018.CR2", "L1_C02_E2.tif"), t)
            self.assertEqual([lce for _, lce in t], sorted(lce for _, lce in t))   # trié comme renommer_par_raw.py

    def test_export_suivant_controle_par_la_table(self):
        with tempfile.TemporaryDirectory() as d:
            comp, raws = rafales_avec_raws()
            table = Path(d) / "table_raw_LCE.csv"
            (Path(d) / "L").mkdir()
            export(Path(d) / "L", comp, prefixe="Pano_HDR-", raws=raws)
            self.assertEqual(lancer(Path(d) / "L", "--expos", "3", "--apply", "--table", str(table)).returncode, 0)
            # export H : les vues centrées (1 RAW sur 3), dans l'ordre de prise
            (Path(d) / "H").mkdir()
            export(Path(d) / "H", [0] * 6, prefixe="Pano_E0-", raws=raws[::3])
            r = lancer(Path(d) / "H", "--expos", "3", "--apply", "--table", str(table))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Plan conforme à la table", r.stdout)
            self.assertTrue((Path(d) / "H" / "L1_C02_E0.tif").exists())

    def test_ordre_faux_detecte_par_la_table_sans_rien_modifier(self):
        with tempfile.TemporaryDirectory() as d:
            comp, raws = rafales_avec_raws()
            table = Path(d) / "table_raw_LCE.csv"
            (Path(d) / "L").mkdir()
            export(Path(d) / "L", comp, prefixe="Pano_HDR-", raws=raws)
            lancer(Path(d) / "L", "--expos", "3", "--apply", "--table", str(table))
            (Path(d) / "H").mkdir()
            centrees = raws[::3]
            centrees[1], centrees[2] = centrees[2], centrees[1]    # deux positions exportées dans le mauvais ordre
            export(Path(d) / "H", [0] * 6, prefixe="Pano_E0-", raws=centrees)
            avant = noms(Path(d) / "H")
            r = lancer(Path(d) / "H", "--expos", "3", "--apply", "--table", str(table))
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("2 écart(s) avec la table", r.stderr)
            self.assertIn("la table dit L0_C02_E0.tif", r.stdout)
            self.assertEqual(noms(Path(d) / "H"), avant)

    def test_pas_de_table_pour_un_export_partiel_ou_sans_raw(self):
        with tempfile.TemporaryDirectory() as d:
            table = Path(d) / "table_raw_LCE.csv"
            (Path(d) / "H").mkdir()
            export(Path(d) / "H", [0] * 6, prefixe="Pano_E0-", raws=[f"R{k}.CR2" for k in range(6)])
            r = lancer(Path(d) / "H", "--expos", "3", "--apply", "--table", str(table))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("un export partiel ne l'écrit pas", r.stdout)
            self.assertFalse(table.exists())
            (Path(d) / "L").mkdir()
            comp, raws = rafales_avec_raws()
            raws[4] = None
            export(Path(d) / "L", comp, prefixe="Pano_HDR-", raws=raws)
            r = lancer(Path(d) / "L", "--expos", "3", "--apply", "--table", str(table))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("1 fichier(s) sans RAW d'origine", r.stdout)
            self.assertFalse(table.exists())

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
