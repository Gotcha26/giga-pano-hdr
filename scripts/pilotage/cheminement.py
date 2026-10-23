"""Cheminement de la prise de vue : coin de départ, serpentin facultatif, toujours en lignes (jamais en colonnes).

Module pur, partagé par le renommage (renommer_pano.py), le menu console et la page web 1B. Deux conventions :
- les cases « vues » sont (rangée vue du haut, colonne vue de la gauche), base 0 ;
- les cases « nommées » suivent la convention des noms L_C_E de la chaîne : ligne 0 = haut, colonne 0 = bord DROIT
  (celle que les scripts de géométrie supposent pour le lacet). Le défaut (départ haut droit, sans serpentin) y
  redonne exactement l'ancien calcul rang -> divmod(rang, colonnes).
"""

COINS = ("hg", "hd", "bg", "bd")
DEFAUT = "hd"
LIGNES_DESSIN, COLONNES_DESSIN = 3, 5      # le dessin est une représentation, indépendante de la grille réelle
NOMS_COINS = {"hg": "haut gauche", "hd": "haut droit", "bg": "bas gauche", "bd": "bas droit"}
FLECHES_COINS = {"hg": "↘", "hd": "↙", "bg": "↗", "bd": "↖"}      # vers le centre : le sens de la prise de vue


def verifier_depart(depart):
    """`depart` s'il est un des quatre coins ; ValueError sinon."""
    if depart not in COINS:
        raise ValueError(f"coin de départ inconnu : {depart!r} (attendu : {', '.join(COINS)})")
    return depart


def ordre_prise(lignes, colonnes, depart, serpentin):
    """Les cases dans l'ordre de prise, en (rangée vue du haut, colonne vue de la gauche).

    Rangées parcourues depuis le haut (départ h*) ou le bas (b*) ; la première va vers la droite si le départ est à
    gauche, vers la gauche sinon ; avec `serpentin`, une rangée sur deux est inversée."""
    verifier_depart(depart)
    bas, droite = depart[0] == "b", depart[1] == "d"
    cases = []
    for k in range(lignes):
        rangee = lignes - 1 - k if bas else k
        vers_droite = (not droite) != (serpentin and k % 2 == 1)
        colonnes_vues = range(colonnes) if vers_droite else range(colonnes - 1, -1, -1)
        cases += [(rangee, c) for c in colonnes_vues]
    return cases


def cases_nommees(lignes, colonnes, depart, serpentin):
    """Comme ordre_prise, mais en (ligne, colonne) de la convention des noms (colonne 0 = bord droit)."""
    return [(r, colonnes - 1 - c) for r, c in ordre_prise(lignes, colonnes, depart, serpentin)]


def _sens_premiere_ligne(depart):
    return "de gauche à droite" if depart[1] == "g" else "de droite à gauche"


def resume(depart, serpentin):
    """Une phrase qui décrit le cheminement."""
    verifier_depart(depart)
    mouvement = "en remontant" if depart[0] == "b" else "en descendant"
    sens = _sens_premiere_ligne(depart)
    fin = (f"serpentin : 1re ligne {sens}, puis sens inversé à chaque ligne." if serpentin
           else f"toutes les lignes {sens}.")
    return f"Départ {NOMS_COINS[depart]}, {mouvement} ; {fin}"


def _numeros(depart, serpentin):
    """{(rangée, colonne vues): numéro de prise à partir de 1} pour le dessin 3 x 5."""
    ordre = ordre_prise(LIGNES_DESSIN, COLONNES_DESSIN, depart, serpentin)
    return {case: i + 1 for i, case in enumerate(ordre)}, ordre


