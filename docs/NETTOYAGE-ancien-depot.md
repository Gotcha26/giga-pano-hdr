# Nettoyage de l'ancien dépôt : à faire après la clôture de l'issue #46

Le dossier `assemblage-panorama/` du dépôt privé de la visionneuse (`Gotcha26/piwigo-GigaPanoramaViewer_private`, dossier local `…\Piwigo\GigaPanoramaViewer\`) a été **recopié, pas déplacé**, dans ce dépôt le 2026-10-18. L'ancien dépôt reste la référence tant que son issue **#46** (colonnes dans le ciel du rendu pleine résolution) est ouverte : les commentaires, PR et chemins qu'elle cite pointent encore là-bas.

---

## 🎯 Pourquoi attendre

- L'issue #46 cite des chemins (`assemblage-panorama/scripts/…`, `assemblage-panorama/docs/GUIDE_panorama_hugin.md`) et des étapes du guide : tant qu'elle vit, ces renvois doivent rester valables.
- Le rendu final n'est pas encore jugé en ligne par l'auteur ; un nouvel export et un nouveau rendu sont prévus. Toute mesure nouvelle entre d'abord dans le carnet **de ce dépôt** (`etudes-de-cas/…/TESTS-ANALYSES.md`), et l'ancien carnet ne bouge plus.

**Règle pendant la transition** : ce dépôt est la source de vérité pour le guide, l'étude de cas et les scripts. L'ancien dossier est gelé ; on n'y corrige plus rien, on y renvoie seulement.

---

## ✅ Ce qui a été copié (état au 2026-10-18)

| Dans l'ancien dépôt | Dans ce dépôt | Remarque |
| --- | --- | --- |
| `assemblage-panorama/docs/GUIDE_panorama_hugin.md` (v6.0, 1915 lignes) | `docs/GUIDE.md` (guide général) **+** `etudes-de-cas/2026-06-19-wattenberg-200mm/ETUDE-DE-CAS.md` | **Scindé** : la méthode d'un côté, les chiffres et incidents du panorama de l'autre. Même numérotation d'étapes |
| `assemblage-panorama/docs/TESTS-ANALYSES.md` (v1.1) | `etudes-de-cas/2026-06-19-wattenberg-200mm/TESTS-ANALYSES.md` | Copie ; liens vers le guide réécrits ; une phrase d'introduction adaptée |
| `assemblage-panorama/scripts/*.py`, `*.ps1`, `*.cmd` (42 fichiers) | `scripts/` | Copie à l'identique |
| `page-autonome/tuiler.ps1` | `scripts/tuiler.ps1` | Copié aussi : il appartient à la chaîne d'assemblage (**7A**), pas au banc d'essai |
| `assemblage-panorama/scripts/INDEX.md` | `scripts/INDEX.md` | Réécrit : colonne « portée », ***tuiler.ps1*** ajouté, liens vers le nouveau guide |
| `assemblage-panorama/tests/*.py` | `tests/` | Copie ; chemins de lancement et fixtures adaptés (`GUIDE.md`) |
| `assemblage-panorama/donnees/table_raw_LCE.csv` | `etudes-de-cas/…/donnees/` | Copie |
| `assemblage-panorama/lightroom/presets/*` | `etudes-de-cas/…/lightroom/presets/` | Copie |

**Pas copié** (reste dans le dépôt de la visionneuse, car propre à elle) : `page-autonome/index.html`, `vendor/` (OpenSeadragon), `empaqueter.ps1`, `hebergement/`, `tests/tester_empaqueter.ps1`, `page-autonome/README.md`. Le guide général parle désormais d'« une visionneuse Deep Zoom locale » en **7B** ; l'étude de cas nomme le banc d'essai.

**Adaptations faites aux scripts** : ***verifier_renvois.py*** lit `docs/GUIDE.md` et parcourt `etudes-de-cas/*/*.md` au lieu de `docs/TESTS-ANALYSES.md` ; les deux tests citent `tests/` au lieu de `assemblage-panorama/tests/`. Aucun autre script n'a été modifié.

---

## 🛠️ À faire dans l'ancien dépôt, une fois #46 close

1. **Dernière synchronisation** : relire les commentaires de #46 postérieurs au 2026-10-18 et reporter dans `etudes-de-cas/…/TESTS-ANALYSES.md` et `ETUDE-DE-CAS.md` (section « État du chantier ») ce qui manque : seuil de tolérance en pleine résolution (M-16), verdict en ligne, dernier export.
2. **Supprimer** `assemblage-panorama/` (docs, scripts, tests, donnees, lightroom) et `page-autonome/tuiler.ps1`, en une PR dédiée.
3. **Remplacer** par un renvoi : dans `README.md` et `LISEZMOI.md` de la visionneuse (lignes « It does not stitch panoramas… `assemblage-panorama/` » et l'arborescence), pointer vers `https://github.com/Gotcha26/giga-pano-hdr`.
4. **`.deployignore`** : retirer la ligne `assemblage-panorama/` (devenue sans objet) ; garder `page-autonome/`.
5. **`page-autonome/README.md`** : la ligne « Tuiler : `.\tuiler.ps1 …` » devient un renvoi vers `scripts/tuiler.ps1` de ce dépôt (ou garder une copie si le banc d'essai doit rester autonome : à décider).
6. **Archives `.superpowers/`** de la visionneuse (handoffs, plans) : rien à faire, elles sont gitignorées et historiques.
7. **Fermer la boucle** : un commentaire final sur #46 avec le lien vers l'étude de cas de ce dépôt.

---

## 🧭 Ce qu'il reste à décider ici (pas dans l'ancien dépôt)

- **Licence** : choisie le 2026-10-18, MIT pour les scripts, CC BY 4.0 pour la documentation (`LICENSE`, `LICENSE-docs`).
- **Lanceur unique** : prévu après la stabilisation ; les scripts gardent leurs interfaces actuelles.

---

**Version** : 1.0
**Dernière mise à jour** : 2026-10-18
