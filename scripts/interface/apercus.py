"""Aperçus des images produites : liste d'un dossier et JPEG réduit par libvips, mis en cache hors du panorama.

Logique pure, sans NiceGUI. Le cache vit dans %LOCALAPPDATA%\\giga-pano-hdr\\apercus (repli ~/.giga-pano-hdr/apercus),
jamais sous $T ; son nom dépend du chemin et de la date de modification, donc un fichier retouché est re-réduit.
"""

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

EXTENSIONS = (".tif", ".tiff", ".jpg", ".jpeg", ".png")
LARGEUR = 2000


@dataclass
class Image:
    chemin: Path
    taille: int
    modifie: float


def lister_images(dossier):
    """Images du dossier (sous-dossiers ignorés), la plus récente d'abord ; [] si le dossier est vide, absent ou illisible."""
    if not dossier:
        return []
    images = []
    try:
        for p in Path(dossier).iterdir():
            if p.suffix.lower() in EXTENSIONS and p.is_file():
                st = p.stat()
                images.append(Image(p, st.st_size, st.st_mtime))
    except OSError:
        return []
    return sorted(images, key=lambda i: i.modifie, reverse=True)


def dossier_cache():
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "giga-pano-hdr" / "apercus"
    return Path.home() / ".giga-pano-hdr" / "apercus"


def chemin_cache(fichier, racine=None):
    """Chemin du JPEG en cache pour ce fichier dans son état actuel (ne crée rien)."""
    fichier = Path(fichier)
    cle = f"{fichier.resolve()}|{fichier.stat().st_mtime_ns}"
    return (racine or dossier_cache()) / (hashlib.sha1(cle.encode("utf-8")).hexdigest() + ".jpg")


def apercu(fichier, vips, largeur=LARGEUR, lancer=subprocess.run, racine=None):
    """JPEG réduit à `largeur` pixels ; lève RuntimeError si vips échoue."""
    cache = chemin_cache(fichier, racine)
    if cache.exists():
        return cache
    cache.parent.mkdir(parents=True, exist_ok=True)
    r = lancer([vips, "thumbnail", str(fichier), f"{cache}[Q=85]", str(largeur)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip() or f"vips thumbnail a échoué (code {r.returncode})")
    return cache


def vider_cache(racine=None):
    """Supprime les aperçus en cache ; retourne leur nombre."""
    dossier = racine or dossier_cache()
    if not dossier.is_dir():
        return 0
    n = 0
    for p in dossier.glob("*.jpg"):
        p.unlink()
        n += 1
    return n
