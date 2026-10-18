"""Détection des outils de la chaîne (Hugin, multiblend, libvips, ExifTool, Python, Pillow, PowerShell).

Pour chaque outil : chemin trouvé (configuration du poste, puis PATH, puis emplacements habituels), version lue
en lançant l'exécutable (toute erreur donne « version inconnue », jamais une exception), commande d'installation
proposée (winget, pip) ou page de téléchargement. Rien n'est installé ici : le lanceur demande d'abord.
"""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

PYTHON = "<python>"   # exécutable résolu en sys.executable au moment de la détection


@dataclass
class Outil:
    cle: str
    nom: str
    executable: str
    args_version: list
    motif: str                      # regex, groupe 1 = version
    candidats: list                 # chemins absolus à essayer après la configuration et le PATH
    winget: Optional[str]
    url: Optional[str]
    dezipper: Optional[str] = None  # dossier conseillé pour une archive
    version_requise: bool = False   # présent seulement si la version se lit (Pillow : l'import doit réussir)


OUTILS = [
    Outil("hugin", "Hugin", "nona.exe", ["--help"], r"nona version ([\d.]+)",
          [r"C:\Program Files\Hugin\bin\nona.exe"], "Hugin.Hugin", "https://hugin.sourceforge.io/download/"),
    Outil("enblend", "enblend", "enblend.exe", ["--version"], r"enblend ([\d.]+)",
          [r"C:\Program Files\Hugin\bin\enblend.exe"], None, "https://hugin.sourceforge.io/download/"),
    Outil("multiblend", "multiblend", "multiblend.exe", ["--help"], r"[Mm]ultiblend v?([\d.]+)",
          [r"D:\Outils\multiblend\multiblend.exe"], None, "http://horman.net/multiblend/", r"D:\Outils\multiblend\\"),
    Outil("vips", "libvips", "vips.exe", ["--version"], r"vips-([\d.]+)",
          [r"D:\Outils\libvips\vips-dev-8.18\bin\vips.exe"], None,
          "https://github.com/libvips/build-win64-mxe/releases/latest", r"D:\Outils\libvips\\"),
    Outil("exiftool", "ExifTool", "exiftool.exe", ["-ver"], r"^\s*([\d.]+)", [], "OliverBetz.ExifTool",
          "https://exiftool.org/"),
    Outil("python", "Python", PYTHON, ["--version"], r"Python ([\d.]+)", [], "Python.Python.3.13",
          "https://www.python.org/downloads/windows/"),
    Outil("pillow", "Pillow", PYTHON, ["-c", "import PIL; print(PIL.__version__)"], r"^\s*([\d.]+)", [], None, None,
          version_requise=True),
    Outil("pwsh", "PowerShell 7", "pwsh.exe", ["-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
          r"^\s*([\d.]+)", [], "Microsoft.PowerShell", "https://learn.microsoft.com/powershell/"),
]

RESUME_CLES = ["hugin", "multiblend", "vips", "exiftool"]


@dataclass
class Etat:
    outil: Outil
    chemin: Optional[str]
    version: Optional[str]

    @property
    def present(self):
        return self.chemin is not None


def _chemin(outil, configures, which):
    if outil.executable == PYTHON:
        return sys.executable
    configure = configures.get(outil.cle)
    if configure and os.path.exists(configure):
        if os.path.isdir(configure):               # dossier Hugin configuré : on y cherche l'exécutable
            dans_dossier = os.path.join(configure, outil.executable)
            return dans_dossier if os.path.exists(dans_dossier) else None
        return configure
    trouve = which(outil.executable)
    if trouve:
        return trouve
    for candidat in outil.candidats:
        if os.path.exists(candidat):
            return candidat
    return None


def _version(outil, chemin, lancer):
    try:
        r = lancer([chemin, *outil.args_version], capture_output=True, text=True, timeout=20)
    except Exception:
        return None
    if getattr(r, "returncode", 1) != 0:
        return None
    sortie = (getattr(r, "stdout", "") or "") + "\n" + (getattr(r, "stderr", "") or "")
    m = re.search(outil.motif, sortie, re.MULTILINE)
    return m.group(1) if m else None


def detecter(outil, configures, which=shutil.which, lancer=subprocess.run):
    chemin = _chemin(outil, configures or {}, which)
    if chemin is None:
        return Etat(outil, None, None)
    version = _version(outil, chemin, lancer)
    if outil.version_requise and version is None:
        return Etat(outil, None, None)
    return Etat(outil, chemin, version)


def detecter_tous(configures):
    return [detecter(o, configures) for o in OUTILS]


def resume(etats, c):
    morceaux = []
    for e in etats:
        if e.outil.cle in RESUME_CLES:
            etat = f"{c.OK}OK{c.RESET}" if e.present else f"{c.ERREUR}ABSENT{c.RESET}"
            morceaux.append(f"{e.outil.nom} {etat}")
    return " · ".join(morceaux)


def commande_installation(outil):
    if outil.cle == "pillow":
        return f'"{sys.executable}" -m pip install pillow'   # le pip de CE Python, pas un autre du PATH
    if outil.winget:
        return f"winget install --id {outil.winget} -e --accept-package-agreements --accept-source-agreements"
    return None


def dossiers_presets_lightroom(appdata=None):
    """(libellé, chemin, existe) pour les deux dossiers de préréglages Lightroom sous %APPDATA%."""
    base = Path(appdata or os.environ.get("APPDATA", str(Path.home())))
    dossiers = [
        ("Préréglages d'export", base / "Adobe" / "Lightroom" / "Export Presets"),
        ("Préréglages de développement", base / "Adobe" / "CameraRaw" / "Settings"),
    ]
    return [(libelle, chemin, chemin.is_dir()) for libelle, chemin in dossiers]
