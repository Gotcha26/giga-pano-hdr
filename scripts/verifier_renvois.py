"""Vérifie la numérotation du guide : identifiants d'étapes, liens internes, restes de l'ancien système.

CONTEXTE
    Utilitaire de rédaction. Le guide numérote ses gestes par phase (0 à 7) et par étape (lettre majuscule qui
    repart à A dans chaque phase) : 3E, 3C.2. Chaque identifiant est un titre du guide ; le texte, l'index des
    scripts, le journal des tests et les docstrings le citent. Ce script empêche le retour du désordre : un renvoi
    vers un identifiant qui n'existe pas, un lien vers une ancre disparue, une trace de l'ancienne numérotation
    (étape 6b, 0b bis, section 5, dossiers 10_grille…).

MODE OPÉRATOIRE
    Lit les identifiants déclarés (titres « ### 3E — … » du guide), puis parcourt le guide (docs/GUIDE.md),
    scripts/INDEX.md, les documents des études de cas (etudes-de-cas/*/*.md) et les scripts .py / .ps1. Dans le Markdown, une citation est tout identifiant isolé
    (3E ou **3E**) hors titres, code en ligne et cibles de liens, y compris dans les schémas (bloc sans langue,
    mermaid) ; dans un autre bloc de code, seul un commentaire « # 3E.2. » compte. FAUX_AMIS (EOS-1D, 4K) n'est
    pris pour une citation qu'en gras. Dans un script : « Étape 3E » ou « Étapes 3C à 3E ».
    Les ancres sont calculées comme sur GitHub. Dans les études de cas, les anciens noms de dossiers sont admis
    (historique des mesures).

ENTRÉES
    --racine DOSSIER   racine du dépôt (défaut : parent du dossier de ce script)
    --releve           affiche tous les écarts et sort à 0 (inventaire)

SORTIES
    Console : une ligne « fichier:ligne: nature: extrait » par écart (natures : non-declare, ancien-systeme,
    lien-casse), puis « N écart(s) ». Code de sortie 1 s'il y a un écart (sauf --releve).

EXEMPLE
    python verifier_renvois.py --releve
    python verifier_renvois.py
"""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

Ecart = tuple[str, int, str, str]

ID = r"[0-7][A-Z](?:\.\d+)?"
GUIDE = Path("docs") / "GUIDE.md"
ETUDES = Path("etudes-de-cas")

RE_TITRE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
RE_DECLARE = re.compile(rf"^#{{2,4}} ({ID}) — ")
RE_CITE_NU = re.compile(rf"(?<![\w.]){ID}(?![\w])")  # un identifiant isolé, en gras ou non
FAUX_AMIS = {"1D", "4K"}  # « Canon EOS-1D X », « écran 4K » : ignorés hors gras
RE_CITE_CODE = re.compile(rf"^\s*#\s+({ID})\.")
RE_CITE_SCRIPT = re.compile(rf"[ÉéEe]tapes?\s+({ID}(?:\s*(?:,|à|a|et)\s*{ID})*)")
RE_ID = re.compile(ID)

RE_ETAPE_CHIFFRE = re.compile(r"(?i:[ée]tapes?)\s+(?:n°\s*)?\d+(?![A-Z\d])")
RE_PLAGE_CHIFFRE = re.compile(rf"(?i:[ée]tapes?)\s+{ID}\s+(?:à|et)\s+\d+(?![A-Z\d])")
RE_BIS = re.compile(r"\b\d+\s?(?:bis|ter)\b")
RE_GRAS_SUFFIXE = re.compile(r"\*\*\d+[a-d]\.")
RE_COMMENTAIRE_NUMERO = re.compile(r"^\s*#\s+\d+[a-d]?\.?\s?(?:bis)?\b")
RE_SECTION = re.compile(r"\bsections?\s+\d")
RE_SUFFIXE_NU = re.compile(r"\b\d{1,2}[a-d]\b")
RE_ETIQUETTE_NUMERO = re.compile(r"[\[\"]\d+[a-d]?(?:-\d+[a-d]?)?\.")  # nœud de diagramme « [2. … » ou « [0a-0b. … »
RE_DOSSIER = re.compile(r"\b[1-7]0_[a-z]")

RE_CODE_EN_LIGNE = re.compile(r"`[^`]*`")
RE_CIBLE_LIEN = re.compile(r"\]\([^)\s]*\)")
RE_LIEN_LOCAL =re.compile(r"\]\(#([^)\s]+)\)")
RE_LIEN_GUIDE = re.compile(r"\]\([^)\s]*GUIDE\.md#([^)\s]+)\)")


CLOTURE = "```"
SCHEMAS = ("", "mermaid")  # blocs lus comme du texte : arborescences et diagrammes


def _blocs(texte: str):
    """(numéro, ligne, bloc) : bloc vaut None hors code, la langue du bloc de code (« » sans langue), ou CLOTURE."""
    bloc = None
    for n, ligne in enumerate(texte.splitlines(), 1):
        if ligne.lstrip().startswith(CLOTURE):
            bloc = ligne.strip()[3:].strip().lower() if bloc is None else None
            yield n, ligne, CLOTURE
            continue
        yield n, ligne, bloc


def _lignes(texte: str):
    """(numéro, ligne, dans_code) pour chaque ligne ; les clôtures ``` elles-mêmes sont marquées dans_code."""
    for n, ligne, bloc in _blocs(texte):
        yield n, ligne, bloc is not None


