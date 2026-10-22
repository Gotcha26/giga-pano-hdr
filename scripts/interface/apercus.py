"""Aperçus des images produites : liste d'un dossier et JPEG réduit par libvips, mis en cache hors du panorama.

Logique pure, sans NiceGUI. Le cache vit dans %LOCALAPPDATA%\\giga-pano-hdr\\apercus (repli ~/.giga-pano-hdr/apercus),
jamais sous $T ; son nom dépend du chemin et de la date de modification, donc un fichier retouché est re-réduit.
"""

import hashlib
import os
import subprocess
import threading
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
    """Images du dossier (sous-dossiers ignorés), la plus récente d'abord ; [] si le dossier est vide, absent ou
    illisible. Un fichier illisible à lui seul (supprimé entre-temps, verrouillé) est ignoré sans annuler la liste."""
    if not dossier:
        return []
    images = []
    try:
        entrees = list(Path(dossier).iterdir())
    except OSError:
        return []
    for p in entrees:
        if p.suffix.lower() not in EXTENSIONS:
            continue
        try:
            if not p.is_file():
                continue
            st = p.stat()
        except OSError:
            continue
        images.append(Image(p, st.st_size, st.st_mtime))
    return sorted(images, key=lambda i: i.modifie, reverse=True)


def dossier_cache():
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "giga-pano-hdr" / "apercus"
    return Path.home() / ".giga-pano-hdr" / "apercus"


def chemin_cache(fichier, racine=None):
    """Chemin du JPEG en cache pour ce fichier dans son état actuel (ne crée rien).

    Le fichier doit exister : sa date de modification entre dans le nom (OSError sinon)."""
    fichier = Path(fichier)
    cle = f"{fichier.resolve()}|{fichier.stat().st_mtime_ns}"
    return (racine or dossier_cache()) / (hashlib.sha1(cle.encode("utf-8")).hexdigest() + ".jpg")


# Un verrou par chemin de cache : deux clics rapides (ou deux onglets) sur la même image n'invoquent vips qu'une
# fois, le second attend puis relit le cache ; des images différentes se réduisent en parallèle. Le dictionnaire
# n'est jamais purgé (quelques octets par image ouverte pendant la session).
_VERROUS = {}
_VERROU_DES_VERROUS = threading.Lock()


def _verrou(cache):
    with _VERROU_DES_VERROUS:
        return _VERROUS.setdefault(str(cache), threading.Lock())


def apercu(fichier, vips, largeur=LARGEUR, lancer=subprocess.run, racine=None, delai=120):
    """JPEG réduit à `largeur` pixels ; lève RuntimeError si vips échoue ou dépasse `delai` secondes.

    vips écrit dans `<cache>.part.jpg`, renommé en `<cache>.jpg` seulement après un succès : un échec ou une
    interruption ne laisse jamais un JPEG tronqué que le cache resservirait."""
    cache = chemin_cache(fichier, racine)
    with _verrou(cache):
        if cache.exists():
            return cache
        cache.parent.mkdir(parents=True, exist_ok=True)
        partiel = cache.with_suffix(".part.jpg")
        try:
            try:
                r = lancer([vips, "thumbnail", str(fichier), f"{partiel}[Q=85]", str(largeur)],
                           capture_output=True, text=True, timeout=delai)
            except subprocess.TimeoutExpired:
                raise RuntimeError(f"vips thumbnail n'a pas répondu en {delai} s : aperçu abandonné.") from None
            if r.returncode != 0:
                raise RuntimeError((r.stderr or "").strip() or f"vips thumbnail a échoué (code {r.returncode})")
            os.replace(partiel, cache)
        except BaseException:
            partiel.unlink(missing_ok=True)
            raise
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
