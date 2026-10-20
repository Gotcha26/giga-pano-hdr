# Nettoyage de l'ancien dépôt : 2026-10-18 et 2026-10-20

Le dossier `assemblage-panorama/` du dépôt privé de la visionneuse (`Gotcha26/piwigo-GigaPanoramaViewer_private`, dossier local `…\Piwigo\GigaPanoramaViewer\`) a été **recopié** dans ce dépôt le 2026-10-18, puis **retiré** de l'ancien le même jour par la PR [#58](https://github.com/Gotcha26/piwigo-GigaPanoramaViewer_private/pull/58). Ce document garde la trace de ce qui a été déplacé, de ce qui est resté, et de ce que la PR a changé là-bas.

**Règle** : ce dépôt est la seule source de la méthode (guide, étude de cas, scripts). L'issue **#46** de la visionneuse garde l'historique de l'enquête sur les colonnes du ciel ; sa clôture revient à l'auteur, après validation du rendu en ligne. Les suites (mesures de jonction sur `Export-TIFF-H2`, export moins saturé) se consignent dans l'étude de cas, section « État du chantier ».

---

## ✅ Ce qui a été déplacé

| Dans l'ancien dépôt | Dans ce dépôt | Remarque |
| --- | --- | --- |
| `assemblage-panorama/docs/GUIDE_panorama_hugin.md` (v6.0, 1915 lignes) | `docs/GUIDE.md` (guide général) **+** `etudes-de-cas/2026-06-19-wattenberg-200mm/ETUDE-DE-CAS.md` | **Scindé** : la méthode d'un côté, les chiffres et incidents du panorama de l'autre.<br>Même numérotation d'étapes |
| `assemblage-panorama/docs/TESTS-ANALYSES.md` (v1.1, puis M-17 de la PR #57) | `etudes-de-cas/2026-06-19-wattenberg-200mm/TESTS-ANALYSES.md` | <ul><li>Copie</li><li>Liens vers le guide réécrits</li><li>Une phrase d'introduction adaptée</li><li>M-17 transposée (commit `113b3ed`)</li></ul> |
| `assemblage-panorama/scripts/*.py`, `*.ps1`, `*.cmd` (42 fichiers) | `scripts/` | Copie, puis menus de pilotage et lanceur ajoutés (PR [#1](https://github.com/Gotcha26/giga-pano-hdr/pull/1)) |
| `page-autonome/tuiler.ps1` | `scripts/tuiler.ps1` | Copié aussi : il appartient à la chaîne d'assemblage (**7A**), pas au banc d'essai |
| `assemblage-panorama/scripts/INDEX.md` | `scripts/INDEX.md` | <ul><li>Réécrit : colonne « portée »</li><li>***tuiler.ps1*** ajouté</li><li>Liens vers le nouveau guide</li></ul> |
| `assemblage-panorama/tests/*.py` | `tests/` | Copie<br>chemins de lancement et fixtures adaptés (`GUIDE.md`) |
| `assemblage-panorama/donnees/table_raw_LCE.csv` | `etudes-de-cas/…/donnees/` | Copie |
| `assemblage-panorama/lightroom/presets/*` | `etudes-de-cas/…/lightroom/presets/` | Copie |

**Pas copié** (reste dans le dépôt de la visionneuse, car propre à elle) : `page-autonome/index.html`, `vendor/` (OpenSeadragon), `empaqueter.ps1`, `hebergement/`, `tests/tester_empaqueter.ps1`, `page-autonome/README.md`. Le guide général parle désormais d'« une visionneuse Deep Zoom locale » en **7B** ; l'étude de cas nomme le banc d'essai.

**Adaptations faites aux scripts à la copie** : ***verifier_renvois.py*** lit `docs/GUIDE.md` et parcourt `etudes-de-cas/*/*.md` au lieu de `docs/TESTS-ANALYSES.md` ; les deux tests citent `tests/` au lieu de `assemblage-panorama/tests/`.

---

## 🛠️ Ce que la PR #58 a changé dans l'ancien dépôt

1. **Supprimé** : `assemblage-panorama/` (52 fichiers) et `page-autonome/tuiler.ps1`.
2. `README.md` et `LISEZMOI.md` : la mention « n'assemble pas… `assemblage-panorama/` » renvoie vers ce dépôt ; ligne retirée de l'arborescence, renvoi ajouté dessous ; schéma Mermaid mis à jour.
3. `CLAUDE.md` : « Dépôt mixte » ne cite plus que `page-autonome/` et pointe vers ce dépôt.
4. `.deployignore` : ligne `assemblage-panorama/` retirée ; `tests/test_bootstrap.php` ajusté (tout PASS).
5. `.gitignore`, `page-autonome/README.md`, `page-autonome/index.html` : `tuiler.ps1` désigné dans ce dépôt.
6. Archives `.superpowers/` de la visionneuse : intactes, gitignorées et historiques.
7. Commentaire posé sur #46 avec le lien vers ce dépôt et son étude de cas.

---

## 🧹 Second nettoyage : `page-autonome/` (2026-10-20)

Laissé dans la visionneuse le 18 octobre, `page-autonome/` servait en réalité la chaîne de ce dépôt (contrôler les tuiles, empaqueter), pas le plugin. Ses usages ont maintenant un équivalent ici, et le dossier est retiré de la visionneuse.

| Dans la visionneuse | Ici | Remarque |
| --- | --- | --- |
| `page-autonome/index.html` + `vendor/openseadragon/` | `scripts/visionneuse/` (page + *OpenSeadragon* 6.1.1), servis par ***controler_tuiles.py*** (**7B**) | Plus de copie ni de jonction : le script sert les dossiers des deux `.dzi` où qu'ils soient |
| `page-autonome/empaqueter.ps1` | ***empaqueter.py*** (**7D**) | Même format (`panorama.json` version 1, ZIP sans compression), mêmes refus |
| `page-autonome/tests/tester_empaqueter.ps1` | `tests/test_empaqueter.py` | Mêmes cas, plus le contenu du ZIP |
| `page-autonome/README.md` (mise en route, empaquetage) | Guide, **7B** et **7D** | |
| `page-autonome/hebergement/` (`.htaccess`, `gigapanorama-ping.txt`) | **Pas ici** : propre à l'hébergement du plugin | Leur contenu est dans la documentation utilisateur de la visionneuse (page 03) |

**Donnée vérifiée avant le retrait** : le cadre d'un HDR non recadré (`0,016135 / 0,012329 / 0,983864`), cité en commentaire de `index.html`, figure dans **T-04** et dans l'étude de cas (**7B**).

---

## 🧭 Décisions prises ici

- **Licence** : MIT pour les scripts, CC BY 4.0 pour la documentation (`LICENSE`, `LICENSE-docs`).
- **Lanceur unique** : livré (PR [#1](https://github.com/Gotcha26/giga-pano-hdr/pull/1)) ; les scripts gardent leur ligne de commande, le lanceur et les menus de pilotage ne font qu'orienter et préremplir.

---

**Version** : 2.1
**Dernière mise à jour** : 2026-10-20