def _texte_seul(ligne: str) -> str:
    """La ligne sans code en ligne ni cible de lien."""
    return RE_CIBLE_LIEN.sub("]()", RE_CODE_EN_LIGNE.sub("``", ligne))


def ancre(titre: str) -> str:
    s = titre.lower().replace("*", "").replace("`", "")
    s = re.sub(r"[^\w\- ️]", "", s)  # GitHub garde le sélecteur de variante des emoji (U+FE0F)
    return s.replace(" ", "-")


def ancres(texte: str) -> set[str]:
    vues: dict[str, int] = {}
    resultat = set()
    for _, ligne, dans_code in _lignes(texte):
        m = None if dans_code else RE_TITRE.match(ligne)
        if not m:
            continue
        base = ancre(m.group(2))
        if base in vues:
            vues[base] += 1
            resultat.add(f"{base}-{vues[base]}")
        else:
            vues[base] = 0
            resultat.add(base)
    return resultat


def declares(texte: str) -> set[str]:
    return {m.group(1) for _, ligne, dans_code in _lignes(texte) if not dans_code
            for m in [RE_DECLARE.match(ligne)] if m}


def cites(texte: str, est_script: bool) -> list[tuple[int, str]]:
    resultat = []
    if est_script:
        for n, ligne in enumerate(texte.splitlines(), 1):
            for m in RE_CITE_SCRIPT.finditer(ligne):
                resultat += [(n, i) for i in RE_ID.findall(m.group(1))]
        return resultat
    for n, ligne, bloc in _blocs(texte):
        if bloc == CLOTURE:
            continue
        if bloc is None and RE_TITRE.match(ligne):
            continue
        if bloc is None or bloc in SCHEMAS:
            seul = _texte_seul(ligne)
            resultat += [(n, m.group(0)) for m in RE_CITE_NU.finditer(seul)
                         if m.group(0) not in FAUX_AMIS or seul[max(0, m.start() - 2):m.start()] == "**"]
        else:
            m = RE_CITE_CODE.match(ligne)
            if m:
                resultat.append((n, m.group(1)))
    return resultat


def restes(texte: str, exempter_dossiers: bool, est_script: bool = False) -> list[tuple[int, str]]:
    resultat = []
    for n, ligne, bloc in _blocs(texte):
        motifs = [RE_ETAPE_CHIFFRE, RE_PLAGE_CHIFFRE]
        if not exempter_dossiers:
            motifs.append(RE_DOSSIER)
        if not est_script:
            motifs += [RE_BIS, RE_GRAS_SUFFIXE, RE_SECTION]
            if bloc is None or bloc in SCHEMAS:
                motifs += [RE_SUFFIXE_NU, RE_ETIQUETTE_NUMERO] if bloc else [RE_SUFFIXE_NU]
            elif bloc != CLOTURE:
                motifs.append(RE_COMMENTAIRE_NUMERO)
        if any(m.search(_texte_seul(ligne)) for m in motifs):
            resultat.append((n, ligne.strip()))
    return resultat


def liens(texte: str) -> list[tuple[int, str]]:
    """Liens internes ; l'ancre d'un lien vers le guide depuis un autre fichier est préfixée « GUIDE# »."""
    resultat = []
    for n, ligne, dans_code in _lignes(texte):
        if dans_code:
            continue
        resultat += [(n, unquote(a)) for a in RE_LIEN_LOCAL.findall(ligne)]
        resultat += [(n, "GUIDE#" + unquote(a)) for a in RE_LIEN_GUIDE.findall(ligne)]
    return resultat


def verifier(racine: Path) -> list[Ecart]:
    guide = (racine / GUIDE).read_text(encoding="utf-8")
    ids = declares(guide)
    ancres_guide = ancres(guide)
    fichiers = [racine / GUIDE, racine / "scripts" / "INDEX.md"]
    fichiers += sorted((racine / ETUDES).glob("*/*.md")) if (racine / ETUDES).exists() else []
    fichiers += sorted(p for p in (racine / "scripts").glob("*.py") if p.name != Path(__file__).name)
    fichiers += sorted((racine / "scripts").glob("*.ps1"))
    ecarts: list[Ecart] = []
    for chemin in fichiers:
        if not chemin.exists():
            continue
        texte = chemin.read_text(encoding="utf-8")
        nom = chemin.relative_to(racine).as_posix()
        est_script = chemin.suffix in (".py", ".ps1")
        journal = ETUDES in chemin.relative_to(racine).parents  # étude de cas : anciens noms de dossiers admis
        ecarts += [(nom, n, "non-declare", i) for n, i in cites(texte, est_script) if i not in ids]
        ecarts += [(nom, n, "ancien-systeme", e) for n, e in restes(texte, journal, est_script)]
        if not est_script:
            locales = ancres(texte)
            for n, a in liens(texte):
                cible, connues = (a[6:], ancres_guide) if a.startswith("GUIDE#") else (a, locales)
                if cible not in connues:
                    ecarts.append((nom, n, "lien-casse", "#" + cible))
    return sorted(ecarts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vérifie la numérotation du guide d'assemblage.")
    parser.add_argument("--racine", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--releve", action="store_true", help="inventaire : affiche tout, sort à 0")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ecarts = verifier(args.racine)
    for fichier, ligne, nature, extrait in ecarts:
        print(f"{fichier}:{ligne}: {nature}: {extrait}")
    print(f"{len(ecarts)} écart(s)")
    return 0 if args.releve or not ecarts else 1


if __name__ == "__main__":
    sys.exit(main())
