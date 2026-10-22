"""Sources d'aide de l'interface : section du guide d'un repère, lien GitHub et mode d'emploi d'un script.

Logique pure, sans NiceGUI. L'aide est lue à l'exécution dans docs/GUIDE.md et dans les en-têtes des scripts ;
rien n'est recopié dans le code.
"""

import re
from pathlib import Path

import verifier_renvois
from pilotage import arguments, lancer

GUIDE = Path(__file__).resolve().parent.parent.parent / "docs" / "GUIDE.md"
URL_GUIDE = "https://github.com/Gotcha26/giga-pano-hdr/blob/main/docs/GUIDE.md"

RE_TITRE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")


def _titres(guide):
    """(lignes du guide, [(index de ligne, niveau, texte du titre)]) des titres hors blocs de code, ou None si le
    guide est illisible. Les blocs de code (``` ou ~~~) suivent les règles de verifier_renvois._lignes."""
    try:
        texte = Path(guide).read_text(encoding="utf-8")
    except OSError:
        return None
    titres = []
    for n, ligne, dans_code in verifier_renvois._lignes(texte):
        m = None if dans_code else RE_TITRE.match(ligne)
        if m:
            titres.append((n - 1, len(m.group(1)), m.group(2)))
    return texte.splitlines(), titres


def _correspond(texte, repere):
    nu = texte.replace("*", "").strip()
    return nu.startswith(repere + " ") or nu.startswith(repere + " —")


def _trouver(repere, guide):
    """(lignes, titres, position du titre du repère dans titres) ou None."""
    lus = _titres(guide)
    if lus is None:
        return None
    lignes, titres = lus
    for k, (_, niveau, texte) in enumerate(titres):
        if niveau in (3, 4) and _correspond(texte, repere):
            return lignes, titres, k
    return None


def section_du_guide(repere, guide=GUIDE):
    """Markdown du titre ### ou #### du repère, titre compris, jusqu'au prochain titre de niveau égal ou supérieur."""
    trouve = _trouver(repere, guide)
    if trouve is None:
        return None
    lignes, titres, k = trouve
    debut, niveau, _ = titres[k]
    fin = next((i for i, n, _ in titres[k + 1:] if n <= niveau), len(lignes))
    return "\n".join(lignes[debut:fin]).rstrip() + "\n"


def lien_guide(repere, guide=GUIDE):
    """Lien GitHub vers le titre du repère dans le guide, ou vers le guide entier si le repère est introuvable."""
    trouve = _trouver(repere, guide)
    if trouve is None:
        return URL_GUIDE
    _, titres, k = trouve
    return URL_GUIDE + "#" + verifier_renvois.ancre(titres[k][2])


def mode_d_emploi(script):
    """Docstring d'un script Python ou bloc de commentaires d'en-tête d'un script PowerShell ; vide sinon."""
    script = Path(script)
    if script.suffix == ".py":
        return arguments.lire_declaration(script)[2]
    if script.suffix == ".ps1":
        return lancer.commentaire_ps(script)
    return ""
