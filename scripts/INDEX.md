# Index des scripts d'assemblage

Les 43 scripts de ce dossier forment la chaîne qui mène des images exportées de *Lightroom* à un giga-panorama tuilé : renommage, géométrie dans *Hugin*, rendu, mesures de qualité, cadrage, tuilage. Chacun porte, **en tête de fichier**, son propre mode d'emploi.

---

## 📋 Pour qui ?

Pour qui veut savoir « quel script pour quoi ? » sans ouvrir les 43 fichiers : cet index les classe par phase, dans l'ordre où on s'en sert, avec l'identifiant de l'étape du [guide](../docs/GUIDE.md) qui les emploie (**3F**, **6C**…) et leur **portée**. Le détail des gestes dans *Hugin* et *Lightroom* est dans le guide (voir son aide-mémoire pour la séquence complète).

---

## 🎯 Portée : trois familles

| Portée | Sens | Ce qu'il faut adapter pour un autre panorama |
| :---: | --- | --- |
| 🟢 **Générique** | Ne suppose rien de la grille ni de l'objectif ; lit ce dont il a besoin dans les fichiers, le projet ou les arguments | Rien, ou les chemins d'installation des outils (en tête des `.ps1`, ou en paramètre) |
| 🟡 **Paramétré par la grille** | Contient en tête des **constantes** (colonnes, lignes, focale, pas, champ) écrites pour une prise de vue donnée | Les constantes en tête du script (voir les [conventions](#️-conventions-communes)) |
| 🔵 **Rédaction** | Sert à tenir le guide, pas à assembler | Rien |

Les 43 scripts sont des outils de **méthode** : aucun n'est propre à un seul panorama. Ce qui est propre à un panorama (table RAW → `L_C_E`, préréglages Lightroom, mesures) est dans son dossier `etudes-de-cas/`.

---

## 📚 Le mode d'emploi en tête de chaque script

Tous les scripts suivent le même plan. Python : docstring de module (visible avec `help()` ou en ouvrant le fichier). PowerShell : bloc de commentaires avant `param(`.

| Rubrique | Contenu |
| --- | --- |
| **Titre** | Une phrase : ce que fait le script (première ligne) |
| **CONTEXTE** | Où il se place dans la chaîne, et pourquoi il existe |
| **MODE OPÉRATOIRE** | Ce qu'il fait, dans l'ordre |
| **ENTRÉES** | Arguments, options, et constantes à adapter en tête de script |
| **SORTIES** | Ce qui s'affiche, ce qui est écrit (et ce qui ne l'est pas) |
| **EXEMPLE** | Une ligne de commande prête à adapter |
| **Usage** | La syntaxe courte |

> Les scripts PowerShell sont **volontairement sans accents** : ils se lancent aussi bien avec *Windows PowerShell* qu'avec *PowerShell 7*.

---

## ⚙️ Conventions communes

| Convention | Valeur |
| --- | --- |
| Grille | `COLS` colonnes × `ROWS` lignes ; numéro d'image `k = ligne × COLS + colonne` ; image 0 = `L0_C00` (haut, côté où chaque ligne commence) |
| Noms d'images | `L{ligne}_C{colonne}_E{expo}.tif`, produits par ***renommer_pano.py*** ou ***renommer_par_raw.py*** |
| Pas et champ | `PAS_H`, `PAS_V` en degrés ; champ d'une image calculé d'après `FOCALE` et `LARGEUR_MM` |
| Projets | `.pto` de *Hugin* ; les scripts de géométrie lisent et écrivent ce texte, sans passer par *Hugin* |
| Sécurité | Les scripts qui renomment ou déplacent des images travaillent en essai à blanc par défaut (`--apply` pour agir) ; les scripts de projet écrivent le `.pto` de sortie qu'on leur indique (il n'écrase l'entrée que si on donne le même chemin) |

Les valeurs **actuellement en dur** dans les scripts 🟡 sont celles de l'[étude de cas](../etudes-de-cas/2026-06-19-wattenberg-200mm/ETUDE-DE-CAS.md#-paramètres-du-panorama) : 37 colonnes, 6 lignes, 200 mm, pas de 5,0° × 5,8°, champ horizontal 6,87°. Pour une autre prise de vue, les adapter en tête de chaque script concerné.

---

## ✨ Vue d'ensemble

```mermaid
flowchart TD
    A["Export Lightroom"] --> B["2E-2F. Contrôler, renommer<br/>verifier_ordre, controle_*, ecart_paires, renommer_*"]
    B --> C["3A. Projet de grille<br/>generer_pto*"]
    C --> D["3B. Hugin : points de contrôle"]
    D --> E["3C-3D. Mesurer et filtrer<br/>diagnostic_*, filtrer_cp, ..."]
    E --> F["3E. Hugin : optimiser"]
    F --> G["3F-3H. Contrôler et replacer<br/>detecter_*, placer_isoles, ..."]
    G --> H["4A. Assembler la vue centrée<br/>rendre_projet"]
    H --> I["5A-5B. HDR<br/>propager_geometrie, nona_images, ..."]
    H --> J["6B-6C. Pleine résolution<br/>extraire / redimensionner / nona / multiblend"]
    I --> K["7A. Tuiler<br/>tuiler.ps1"]
    J --> K
    K --> L["7C. Cadrer<br/>cadrage_lightroom"]
```

---

## 🚀 Les scripts, phase par phase

### Phase 2 — Contrôler et renommer l'export

Étapes [**2E**](../docs/GUIDE.md#2e--vérifier-lexport) et [**2F**](../docs/GUIDE.md#2f--renommer).

| Script | Portée | Rôle |
| --- | :---: | --- |
| [***verifier_ordre.py***](verifier_ordre.py) | 🟢 | Contrôle d'après l'EXIF que l'export est complet et dans l'ordre de prise (rafales d'expositions, heures, ouverture/ISO/focale) ; grille passée en argument |
| [***controle_reglages_export.py***](controle_reglages_export.py) | 🟢 | Contrôle les réglages Lightroom enregistrés dans chaque TIFF : uniformité (images en minorité), RAW complets, dimensions, profil, curseurs de tonalité à 0 et balance des blancs fixe |
| [***ecart_paires.py***](ecart_paires.py) | 🟡 | Écart de luminosité et de teinte entre images voisines sur la même scène (médiane de tuiles, 16 bits) ; signale les paires hors lot. Juge le **rendu**, que le contrôle des réglages ne voit pas |
| [***renommer_pano.py***](renommer_pano.py) | 🟢 | Renomme les fichiers Lightroom en `L_C_E` d'après leur numéro de fin de nom ; `--lignes --colonnes --expos`, essai à blanc, `--apply`, `--undo` |
| [***renommer_par_raw.py***](renommer_par_raw.py) | 🟢 | Même renommage, mais d'après le RAW d'origine lu dans les métadonnées, avec un export renommé ou une table CSV comme référentiel : indépendant de l'ordre de tri |
| [***tiffinfo.py***](tiffinfo.py) | 🟢 | Taille, orientation et bits d'un TIFF, sans le décoder |

### Phase 3 — Projet de grille

Étape [**3A**](../docs/GUIDE.md#3a--générer-le-projet-de-grille).

| Script | Portée | Rôle |
| --- | :---: | --- |
| [***generer_pto.py***](generer_pto.py) | 🟡 | Projet *Hugin* avec les vues centrées `_E0` posées sur la grille théorique |
| [***generer_pto_hdr.py***](generer_pto_hdr.py) | 🟡 | Idem pour toutes les expositions, en piles |

### Phase 3 — Mesurer, nettoyer, filtrer, préparer l'optimisation

Étapes [**3C**](../docs/GUIDE.md#3c--nettoyer-et-mesurer-le-pas-vertical) à **3E**.

| Script | Portée | Rôle |
| --- | :---: | --- |
| [***diagnostic_cp.py***](diagnostic_cp.py) | 🟡 | Écart angulaire des points de contrôle par type de paire (horizontale, verticale, diagonale) |
| [***diagnostic_pas_v.py***](diagnostic_pas_v.py) | 🟡 | Cherche le pas vertical et horizontal réel qui minimise l'écart des points |
| [***corriger_pas_v.py***](corriger_pas_v.py) | 🟡 | Remet les images à la grille avec un nouveau pas vertical |
| [***filtrer_cp.py***](filtrer_cp.py) | 🟡 | Retire les points de contrôle trop éloignés de leur homologue (seuil en degrés) |
| [***preparer_optimisation.py***](preparer_optimisation.py) | 🟢 | Écrit dans le projet les variables à optimiser, à la place de l'onglet Optimisation |

### Phase 3 — Contrôler, replacer les images du ciel

Étapes **3E**, [**3G**](../docs/GUIDE.md#3g--replacer-les-images--orphelines--ciel) et [**3H**](../docs/GUIDE.md#3h--détecter-les-trous).

| Script | Portée | Rôle |
| --- | :---: | --- |
| [***voir_positions.py***](voir_positions.py) | 🟡 | Correction (lacet, tangage, roulis) d'une plage d'images par rapport à la grille |
| [***lister_pires_cp.py***](lister_pires_cp.py) | 🟡 | Points de contrôle les plus éloignés de leur homologue, et images concernées |
| [***detecter_aberrantes.py***](detecter_aberrantes.py) | 🟡 | Images dont la correction s'écarte de celle de leurs voisines |
| [***detecter_trous.py***](detecter_trous.py) | 🟡 | Paires voisines qui se recouvrent trop peu (risque de bande noire) |
| [***compter_cp_paire.py***](compter_cp_paire.py) | 🟢 | Nombre de points de contrôle entre des paires données |
| [***placer_isoles.py***](placer_isoles.py) | 🟡 | Replace par interpolation les images sans (ou presque sans) point de contrôle |
| [***affiner_images_faibles.py***](affiner_images_faibles.py) | 🟡 | Récupère les points valides des images faibles et les déclare à optimiser |

### Phase 3 — Qualité du ciel : vignettage et raccords

Étape [**3F**](../docs/GUIDE.md#3f--corriger-le-vignettage-tonalité-du-ciel), et contrôle du rendu complet ([**6C.5**](../docs/GUIDE.md#6c5--contrôler-le-rendu-complet)).

| Script | Portée | Rôle |
| --- | :---: | --- |
| [***mesurer_ciel.py***](mesurer_ciel.py) | 🟡 | Luminosité du ciel par image et vignettage, sur les originaux |
| [***mesurer_gain_paires.py***](mesurer_gain_paires.py) | 🟡 | Écart d'exposition entre images voisines, sur la même portion de ciel |
| [***mesurer_bandes_ciel.py***](mesurer_bandes_ciel.py) | 🟢 | Ondulation périodique (« store vénitien ») d'un panorama assemblé |
| [***localiser_sauts_ciel.py***](localiser_sauts_ciel.py) | 🟢 | Position des sauts brutaux de luminosité, et image concernée |
| [***comparer_rendus.py***](comparer_rendus.py) | 🟢 | Avant / après : luminosité et ondulation d'une zone de ciel |
| [***comparer_couleur.py***](comparer_couleur.py) | 🟢 | Ondulation de couleur (R, G, B, chrominance) d'une zone de ciel |
| [***rehausser_ciel.py***](rehausser_ciel.py) | 🟢 | Image qui exagère les petites variations de tonalité, pour *voir* les raccords |

### Phases 4 à 6 — Rendus : vue centrée, HDR et pleine résolution

Étapes [**4A**](../docs/GUIDE.md#4a--assembler-la-vue-centrée-nona-puis-multiblend), **4B**, [**5A**](../docs/GUIDE.md#5a--reporter-la-géométrie-sur-les-n-expositions), **5B** et [**6A**](../docs/GUIDE.md#6a--exporter-les-vues-centrées-à-pleine-taille) à **6C**.

| Script | Portée | Rôle |
| --- | :---: | --- |
| [***propager_geometrie.py***](propager_geometrie.py) | 🟡 | Reporte la géométrie optimisée de la vue centrée sur toutes les expositions |
| [***extraire_sous_projet.py***](extraire_sous_projet.py) | 🟢 | Garde seulement certaines images d'un projet (zone d'essai, ou projet de rendu sans variables) |
| [***redimensionner_projet.py***](redimensionner_projet.py) | 🟢 | Change la taille des images et/ou du panorama de sortie |
| [***deplacer_projet.py***](deplacer_projet.py) | 🟢 | Copie un projet ailleurs en réécrivant les chemins d'images |
| [***nona_images.ps1***](nona_images.ps1) | 🟢 | Rend avec *nona* une plage d'images, une par une, reprenable après interruption |
| [***rendre_projet.ps1***](rendre_projet.ps1) | 🟢 | Rend un projet complet : *nona* puis *enblend* ou *multiblend*, durées et pics de RAM ; `-Lisible` en tire une copie lisible |
| [***rendre_lisible.ps1***](rendre_lisible.ps1) | 🟢 | Copie lisible d'un rendu de *multiblend* (BigTIFF sans profil) : TIFF classique 16 bits avec le profil des images, et JPEG sRGB ; jusqu'à ≈ 700 Mpx |
| [***fusionner_par_exposition.ps1***](fusionner_par_exposition.ps1) | 🟢 | Fusionne avec *enblend* ou *multiblend* les images reprojetées d'un HDR, un panorama par exposition |
| [***enblend_vers_multiblend.cmd***](enblend_vers_multiblend.cmd) | 🟢 | Adaptateur à déclarer dans les préférences de *Hugin* à la place d'*enblend* : traduit la ligne de commande et fait fusionner par *multiblend* (lance `enblend_vers_multiblend.ps1`, à garder dans le même dossier) |
| [***surveiller_multiblend.ps1***](surveiller_multiblend.ps1) | 🟢 | Relève RAM du processus, RAM libre et taille de `TEMP` pendant une fusion |
| [***mesurer_charge.ps1***](mesurer_charge.ps1) | 🟢 | Charge CPU et mémoire de *Hugin*, *nona* et *enblend* pendant un rendu |
| [***profil_jonction.ps1***](profil_jonction.ps1) | 🟢 | Profil par bandes d'une jonction : fusion contre les deux sources |
| [***ranger_intermediaires.py***](ranger_intermediaires.py) | 🟢 | Range les images intermédiaires dans `_a_supprimer/` (ne supprime jamais) |

### Phase 7 — Tuiler et cadrer

Étapes [**7A**](../docs/GUIDE.md#7a--tuiler-avec-libvips) et [**7C**](../docs/GUIDE.md#7c--cadrer-les-deux-sources-facultatif).

| Script | Portée | Rôle |
| --- | :---: | --- |
| [***tuiler.ps1***](tuiler.ps1) | 🟢 | Pyramide Deep Zoom (`.dzi` + `_files`) d'un TIFF géant avec *libvips* : conversion sRGB 8 bits, aplatissement de l'alpha, `dzsave` en WebP ou JPEG ; durée et RAM relevées |
| [***cadrage_lightroom.py***](cadrage_lightroom.py) | 🟢 | Relit le recadrage décidé dans *Lightroom* et l'applique au HDR et à la pleine résolution (commandes `vips extract_area`) ; `--controle` mesure le vide par coin |

### Rédaction du guide

| Script | Portée | Rôle |
| --- | :---: | --- |
| [***verifier_renvois.py***](verifier_renvois.py) | 🔵 | Vérifie la numérotation du guide : identifiants cités mais absents, liens internes cassés, restes de l'ancienne numérotation, dans le guide, cet index, les études de cas et les scripts. `python verifier_renvois.py` (code de sortie 1 s'il y a un écart) ; `--releve` pour l'inventaire |

---

## 🛠️ Prérequis

| Outil | Pour quels scripts |
| --- | --- |
| ***Python*** 3 (bibliothèque standard) | Tous les scripts de géométrie |
| ***Pillow*** | Les scripts qui lisent des pixels : ***mesurer_ciel***, ***mesurer_gain_paires***, ***mesurer_bandes_ciel***, ***localiser_sauts_ciel***, ***comparer_rendus***, ***comparer_couleur***, ***rehausser_ciel*** (et `--controle` de ***cadrage_lightroom***) |
| ***exiftool*** (dans le `PATH`) | ***verifier_ordre***, ***controle_reglages_export***, ***renommer_par_raw***, ***cadrage_lightroom*** (option `--dng`) |
| ***Hugin*** (*nona*, *enblend*) | ***rendre_projet.ps1***, ***nona_images.ps1***, ***fusionner_par_exposition.ps1*** |
| ***multiblend*** | ***rendre_projet.ps1***, ***fusionner_par_exposition.ps1*** et ***enblend_vers_multiblend*** |
| ***libvips*** | ***ecart_paires*** (`vips` dans le `PATH`, ou variable d'environnement `VIPS`), ***tuiler.ps1*** (`-Vips`), ***rendre_lisible.ps1***, ***profil_jonction.ps1***, commandes imprimées par ***cadrage_lightroom*** |

Les chemins d'installation (*Hugin*, *multiblend*, *libvips*) sont écrits en tête des scripts PowerShell concernés, ou passés en paramètre : à adapter à votre poste.

---

## ❓ FAQ

**Un script plante sans message clair : par où commencer ?**
Ouvrir le fichier : la rubrique **ENTRÉES** liste les arguments attendus. Beaucoup de scripts lisent `sys.argv` directement : un argument manquant se traduit par une erreur d'index plutôt que par un message d'aide.

**Les scripts modifient-ils mes fichiers d'origine ?**
Les scripts de diagnostic ne font que lire. Les scripts de projet écrivent un **nouveau** `.pto` (ou le même si on le leur demande explicitement). Ceux qui touchent à des images (***renommer_pano***, ***renommer_par_raw***, ***ranger_intermediaires***) sont en essai à blanc tant qu'on n'ajoute pas `--apply`, et savent défaire (`--undo`) ou ne suppriment rien. Seul ***rendre_projet.ps1*** supprime des fichiers (les intermédiaires), et seulement après une fusion réussie.

**Pourquoi tant de constantes en dur ?**
Les scripts 🟡 ont été écrits pour une prise de vue précise. Les adapter reste plus simple que de tout paramétrer, et la rubrique **CONTEXTE** de chaque en-tête dit où se trouvent les valeurs. Un lanceur unique, qui aiguillera vers le bon script et portera ces paramètres, est prévu.

**Pourquoi un seul dossier et pas un dossier par portée ?**
Les scripts s'appellent entre eux (***rendre_projet.ps1*** → ***rendre_lisible.ps1***, ***enblend_vers_multiblend.cmd*** → `.ps1`) et toutes les commandes du guide se lancent depuis `$OUTILS`. Un seul dossier évite de casser ces liens ; la portée est dite ici.

---

## 📚 Pour aller plus loin

- [Guide général](../docs/GUIDE.md) : la séquence complète, phase par phase.
- [Étude de cas](../etudes-de-cas/2026-06-19-wattenberg-200mm/ETUDE-DE-CAS.md) et son [carnet](../etudes-de-cas/2026-06-19-wattenberg-200mm/TESTS-ANALYSES.md) : mesures et comparaisons faites avec ces scripts.

---

**Version** : 2.0
**Dernière mise à jour** : 2026-10-18