def dessin_texte(depart, serpentin):
    """Le dessin 3 x 5 en texte (5 lignes) : numéros de prise reliés par → ou ←, et une ligne de liaison entre deux
    rangées (↓ ou ↑ sur la case d'arrivée ; ┄ sur le chemin de retour quand il n'y a pas de serpentin)."""
    numeros, ordre = _numeros(depart, serpentin)
    bas = depart[0] == "b"
    texte, positions, debuts, fins = [], [], {}, {}
    for r in range(LIGNES_DESSIN):
        cases = [c for rr, c in ordre if rr == r]         # colonnes de la rangée, dans l'ordre de prise
        debuts[r], fins[r] = cases[0], cases[-1]
        vers_droite = cases[0] < cases[-1]
        ligne, pos = "  ", {}
        for c in range(COLONNES_DESSIN):
            pos[c] = len(ligne)
            ligne += str(numeros[(r, c)])
            if c < COLONNES_DESSIN - 1:
                ligne += " → " if vers_droite else " ← "
        texte.append(ligne)
        positions.append(pos)
    resultat = [texte[0]]
    for r in range(LIGNES_DESSIN - 1):
        haut, bas_r = r, r + 1
        depart_liaison, arrivee, fleche = ((fins[bas_r], debuts[haut], "↑") if bas
                                           else (fins[haut], debuts[bas_r], "↓"))
        a = positions[bas_r if bas else haut][depart_liaison]
        b = positions[haut if bas else bas_r][arrivee]
        liaison = [" "] * (max(a, b) + 1)
        for i in range(min(a, b), max(a, b)):
            liaison[i] = "┄"
        liaison[b] = fleche
        resultat += ["".join(liaison), texte[r + 1]]
    return resultat


def dessin_svg(depart, serpentin):
    """Fragment <svg> du cheminement 3 x 5 : cases numérotées, flèches, case de départ pleine ; sans serpentin, le
    retour au début de la ligne suivante est tracé en pointillé. Couleurs : variables CSS --cm-* avec repli."""
    numeros, ordre = _numeros(depart, serpentin)
    cw = ch = 64
    ox = oy = 10
    larg, haut = ox * 2 + COLONNES_DESSIN * cw, oy * 2 + LIGNES_DESSIN * ch

    def centre(case):
        return ox + case[1] * cw + cw / 2, oy + case[0] * ch + ch / 2

    s = [f'<svg viewBox="0 0 {larg} {haut}" xmlns="http://www.w3.org/2000/svg">',
         '<defs><marker id="cm-fl" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" refX="8" refY="5" '
         'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--cm-acc,#1976d2)"/></marker></defs>']
    for i, case in enumerate(ordre):
        x, y = centre(case)
        depart_case = i == 0
        remplissage = "var(--cm-acc,#1976d2)" if depart_case else "var(--cm-case,#e3f0fc)"
        texte = "#ffffff" if depart_case else "var(--cm-txt,#1f2430)"
        s.append(f'<rect x="{x - cw / 2 + 3}" y="{y - ch / 2 + 3}" width="{cw - 6}" height="{ch - 6}" rx="6" '
                 f'fill="{remplissage}" stroke="var(--cm-trait,#d5d9e0)"/>')
        s.append(f'<text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="central" font-size="14" '
                 f'font-weight="600" fill="{texte}">{numeros[case]}</text>')
    for a, b in zip(ordre, ordre[1:]):
        (xa, ya), (xb, yb) = centre(a), centre(b)
        if a[0] != b[0] and a[1] != b[1]:               # retour au début de la ligne suivante (sans serpentin)
            sens = 1 if yb > ya else -1
            s.append(f'<path d="M{xa},{ya + sens * 14} C{xa},{ya + sens * 40} {xb},{yb - sens * 40} {xb},{yb - sens * 14}" '
                     'fill="none" stroke="var(--cm-saut,#e07b00)" stroke-width="2.5" stroke-dasharray="6 5"/>')
        else:
            dx = (xb > xa) - (xb < xa)
            dy = (yb > ya) - (yb < ya)
            s.append(f'<path d="M{xa + dx * 16},{ya + dy * 16} L{xb - dx * 20},{yb - dy * 20}" fill="none" '
                     'stroke="var(--cm-acc,#1976d2)" stroke-width="3" marker-end="url(#cm-fl)"/>')
    s.append("</svg>")
    return "".join(s)
