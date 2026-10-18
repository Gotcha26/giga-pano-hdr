# Tests et analyses : ce qui est mesuré, ce qui reste à démontrer

Carnet d'expérimentation de l'[étude de cas](ETUDE-DE-CAS.md) (Wattenberg, 200 mm, 222 positions). Il tient à part tout ce que le [guide général](../../docs/GUIDE.md) ne doit pas affirmer : les **mesures et leurs analyses**, les **hypothèses** à vérifier par un test, les **pistes jamais essayées** et les **décisions** avec leurs raisons.

Le guide donne la **procédure** et ne contient ni statut d'avancement, ni résultat de test, ni historique : tout cela est ici. Quand une fiche de ce carnet passe à **Mesuré** et que la méthode qui en découle est stable, la procédure correspondante entre dans le guide. Les passages retirés du guide lors de sa mise au point sont conservés mot pour mot dans le [journal](#-journal-de-mise-au-point-retiré-du-guide-le-2026-10-11), en fin de carnet.

> **Numérotation et dossiers.** Les renvois au guide suivent sa numérotation actuelle (phase, puis étape en lettre : **3F**, **6B**). Les chemins de dossiers cités dans les fiches (`10_grille`, `20_optimisation`, `30_phase1_centree`, `40_hdr`, `50_pleine_res`, `60_tuiles`) sont ceux de l'époque des mesures ; ils s'appellent aujourd'hui `3_grille`, `3_optimisation`, `4_vue_centree`, `5_hdr`, `6_pleine_res` et `7_tuiles` (voir le guide, [**0D**](../../docs/GUIDE.md#0d--préparer-les-disques-et-les-emplacements)).

---

## 📋 Comment lire ce carnet

| Statut | Sens |
| :---: | --- |
| ✅ **Mesuré** | Résultat obtenu sur ce panorama, chiffres à l'appui |
| 🔬 **À tester** | Hypothèse ou extrapolation : le test est décrit, il n'a pas été fait |
| 🗃️ **Piste** | Idée jamais essayée, hors du chemin principal |
| 📌 **Décidé** | Choix pris, avec sa raison et ce qui permettrait de revenir dessus |

**Gabarit d'une fiche** : *question* → *hypothèse ou état* → *test* → *critère de réussite* → *si ça échoue* → *statut*. Une fiche « À tester » sans chiffre mesuré n'a **pas** de résultat : ne rien y inventer.

**Règle de tenue** : toute nouvelle affirmation non vérifiée entre ici **avant** d'entrer dans le guide.

| Fiche | Sujet | Statut |
| :---: | --- | :---: |
| [M-01](#m-01--rendu-de-la-vue-centrée-à-45-056-px) | Rendu de la vue centrée à 45 056 px (37, 111, 222 images) | ✅ |
| [M-02](#m-02--tuilage-libvips-à-45-056-px) | Tuilage *libvips* à 45 056 px | ✅ |
| [M-03](#m-03--affichage-dune-pyramide-dans-un-navigateur) | Affichage d'une pyramide dans un navigateur | ✅ |
| [M-04](#m-04--projections-avant-mesure-et-écarts) | Projections avant mesure et écarts | ✅ |
| [M-05](#m-05--ouverture-dun-tiff-de-507-mpx-dans-lightroom) | Ouverture d'un TIFF de 507 Mpx dans Lightroom | ✅ |
| [M-06](#m-06--enblend-lit-le-bigtiff-mais-ne-sait-pas-écrire-plus-de-4-go) | *enblend* lit le BigTIFF mais ne sait pas écrire plus de 4 Go | ✅ |
| [M-07](#m-07--multiblend-écrit-le-bigtiff--enblend-vers-png-plante) | *multiblend* écrit le BigTIFF (109 s, 8,2 Go de RAM) ; *enblend* vers PNG plante | ✅ |
| [M-08](#m-08--ciel--multiblend-contre-enblend---blend-colorspaceidentity) | Ciel : *multiblend* contre *enblend* `IDENTITY` (équivalent à l'intérieur, halo près des bordures) | ✅ |
| [M-09](#m-09--palier-de-trois-lignes-111-images--durée-et-ram-de-nona-et-de-multiblend) | Palier de trois lignes (111 images) : durée et RAM de *nona* et de *multiblend* | ✅ |
| [M-10](#m-10--multiblend---cache-threshold--la-ram-du-processus-est-plafonnée-le-fichier-est-identique) | *multiblend* `--cache-threshold` : RAM plafonnée, fichier identique | ✅ |
| [M-11](#m-11--rendu-complet-des-222-images-à-90-112-px--nona-et-multiblend---cache-threshold4g) | Rendu complet des 222 images à 90 112 px : *nona* et *multiblend* | ✅ |
| [M-12](#m-12--multiblend-ou-enblend-pour-la-vue-centrée-et-le-hdr-à-20-000-px-issue-31) | *multiblend* ou *enblend* pour la vue centrée et le HDR à 20 000 px | ✅ |
| [M-13](#m-13--nettoyage-des-poussières-sur-les-vues-centrées--2-h-pour-220-images) | Nettoyage des poussières sur les vues centrées : 2 h pour 220 images | ✅ |
| [M-14](#m-14--export-h-depuis-222-copies-virtuelles--3-min-54-s) | Export H depuis 222 copies virtuelles : 3 min 54 s | ✅ |
| [M-15](#m-15--correction-de-la-brume--des-écarts-de-teinte-entre-images) | Correction de la brume : des écarts de teinte entre images | ✅ |
| [M-16](#m-16--rendu-complet-des-222-images-à-90-112-px-avec-le-développement-validé-brume-et-tonalité-à-0) | Rendu complet à 90 112 px avec le développement validé (brume et tonalité à 0) : durées, ciel homogène | ✅ |
| [T-01](#t-01--enblend-et-les-fichiers-de-plus-de-4-go) | *enblend* et les fichiers de plus de 4 Go (résolu : M-06, réponse négative) | ✅ |
| [T-02](#t-02--ram-du-fusionneur-à-2-gpx) | RAM du fusionneur (*multiblend*) à 2 Gpx | 🔬 |
| [T-03](#t-03--durée-du-rendu-complet-à-90-112-px) | Durée du rendu complet à 90 112 px | 🔬 |
| [T-04](#t-04--superposition-du-hdr-et-de-la-pleine-résolution) | Superposition du HDR et de la pleine résolution | 🔬 |
| [T-05](#t-05--raccord-de-tonalité-entre-le-hdr-et-la-pleine-résolution) | Raccord de tonalité entre le HDR et la pleine résolution | 🔬 |
| [T-06](#t-06--20-000-px-suffisent-ils-au-hdr-) | 20 000 px suffisent-ils au HDR ? | 🔬 |
| [T-07](#t-07--hdr-plus-large-que-20-000-px) | HDR plus large que 20 000 px | 🔬 |
| [T-08](#t-08--crénelage-de-nona-à-forte-réduction) | Crénelage de *nona* à forte réduction | 🔬 |
| [T-09](#t-09--finitions-à-pleine-résolution) | Finitions à pleine résolution | 🔬 |
| [T-10](#t-10--tuilage-à-2-gpx) | Tuilage à 2 Gpx | 🔬 |
| [T-11](#t-11--fluidité-navigateurs-et-couleur-à-lœil) | Fluidité, navigateurs et couleur à l'œil | 🔬 |
| [T-12](#t-12--ouverture-dun-tiff-de-507-mpx-dans-lightroom) | Ouverture d'un TIFF de 507 Mpx dans Lightroom (résolu : M-05) | ✅ |
| [T-13](#t-13--vignettage-et-option-calques-de-hugin) | Vignettage et option Calques de *Hugin* | 🔬 |
| [T-14](#t-14--coût-de-linterface-de-hugin-pendant-nona) | Coût de l'interface de *Hugin* pendant *nona* | 🔬 |
| [T-15](#t-15--alternative-à-un-tiff-unique-de-plus-de-4-go) | Alternative à un TIFF unique de plus de 4 Go | 🔬 |
| [P-01 à P-07](#️-pistes-jamais-essayées) | Pistes jamais essayées | 🗃️ |
| [D-01 à D-08](#-décisions-et-leurs-raisons) | Décisions et leurs raisons | 📌 |

---

## ✅ Mesures acquises

### M-01 — Rendu de la vue centrée à 45 056 px

- **Question** : *enblend* tient-il en RAM sur une toile de 45 056 × 11 264 px (507 Mpx), et à quel coût ?
- **Conditions** : vue centrée (exposition 0), 3 sous-ensembles du maître, `nona` puis `enblend --blend-colorspace=IDENTITY` avec ***rendre_projet.ps1***. Sources : l'export 2560 (**supprimé depuis** : ce rendu ne se refait plus à l'identique).

| Sous-ensemble | *nona* | RAM *nona* | *enblend* | RAM *enblend* | Fichier |
| --- | --- | --- | --- | --- | --- |
| L3 (37 images) | 477 s | 3,4 Go | 360 s | 9,2 Go | 887 Mo |
| L2-L4 (111 images) | 1 418 s | 3,4 Go | 2 421 s | 13,4 Go | 1 911 Mo |
| **Complet (222 images)** | **2 820 s** | 3,4 Go | **7 703 s** | **20,3 Go** | **3 267 Mo** |

| Durée par image | 37 images | 111 images | 222 images |
| --- | :---: | :---: | :---: |
| *nona* | 12,9 s | 12,8 s | 12,7 s |
| *enblend* | 9,7 s | 21,8 s | 34,7 s |

- **Analyse** : *nona* est **linéaire** (≈ 13 s par image). *enblend* ne l'est pas : son coût par image **croît avec le nombre d'images** (la surface à raccorder grandit), et sa RAM aussi (9,2 → 13,4 → 20,3 Go), mais moins vite que le nombre d'images.
- **Autres constats** : total **2 h 55** ; TIFF **classique** de 3,27 Go en LZW (sous la limite de 4 Go), profil **Adobe RGB conservé** ; intermédiaires de *nona* : 8,9 Go pour 222 images. Avertissements `unable to run Dijkstra optimizer` (sans effet sur le résultat) ; `images do not overlap` observé sur la ligne L3 (trou 135-136 connu). Contrôle visuel par l'utilisateur : conforme ; ouverture dans *Lightroom* : fonctionnelle (M-05).
- **Limite de cette mesure** : elle ne se transpose **pas** à 90 112 px (voir T-02).
- **Statut** : ✅ Mesuré (2026-10-09).

### M-02 — Tuilage *libvips* à 45 056 px

- **Question** : *libvips* tuile-t-il un TIFF RGBA 16 bits Adobe RGB de 507 Mpx, et à quel coût ?
- **Conditions** : ***tuiler.ps1*** (conversion `vips icc_transform` vers sRGB 8 bits, puis `vips dzsave`, tuiles de 512 px, JPEG Q90), *libvips* 8.18.7.
- **Résultat** (`complet.tif`, 3,27 Go) : conversion **16 s**, `dzsave` **4 s**, **0,7 Go de RAM** à chaque étape, fichier temporaire 1,9 Go, **2 613 tuiles pour 146 Mo** (17 niveaux, 1 936 tuiles au niveau le plus fin, médiane de 41 Ko par tuile, aucune tuile vide). Sur la ligne L3 seule (887 Mo) : 71 Mo.
- **À savoir** : l'option `--profile` de `dzsave` ne convertit pas les pixels (elle ne fait qu'intégrer un profil) ; la conversion passe par `icc_transform`. Le canal alpha est aplati par l'enregistrement JPEG (parties vides en noir).
- **Statut** : ✅ Mesuré (2026-10-09).

### M-03 — Affichage d'une pyramide dans un navigateur

- **Question** : la page autonome affiche-t-elle une pyramide DZI de cette taille ?
- **Conditions** : `page-autonome/index.html` (*OpenSeadragon* 6.1.1), pyramide de la ligne L3 servie par `python -m http.server`, navigateur automatisé.
- **Résultat** : le panorama s'affiche en entier ; à 100 % les tuiles du niveau le plus fin se chargent et l'image est nette (herbe, lisière de forêt) ; mini-carte et indicateur de zoom fonctionnent ; le trou 135-136 apparaît en bande noire, comme prévu. Un défaut corrigé : le curseur de fondu s'affichait avec une seule source.
- **Non vérifié** : fluidité du déplacement (T-11), fondu entre deux pyramides (T-04).
- **Statut** : ✅ Mesuré (2026-10-09).

### M-04 — Projections avant mesure et écarts

| Grandeur | Projection avant | Mesure | Écart |
| --- | --- | --- | --- |
| Rendu de la vue centrée à 45 056 px | ≈ 2 h 40 | **2 h 55** | + 9 % |
| RAM d'*enblend* à 45 056 px | « 20 à 40 Go » (extrapolation linéaire d'un rendu à 100 Mpx) | **20,3 Go** | bas de la fourchette |
| Taille du TIFF à 45 056 px | ≈ 3,3 Go (LZW) | **3,27 Go** | conforme |
| *enblend*, durée par image | ≈ 23 s (mesure à 12 images, fenêtre à 100 %) | **9,7 à 34,7 s selon le nombre d'images** | la mesure à 12 images ne se transpose pas |
| HDR à 45 056 px | ≈ 22 h | ≈ 20 h (7 × 2 h 55, **extrapolé**, non mesuré) | cohérent |

- **Leçon** : extrapoler *enblend* d'une petite mesure sous-estime le coût par image. Mesurer sur des sous-ensembles croissants avant les grands calculs (voir T-02).
- **Statut** : ✅ Mesuré (comparaison des chiffres).

### M-05 — Ouverture d'un TIFF de 507 Mpx dans Lightroom

- **Question** : un panorama de 45 056 × 11 264 px (507 Mpx, sous la limite de 512 Mpx de *Lightroom*) s'ouvre-t-il ?
- **Constat** (de l'utilisateur, 2026-10-09) : le rendu de mesure `complet.tif` (3,27 Go, LZW, Adobe RGB) **s'ouvre dans Lightroom, qui le traite normalement**.
- **Ce que cela apporte** : la vue centrée à 45 056 px reste **retouchable dans Lightroom**, contrairement à la pleine résolution (2 030 Mpx, hors limite). C'est le seul rendu de cette taille disponible : son export source (2560) est supprimé, il ne se refait pas à l'identique (voir D-02).
- **Ce que cela ne démontre pas** : que ce rendu doive servir à quelque chose (voir P-07).
- **Statut** : ✅ Mesuré.

### M-06 — *enblend* lit le BigTIFF mais ne sait pas écrire plus de 4 Go

- **Question** : *enblend* 4.3 sait-il lire des intermédiaires BigTIFF et écrire un fichier final de plus de 4 Go ?
- **Conditions** (2026-10-09) : 20 images (L3 C18 à C27 et L4 C18 à C27, soit les images 129 à 138 et 166 à 175) à **90 112 × 22 528 px**, issues de l'export H ; `nona --bigtiff -z LZW`, puis `enblend --compression=none --blend-colorspace=IDENTITY`. La compression est coupée **pour forcer le dépassement** : le fichier final aurait fait ≈ 16 Go.

| Étape | Résultat |
| --- | --- |
| ***nona*** `--bigtiff` | **1 034 s** (≈ 52 s par image), pic de RAM **13,4 Go**, code de sortie 0. Les 20 intermédiaires sont du **BigTIFF** (en-tête `49 49 2B 00`), **3,25 Go** au total (≈ 160 Mo par image) |
| ***enblend*** : lecture et fusion | **Réussies** : les 20 intermédiaires BigTIFF sont lus et fusionnés |
| ***enblend*** : écriture | **Échec** : `enblend: error: Maximum TIFF file size exceeded`, puis `Postcondition violation! exportImage(): Unable to write TIFF data` (*vigra*, `tiff.cxx:877`). Code de sortie 1 ; *enblend* supprime le fichier invalide : **aucun fichier produit** |
| ***enblend*** : durée et RAM | **485 s** et **23,8 Go** (essai par le script), **464 s** et **24,1 Go** (second essai en direct, `-v`) : jusqu'à l'échec d'écriture |

- **Analyse** : l'écrivain TIFF d'*enblend* (*vigra*) produit du **TIFF classique**, limité à 4 Go ; *enblend* **lit** le BigTIFF sans difficulté. L'aide d'*enblend* 4.3 ne propose aucune option BigTIFF. La fenêtre à 100 % (1 030 Mo en LZW) et le rendu à 45 056 px (3,27 Go) restaient sous la limite, d'où l'absence de signal jusqu'ici.
- **Conséquence** : un rendu complet direct avec ***rendre_projet.ps1*** `-BigTiff -CompressionEnblend lzw` **échouerait à l'écriture finale, après plusieurs heures de calcul** : le panorama complet est estimé à ≈ 13 Go en LZW (**extrapolation**). Une chaîne de remplacement est nécessaire : voir [T-15](#t-15--alternative-à-un-tiff-unique-de-plus-de-4-go).
- **Observation sur la RAM, à ne pas sur-interpréter** : pic de 24 Go dès 20 images à 2 Gpx ; relevé ponctuel de **24,5 Go avec seulement 2 images chargées** (à 18 s de calcul). À 45 056 px, la RAM croissait avec le nombre d'images (9,2 → 13,4 → 20,3 Go, M-01) : cet écart n'est **pas expliqué**. Hypothèse, non vérifiée : *enblend* alloue des tampons de la taille de la toile (voir T-02).
- **Non testé** : l'écriture d'un fichier compressé en LZW sous 4 Go à cette taille (les 20 images donneraient environ 1,7 Go, d'après la fenêtre à 100 %).
- **Statut** : ✅ Mesuré (2026-10-09).

### M-07 — *multiblend* écrit le BigTIFF ; *enblend* vers PNG plante

- **Question** : T-15, pistes 1 et 2. *enblend* peut-il écrire un PNG (pas de limite de 4 Go) ? *multiblend* sait-il fusionner les mêmes intermédiaires et écrire du BigTIFF ?
- **Conditions** (2026-10-09) : les 20 intermédiaires BigTIFF de M-06 (`50_pleine_res\test_bigtiff\rendu\f_*.tif`, 90 112 × 22 528 px), sans rien d'autre en cours sur la machine. Journal : `essais_log.txt` du même dossier. *multiblend* 2.0.0 (horman.net/multiblend, archive `multiblend2.0rc5.zip`).

| Essai | Commande | Durée | Pic de RAM | Résultat |
| --- | --- | --- | --- | --- |
| ***enblend*** vers PNG | `--blend-colorspace=IDENTITY -o essai_png.png @liste` | 477 s | 23,0 Go | **Plantage** (code `0xC0000005`, violation d'accès) ; fichier de 0 octet |
| ***multiblend*** | `--bigtiff --compression=LZW --tempdir D:\tmp\multiblend -o essai_mb.tif` + les 20 images | **109 s** | **8,2 Go** | **Réussi**, code 0 ; BigTIFF valide (en-tête `49 49 2B 00`), **1,65 Go**, 25 439 × 7 996 px, 16 bits RVB + alpha |

- **Analyse** :
  - *multiblend* fait **4 à 5 fois plus vite** et avec **près de 3 fois moins de RAM** qu'*enblend* (485 s et 23,8 Go en M-06, qui échouait en plus à l'écriture). Il prend la boîte englobante des 20 images (d'où 25 439 × 7 996 px et non la toile entière) à partir des décalages écrits par *nona* dans les TIFF.
  - La taille de 1,65 Go correspond à l'estimation de M-06 (« environ 1,7 Go » pour ces 20 images) : le panorama complet serait donc bien de l'ordre de **13 Go en LZW** (extrapolation), ce que le BigTIFF de *multiblend* écrit sans limite.
  - **Contrôle visuel** (aperçu à 4 000 px de large, puis deux extraits à 100 % sur la jonction entre les deux lignes, herbe et feuillage) : **aucune couture visible**, tonalité continue. Le contrôle est partiel : deux zones, pas la totalité.
  - **Bande noire verticale** dans la ligne du haut (≈ 140 px de large, de la hauteur de la ligne) : c'est le **trou connu 135-136** (recouvrement négatif de −0,30°, **défaut de prise de vue** confirmé, voir le guide, étape **6B**), compris dans la sélection (images 129 à 138). Ses bords droits sont ceux des images : **aucun défaut du fusionneur**. *enblend* avait signalé de son côté « images do not overlap ».
  - ***enblend* vers PNG** : le plantage vient après la fusion complète, au moment de l'écriture. La cause (PNG, taille, mémoire) n'est **pas établie** : l'essai ne dit donc pas si le PNG fonctionnerait dans un autre cas. Il ne fournit en tout cas pas de voie praticable.
- **Non testé** : le rendu des 222 images (RAM et durée à l'échelle complète, relevées seulement sur 20 images) ; `--cache-threshold` ; l'enchaînement *multiblend* puis `vips dzsave` ; la comparaison de qualité avec *enblend* sur le ciel (les 20 images n'en contiennent pas) ; la différence de tonalité d'*enblend* (`--blend-colorspace=IDENTITY`) face à *multiblend* (pas d'équivalent connu).
- **Conséquence** : *multiblend* est retenu pour la pleine résolution (D-07). Voir les fiches T-15, T-02 et T-03.
- **Statut** : ✅ Mesuré (2026-10-09).

### M-08 — Ciel : *multiblend* contre *enblend* `--blend-colorspace=IDENTITY`

- **Question** : *multiblend* n'a pas d'équivalent à `--blend-colorspace=IDENTITY` (M-07, D-07). Rend-il le ciel aussi bien qu'*enblend* ?
- **Conditions** (2026-10-09) : **12 images de la ligne 0** (`L0_C12` à `L0_C23`, images 12 à 23 du maître, export H), toile de 90 112 × 22 528 px, projet `50_pleine_res\comparatif_ciel\ciel_5184.pto`. ***nona*** **une seule fois** (600 s, 13,4 Go) ; les **mêmes 12 intermédiaires** sont fusionnés trois fois, avec ***rendre_projet.ps1*** (`-SansNona`) : ***enblend*** `--blend-colorspace=IDENTITY` (la référence), ***multiblend*** par défaut, ***multiblend*** `--wideblend`. Les trois rendus sont ramenés à la même boîte (30 541 × 5 515 px, décalage 32 243 ; 1 529 dans la toile d'*enblend*) ; mesures avec *libvips* et ***comparer_couleur.py***, ***comparer_rendus.py***.

| Fusionneur | Durée | Pic de RAM |
| --- | :---: | :---: |
| ***enblend*** `IDENTITY` | 298 s | 24,2 Go |
| ***multiblend*** | **76 s** | **6,5 Go** |
| ***multiblend*** `--wideblend` | 87 s | 6,5 Go |

- **Ciel pur : équivalent.**
  - Bande de ciel de 30 541 × 1 700 px : écart absolu moyen **0,05 %** de la plage (≈ 0,1 niveau sur 255) ; moyennes par canal à 0,04 % près (*multiblend* à peine plus sombre).
  - Zone de 9 000 × 1 200 px, ondulation de couleur après retrait de la tendance (**comparer_couleur.py**) : écart-type R 0,069 (*enblend*) contre 0,068 (*multiblend*), G 0,058 contre 0,057, B 0,046 contre 0,045 ; amplitudes 0,37 à 0,50 des deux côtés. Différence moyenne −0,07 niveau.
  - À 100 % : aucune couture visible dans le ciel, ni dans l'un ni dans l'autre.
- **Écart localisé : un dépassement de *multiblend* près d'une bordure de couverture.** Juste au-dessus d'un coin d'image, au bas de la bande (le bord inférieur de la ligne 0, où la ligne 1 manque dans ce test), *multiblend* est **plus clair que les deux images sources** :

| Zone (100 × 100 px, R G B sur 65 535) | Source | *enblend* | *multiblend* | `--wideblend` |
| --- | --- | --- | --- | --- |
| Lueur | image 5 : 46 704 52 485 61 508 ; image 6 : 43 534 48 846 57 424 | 47 006 52 862 62 152 | **48 614 54 683 64 347** | 49 151 55 199 63 919 |
| Voisine à droite | image 5 : 46 501 52 242 61 324 | 46 545 52 291 61 360 | 47 113 52 950 62 143 | 47 468 53 273 61 398 |
| Voisine à gauche | image 6 : 46 074 51 927 60 962 | 45 899 51 708 60 707 | 45 526 51 280 60 212 | 46 338 52 104 60 353 |
| Ciel haut, au centre de la zone | — | 44 904 50 873 60 640 | 44 972 50 957 60 693 | 45 444 51 414 60 355 |

  - *enblend* reste à ≈ 0,5 % de la source ; ***multiblend* s'en écarte de 1,2 à 4 %** (jusqu'à ≈ 9 niveaux sur 255 en bleu), la valeur dépassant celle des deux images à la lueur. Cela ressemble à un **dépassement de la fusion multi-bandes** (halo) contre une bordure de couverture. À l'intérieur du ciel, loin d'une bordure, l'écart est de 0,1 %.
  - `--wideblend` (14 niveaux au lieu de 11) **ne corrige pas** : la lueur reste (R 49 151, plus haut qu'avec le réglage par défaut).
- **Analyse et limites** :
  - La lueur se trouve sur la **bordure basse du test**, qui n'est pas une bordure du panorama complet : dans le panorama, la ligne 1 s'y raccorde. **Pas démontré** que le même halo apparaît sur une jonction intérieure entre deux lignes ; il apparaîtrait en revanche sur le **bord extérieur** (haut, côtés, trous), qui est de toute façon à retoucher ou à recadrer (T-09).
  - Un seul endroit examiné de près ; l'écart signé moyen de la bande (+0,04 %) ne dit pas combien de bordures présentent ce halo.
  - La tonalité n'est comparée qu'au ciel (bleu clair sans nuage) ; l'herbe et le feuillage ne sont pas mesurés ici (M-07 : jonctions invisibles).
- **Conclusion provisoire** : *multiblend* convient pour le ciel **à l'intérieur** du panorama (écart de 0,05 %, ondulation identique) et il est **4 fois plus rapide**, avec **moins de 7 Go de RAM** contre 24. Le halo de bordure reste à vérifier sur une **jonction intérieure entre deux lignes** : le palier de **trois lignes (111 images, lignes 0 à 2)** de T-02 la contiendra ; c'est là qu'il faut regarder, à 100 %, la jonction ciel / horizon entre les lignes 0 et 1.
- **Suite (2026-10-10)** : au palier de 111 images, **deux jonctions de ciel intérieures sont sans halo** (écart ≤ 0,35 % à la source la plus proche, aucun dépassement) : voir [M-09](#m-09--palier-de-trois-lignes-111-images--durée-et-ram-de-nona-et-de-multiblend). Le halo reste **attendu sur le bord extérieur** du panorama, non mesuré.
- **Statut** : ✅ Mesuré (2026-10-09), confirmé sur deux jonctions intérieures de ciel (2026-10-10).

### M-09 — Palier de trois lignes (111 images) : durée et RAM de *nona* et de *multiblend*

- **Question** : *multiblend* tient-il en RAM à 1 Gpx (T-02) et en combien de temps (T-03) ? La jonction de ciel entre lignes est-elle propre (M-08) ?
- **Conditions** (2026-10-10) : **images 0 à 110** du maître (lignes 0 à 2), export H, toile de 90 112 × 22 528 px, projet `50_pleine_res\lignes_L0-L2\lignes_L0-L2_5184.pto` (extrait, redimensionné et rattaché comme `ligne_L0`). **Recyclage** : les 37 intermédiaires de la ligne 0 (`ligne_L0\rendu`) sont **copiés** (leurs lignes `i` sont identiques dans les deux projets, même toile, mêmes numéros `f_NNNN`) ; ***nona*** ne rend que les images **37 à 110**, une par une (**nona_images.ps1**, `-i`). Fusion : `rendre_projet.ps1 -Fusionneur multiblend -BigTiff -CompressionEnblend lzw -SansNona`. RAM libre avant la fusion : ≈ 22,5 Go, applications fermées.

| Étape | Durée | Pic de RAM |
| --- | :---: | :---: |
| ***nona*** , 74 images (37 à 110) | **3 762 s** (50,8 s par image) | 13,5 Go |
| ***nona*** , équivalent des 111 images (avec les 1 903 s de la ligne 0) | ≈ 5 665 s (1 h 34) | 13,5 Go |
| ***multiblend***, 111 images | **623 s** (5,6 s par image) | **24,6 Go** |

- **Résultat** : BigTIFF LZW de **6,87 Go**, **87 966 × 11 462 px** (1,008 Gpx), 16 bits, lu par *libvips*, code 0. 111 intermédiaires : 17,13 Go.
- **RAM** : 24,6 Go à 1,008 Gpx, soit 0,0244 Go/Mpx (0,0252 à la ligne 0 : **proportionnelle à la surface**). Ajustement sur les deux points (12,9 Go à 511 Mpx, 24,6 Go à 1 008 Mpx) : ≈ 0,9 Go + 0,0235 Go/Mpx. **L'ancien ajustement (3,4 Go + 0,019 Go/Mpx) prédisait 26 Go : trop haut de 1,4 Go.** Pour 222 images (≈ 1,95 Gpx) : **≈ 47 Go**, et non 40, soit **bien au-dessus des 32 Go**.
- **Durée** : 623 s pour 3 fois la surface de la ligne 0 (233 s) : **linéaire**, pas de ralentissement visible dû au disque ; la RAM a tenu (cache système libéré par Windows). Pour 222 images : ≈ 1 250 s (21 min) *si* la RAM suffit, ce qu'elle ne fera pas.
- **Contrôle visuel** : aperçu complet sans couture. **Deux zones de ciel à 100 %** (x ≈ 50 000, y ≈ 3 400 à 5 000 et 6 600 à 8 200), lisses, sans halo visible ; la seconde porte une lisière de forêt, nette. Poussières de capteur visibles, connues.
- **Jonctions de ciel, mesurées** (**profil_jonction.ps1** : profil par bandes de 50 lignes, bande bleue, fichier fusionné contre les deux images sources, sur 3 000 px de large). Les extraits à 100 % ci-dessus avaient été placés à l'estime ; cette mesure localise les jonctions avec la **zone utile de chaque image** (`vips find_trim` sur les intermédiaires de *nona*, qui sont des toiles entières sans décalage dans le TIFF). L'origine du fichier fusionné dans la toile est (2 146 ; 1 111) : le haut le plus haut de la ligne 0 et 90 112 − 87 966. Le panorama **fait le tour de la toile** (l'image 0 est à x = 87 128, l'image 36 à x = 3 895). **Validation de l'origine** : hors recouvrement, le fichier fusionné colle à la source seule à ±0,2 %.

| Jonction | Images | Zone (toile) | Recouvrement en y | Écart fusionné − source A | Écart fusionné − source B |
| --- | --- | --- | --- | :---: | :---: |
| Ligne 0 / ligne 1 | 12 et 49 | x 59 711 à 62 711 | 4 624 à 6 961 | −0,23 à +0,18 % | −1,05 à +0,10 % |
| Ligne 1 / ligne 2 | 49 et 86 | x 59 711 à 62 711 | 7 390 à 9 787 | −0,34 à +0,05 % | −0,17 à +0,11 % |

  - **Aucun dépassement** : à aucune bande le fichier fusionné n'est plus clair que les deux sources (le halo de M-08 était de **+1,2 à +4 %** au-dessus des deux). Il suit la source la plus proche, ou une valeur intermédiaire.
  - L'écart de −1,05 % à −0,83 % à la source B (bandes 4 674 à 4 824, jonction 0/1) vient de B, **plus claire de ≈ 1 % sur ses 250 premières lignes** (bord de l'image 49) : le fichier fusionné reste sur la source A, sans marche visible.
  - Les deux sources diffèrent de 0,1 à 0,5 % dans le recouvrement ; le fichier fusionné passe de l'une à l'autre en douceur (≤ 0,05 % par bande de 50 lignes).
  - **Observation** : un **motif en dents de scie de ±0,2 %, de période 250 lignes**, est présent dans les sources *et* dans le fichier fusionné (une marche de 250 niveaux tous les 5 bandes). Ce n'est donc pas un effet de *multiblend* ; son origine (reprojection par *nona*, ou bande dans les images) n'est pas élucidée.
- **Limites** :
  - **Deux jonctions, une seule colonne** (images 12/49 et 49/86), dans le **ciel** seulement, **bande bleue** seulement ; ni feuillage, ni horizon, ni jonction entre colonnes (jonction verticale), ni bord extérieur du panorama (haut, côtés, trous), où le halo de M-08 est attendu.
  - La RAM libre était de ≈ 22,5 Go pour un pic de 24,6 Go : le pic compte le cache, ce n'est pas la RAM « réellement nécessaire ».
  - Un seul rendu, un seul fichier : pas de répétition.
- **Statut** : ✅ Mesuré (2026-10-10) : RAM, durée, deux jonctions de ciel intérieures sans halo.

### M-10 — *multiblend* `--cache-threshold` : la RAM du processus est plafonnée, le fichier est identique

- **Question** : `--cache-threshold` (mémoire au-delà du seuil placée sur disque) permet-il de tenir en RAM au rendu des 222 images (≈ 47 Go attendus, M-09) ?
- **Conditions** (2026-10-10) : les mêmes 111 intermédiaires que M-09, `rendre_projet.ps1 … -Fusionneur multiblend -OptionsMultiblend '--cache-threshold=…' -SansNona`, dossier temporaire par défaut (C:, 478 Go libres), RAM libre de 25 Go au départ. Relevé toutes les 20 s (mémoire privée et *working set* du processus, RAM libre du système, taille de `%TEMP%`). Référence : M-09, sans option.

| Réglage | Durée | Pic de *working set* | Mémoire **privée** | RAM libre du système (minimum) | `TEMP` (maximum) | Fichier |
| --- | :---: | :---: | :---: | :---: | :---: | :---: |
| aucun (M-09) | 623 s | 24,6 Go | — | non relevée | — | référence |
| `12G` | 627 s | 24,2 Go | non relevée | non relevée | non relevé | **identique** (écart nul) |
| **`4G`** | **637 s** | **24,1 Go** | **4,1 Go** | **0,2 Go** | **14,9 Go** | **identique** (écart nul) |

- **L'option fonctionne.** Avec `4G`, la mémoire **privée** du processus reste à **4,1 Go** pendant tout le rendu (le seuil) ; le reste va dans un fichier de cache sous `%TEMP%` (jusqu'à 14,9 Go ici), supprimé à la fin (3,9 Go restants, étrangers au test).
- **Le « pic de RAM » du journal ne mesure pas la RAM occupée.** Le *working set* (24,1 Go) **compte les pages du fichier de cache** qui restent résidentes tant qu'il reste de la RAM : il atteint le même chiffre qu'avec ou sans option, d'où le premier verdict erroné du test à `12G`. La mesure fiable est la **RAM libre du système**.
- **Pas de ralentissement ici** (637 s contre 623 s), mais la comparaison est **trop favorable** : les 14,9 Go de cache tenaient encore dans la RAM (le système a vu sa RAM libre tomber à **0,2 Go** vers 12 h 38 et a rendu des pages par la suite). Ce qui est **mesuré** : sur disque ou en RAM, le résultat est identique pixel pour pixel. Ce qui **ne l'est pas** : la durée quand le cache dépasse la RAM disponible, qui est le cas des 222 images (≈ 43 Go de cache pour ≈ 25 Go de RAM libre).
- **Conséquences pour le rendu des 222 images** :
  - le plafond de mémoire privée est tenu, donc pas de risque d'épuisement mémoire du processus ;
  - mais la machine sera **à court de RAM libre pendant la fusion** : ne rien lancer d'autre (le point d'arrêt du guide s'applique) ;
  - prévoir **≈ 45 Go libres** pour le cache (C: par défaut ; `--tempdir` pour le déplacer) et une durée **supérieure aux 21 min extrapolées**, inconnue ;
  - le journal de `rendre_projet.ps1` ne donne pas la RAM utile : pour ce rendu, relever aussi la RAM libre du système avec ***surveiller_multiblend.ps1*** (à lancer en parallèle).
- **Limites** : un seul passage par réglage ; `12G` sans relevé de RAM libre ni de `TEMP` ; aucun test où le cache dépasse la RAM ; le disque de C: n'est pas qualifié (SSD supposé).
- **Statut** : ✅ Mesuré (2026-10-10) : l'option marche et ne change pas le résultat ; **durée à cache plus grand que la RAM non mesurée** (levé par M-11).

### M-11 — Rendu complet des 222 images à 90 112 px : *nona* et *multiblend* `--cache-threshold=4G`

- **Question** : le panorama complet (T-02, T-03) se rend-il en 32 Go de RAM, et en combien de temps ?
- **Conditions** (2026-10-10) : les 222 images du maître (`50_pleine_res\complet\complet.pto`, export H, toile de 90 112 × 22 528 px). **Recyclage** : les 111 intermédiaires du palier de trois lignes (M-09) sont **copiés** (13 s ; les 111 premières lignes `i` sont identiques dans les deux projets) ; ***nona*** ne rend que les images **111 à 221** (**nona_images.ps1**). Fusion : `rendre_projet.ps1 -Fusionneur multiblend -BigTiff -CompressionEnblend lzw -OptionsMultiblend '--cache-threshold=4G' -SansNona`, avec **surveiller_multiblend.ps1** en parallèle. Lightroom et Firefox fermés ; RAM libre de 22,1 Go au départ ; cache sous `%TEMP%` (C:, 477 Go libres).

| Étape | Durée | Détail |
| --- | :---: | --- |
| ***nona***, images 111 à 221 (111 images) | **5 910 s** (53,2 s par image) | 13,5 Go de RAM au pic |
| ***nona*** , équivalent des 222 images (avec les 1 903 s de la ligne 0 et les 3 762 s du palier) | ≈ 11 575 s (3 h 13) | |
| ***multiblend*** `--cache-threshold=4G`, 222 images | **1 273 s (21 min)** | mémoire privée **4,2 Go** ; RAM libre du système **0,2 Go** au minimum, de 14 h 55 à 14 h 59 ; `TEMP` jusqu'à **33 Go** |

- **Résultat** : BigTIFF LZW de **12,81 Go**, **88 658 × 20 312 px** (1,80 Gpx), 16 bits, lu par *libvips*, code 0. 222 intermédiaires : 35,11 Go. Aperçu complet : aucune couture visible.
- **Durée linéaire malgré un cache plus grand que la RAM** : 1 273 s pour 1,80 Gpx, soit 0,71 s par Mpx (623 s pour 1,008 Gpx : 0,62 s par Mpx), et **conforme à l'extrapolation de 21 min** (T-03) alors que le cache (33 Go) dépassait la RAM disponible (≈ 24 Go) : levée de la limite de M-10. Pas de pic de durée visible ; l'effet du cache disque est de **+15 % par Mpx** au plus.
- **RAM** : l'ajustement de M-09 prévoyait **≈ 47 Go** de RAM pour *multiblend* ; le cache (33 Go) + la mémoire privée (4,2 Go) donnent **≈ 37 Go** : l'extrapolation était **trop haute d'environ 10 Go**.
- **Poste** : la RAM libre est restée à 0,2 Go pendant ≈ 4 min ; pas d'incident constaté sur la machine (rien d'autre ne tournait).
- **Limites** : un seul rendu ; **aucune mesure de qualité** sur ce fichier (jonctions entre lignes 3 à 5, bords, trous) hors l'aperçu ; la chaîne **vers les tuiles** (T-10) n'est pas essayée.
- **Statut** : ✅ Mesuré (2026-10-10).

### M-12 — *multiblend* ou *enblend* pour la vue centrée et le HDR à 20 000 px (issue #31)

- **Question** : *multiblend* (retenu à 90 112 px, D-07) peut-il aussi remplacer *enblend* pour la vue centrée et pour les 7 calques du HDR (toile de 20 000 × 5 000 px), jusqu'ici fusionnés par *Hugin* avec *enblend* `--blend-colorspace=IDENTITY` ?
- **Conditions** (2026-10-12) : intermédiaires rendus **une seule fois** avec *nona* `--ignore-exposure` (option `-IgnorerExposition` de ***nona_images.ps1***), puis les **mêmes** intermédiaires fusionnés par groupe d'exposition (***fusionner_par_exposition.ps1***) avec chaque fusionneur. Trois essais, sur `pano_HDR_opt4.pto` (projet à 1 554 images) :
  1. **fenêtre « forêt »** : lignes 3 et 4, colonnes 18 à 23 (12 positions × 7 expositions = 84 images) ;
  2. **fenêtre « ciel »** : lignes 0 et 1, colonnes 18 à 23 (idem), avec le bord supérieur en escalier et des angles vides ;
  3. **groupe E0 complet** : les 222 images `_E0` (la vue centrée à 20 000 px).

  *Lightroom* fermé pour les essais 2 (reprise) et 3 ; *Firefox* ouvert (2 Go) ; RAM libre de 16,5 à 20 Go au départ ; aucun autre rendu.
- **Piège relevé** : *nona* applique **par défaut** la correction d'exposition (`Eev` des images ramené à celui du panorama, ligne `p`) : sans `--ignore-exposure`, les 7 expositions sortent saturées et quasi blanches (niveau moyen ≈ 98 % de la plage pour toutes). *Hugin* passe cette option pour les calques « sans correction d'exposition ». Un premier passage, fait sans, a été **écarté** (aucune valeur pour la qualité).

#### Durée et mémoire

| Essai (images par groupe) | *enblend* `IDENTITY` | *multiblend* | Rapport |
| --- | :---: | :---: | :---: |
| Forêt (12) | 17 s ; 1,4 Go | 6 s ; 0,5 Go | **2,8** |
| Ciel + bord (12), 2 passages, ordre inversé | 19,0 s et 18,7 s ; 1,3 à 1,5 Go | 12,1 s et 12,7 s ; 0,8 Go | **1,5** |
| **E0 complet (222)** | **1 572 s (26 min)** ; **4,0 Go** ; RAM libre ≥ 12,2 Go | **140 s (2 min 20)** ; **3,5 Go** ; RAM libre ≥ 12,6 Go | **11** |

- Le rapport **croît avec le nombre d'images** (2,8 puis 1,5 à 12 images selon le contenu, 11 à 222). L'écart de 12 images entre « forêt » et « ciel » est du **contenu** de la fenêtre (une reprise avec *Lightroom* fermé donne les mêmes durées qu'avec).
- ***nona*** : 338 s pour 84 images (4,0 s par image) ; 894 s pour 222 images, pic de RAM 0,7 Go, 1,81 Go d'intermédiaires.
- **RAM** de *multiblend* à 222 images : 3,5 Go, **sans** `--cache-threshold` ni cache disque. L'extrapolation par la surface depuis M-11 (37 Go à 90 112 px) donnait ≈ 2 Go : le bon ordre de grandeur.
- **Estimation du HDR complet** (7 groupes, à partir du groupe E0) : *enblend* ≈ 3 h 03 (à comparer aux 3 h 52 de J-07), *multiblend* ≈ 16 min.

#### Taille, position et couverture

- *enblend* écrit la **toile entière** (20 000 × 5 000 px, zones vides en alpha) ; *multiblend* écrit la **boîte englobante** : 3 321 × 1 754 (forêt), 3 693 × 1 854 (ciel), **19 677 × 4 509 (E0 complet)**. La boîte est la même pour les 7 expositions d'un même jeu, et **identique à la boîte de contenu du fichier d'*enblend*** (origine (323 ; 246) pour E0 complet, mesurée par `vips find_trim`).
- **Couverture identique** : 0,000 % de pixels couverts par un seul des deux (96,27 % de la toile pour E0 complet).
- ***Lightroom* ne fusionne pas les calques d'*enblend* de la petite fenêtre tels quels** (le cadre noir autour de la fenêtre, propre au test : 3 321 × 1 754 dans 20 000 × 5 000) ; il fusionne ceux de *multiblend*.

#### Écart entre les deux fusions (en % de la plage 16 bits)

- **Petites fenêtres** (écart absolu moyen) : forêt 0,2 à 1,1 % selon l'exposition (7 à 15 % des pixels au-delà de 1 %) ; ciel + bord 0,1 à 0,5 % (2 à 7 % au-delà de 1 %). Les écarts forts et étroits sont dans les **zones de couture** : les lignes de raccord diffèrent, donc le pixel gardé vient d'une autre image.
- **E0 complet** : 1,2 à 1,5 % (49 % des pixels au-delà de 1 %, 17 % au-delà de 3 %). La carte des différences (× 20) montre de **larges plages lisses**, à l'intérieur de chaque image, jusqu'à quelques pour cent : des différences de **tonalité à basse fréquence**, pas des raccords.
- **Qui s'écarte des images sources** (centre de **74 images** sur 222, une sur trois ; bloc de 100 × 100 px, canal rouge, comparé à l'image reprojetée) :

  | | Écart absolu moyen | Extrêmes |
  | --- | :---: | :---: |
  | *enblend* | **0,84 %** | +2,37 % / −5,24 % |
  | *multiblend* | **0,16 %** | +0,51 % / −0,45 % |

  *multiblend* **respecte la tonalité des images** ; *enblend* la déplace, parce qu'il répartit les écarts de tonalité entre images voisines sur de grandes distances (ce qui lisse l'ensemble au prix d'un écart aux sources).

#### Qualité visible

- **Ombres** (exposition la plus sombre de la fenêtre « forêt », éclaircie × 6, extrait de 800 × 500 px à 100 % dans le feuillage dense) : ni bruit coloré ni couture avec *multiblend* ; les deux fusions sont indiscernables à l'œil. **Jugement à l'œil, un seul extrait.**
- **Ciel et bord extérieur** (fenêtre « ciel », exposition E0) : écart absolu moyen de 0,04 à 0,08 % dans le ciel et le long du bord ; *multiblend* est de 0,03 % plus sombre en moyenne (moins d'un niveau sur 255), comme en M-08. Sur des blocs de 20 × 20 px, le plus fort écart positif de *multiblend* est de **+0,5 %** (E0 ; +0,24 % en E1, +0,05 % en E6) : **le halo de bordure de M-08 (+1,2 à +4 %) ne se reproduit pas** sur le bord supérieur et les angles vides.
- **Raccords dans le ciel** (« store vénitien », `mesurer_bandes_ciel.py`, E0 complet, x 10 500 à 16 000) : écart-type de l'ondulation 0,61 (*enblend*) contre 0,58 (*multiblend*), corrélation à une période +0,70 contre +0,71. Les bandes viennent des images (vignettage, étape **3F**) : **les mêmes dans les deux**.
- **Trou connu 135-136** (recouvrement négatif, défaut de prise de vue) : identique, bande noire de même largeur et mêmes bords.

#### Retour dans *Lightroom* (fenêtre « forêt », 12 positions)

| Jeu de calques | Taille | Profil | Résultat |
| --- | :---: | :---: | --- |
| *enblend*, toile entière | 20 000 × 5 000 | Adobe RGB | Fusion impossible : cadre noir autour de la fenêtre |
| *multiblend* seul | 3 321 × 1 754 | **aucun** | Fusion réussie (DNG de 9,9 Mo) |
| *enblend* rogné à la même boîte | 3 321 × 1 754 | Adobe RGB | Fusion réussie (DNG de 10,6 Mo) |
| *multiblend* + profil Adobe RGB | 3 321 × 1 754 | Adobe RGB | Fusion réussie (DNG de 10,5 Mo) |

- Les HDR issus des deux derniers jeux sont **« rigoureusement identiques »** (constat de l'auteur dans *Lightroom* ; les DNG diffèrent d'environ 0,5 % en taille, les pixels n'ont pas été comparés).
- ***multiblend* n'écrit aucun profil de couleur** : à recopier sur chaque calque (`exiftool -TagsFromFile … -icc_profile`, ou `-ExportExif` de ***fusionner_par_exposition.ps1***, qui recopie aussi l'EXIF).

#### Limites

- **Un seul panorama, une seule scène.** Le HDR complet (7 groupes à 222 images) n'a pas été fusionné dans *Lightroom* : la fusion n'est vérifiée que sur 12 positions.
- La **tonalité à basse fréquence** (écart de 1,2 à 1,5 % entre les deux fusionneurs sur E0 complet) n'est pas jugée à l'œil sur le panorama entier : l'écart aux images sources dit que *multiblend* est le plus fidèle, pas qu'il est le plus agréable.
- Le groupe E0 est la seule exposition mesurée à 222 images ; les durées des 6 autres groupes sont extrapolées.
- Un seul rendu par configuration à 222 images (pas de répétition) ; pas de test sur un trou de recouvrement à travers un panorama complet.
- **Statut** : ✅ Mesuré (2026-10-12). **Décision** : D-08.

### M-13 — Nettoyage des poussières sur les vues centrées : 2 h pour 220 images

- **Question** : que coûte, en retouche, un capteur poussiéreux sur un panorama de cette taille ?
- **Constat** (de l'utilisateur, 2026-10-17) : le nettoyage des poussières sur **environ 220 vues centrées** a pris **2 h** dans *Lightroom*.
- **Ce qui l'explique** : l'outil d'effacement des poussières de *Lightroom* est efficace sur une surface unie (ciel). Sur une surface texturée, la tache se fond parfois dans le motif, mais souvent une « tache » adoucie reste visible, répétée au même endroit d'image en image : il faut la reprendre au tampon, à la main, sur chaque photo.
- **Ce que cela apporte** : l'étape **0E** du guide (vérifier et nettoyer le capteur avant la prise de vue) est justifiée par un coût mesuré, et non par principe.
- **Ce que cela ne démontre pas** : la part du temps passée sur le ciel et sur les zones texturées (non séparée), ni la durée du test du capteur.
- **Statut** : ✅ Mesuré.

### M-14 — Export H depuis 222 copies virtuelles : 3 min 54 s

- **Question** : que coûte l'export H (222 vues centrées à pleine taille) dans *Lightroom* ?
- **Mesure** (2026-10-17, machine de référence, *Lightroom Classic* 15.4.1) : export des **222 copies virtuelles** de l'étape **6A.1** avec le préréglage « PANO TIFF (H) E0 » (TIFF 16 bits, ZIP, Adobe RGB, 3456 × 5184 px). Relevé toutes les 5 s de la mémoire et du processeur de *Lightroom* et de la RAM libre du système.
- **Résultats** :
  - **durée : 3 min 54 s**, du premier fichier créé (16:12:52) au dernier écrit (16:16:47) ;
  - **disque : 16,8 Go**, 222 fichiers de 78 Mo en moyenne ;
  - **RAM de *Lightroom*** : 6,3 Go avant l'export, **7,0 Go au plus** pendant (+0,7 Go) ; RAM libre du système au plus bas **8,3 Go** ;
  - **processeur** : en moyenne **4,2 cœurs** occupés par *Lightroom*, 6,6 au plus (16 threads disponibles).
- **Ce que cela apporte** : l'export H est **court et léger** ; le refaire après une retouche des copies virtuelles ne coûte que quelques minutes. Les cases « RAM » et « durée » de la Phase 2 sont remplies pour l'export H.
- **Ce que cela ne démontre pas** : la durée de l'export L (1554 images à 2 048 px) ni celle du développement, non chronométrés ; la RAM de *Lightroom* dépend aussi du catalogue et de l'historique de la session.
- **Incident** : le dossier désigné à l'export était `2026-06-19` au lieu de `2026-06-19\200mm` : l'export est parti un niveau trop haut, puis a été déplacé (même disque, instantané). C'est le risque du dossier choisi à l'export : le guide le signale en **2D**.
- **Statut** : ✅ Mesuré.

### M-15 — Correction de la brume : des écarts de teinte entre images

- **Question** : pourquoi, sur le rendu complet de 6C (222 vues centrées retouchées dans *Lightroom* avec les mêmes réglages), le ciel montre-t-il des colonnes et des images qui sortent du lot en teinte ? (issue #46)
- **Constat** (2026-10-17) : le rendu complet (88 658 × 20 312 px) montre, sur une bande de ciel au contraste ×8, des colonnes verticales régulières, une par image, et l'auteur repère des images à la colorimétrie différente (L0_C23, L4_C16/C17, L3_C10/C11).
- **Mesures**, en 16 bits, sur la même scène vue dans deux images voisines (médiane de tuiles de 100 px) :
  - **L0_C23 est plus bas d'environ 5 à 6 % en vert que C22 et C24** (C22→C23 −4,9 %, C23→C24 +6,2 %, médiane de la ligne +1,3 %). Confirmé. L4_C16/C17 : B +9,6 %, cohérent mais bruité. L3_C10/C11 : −3,4 %, **non confirmé** (dans le bruit de la méthode). Sur les lignes 3 et 4, le paysage limite la mesure.
  - **Ce n'est pas la prise de vue** : 1/100 s, f/10, ISO 100, manuel sur les 222 CR2 ; le niveau RAW linéaire est lisse à C23 (−1,0 % puis +0,1 %), et un développement neutre (*dcraw*, mêmes multiplicateurs pour toutes les images) ne le fait pas ressortir.
  - **Ce ne sont pas les réglages enregistrés** : le XMP des 222 TIFF donne les **mêmes** réglages globaux (Daylight 5500, teinte +10, **Dehaze +45**, Noirs −41, TSL, courbes). Seuls diffèrent le filtre « Dust Removal » (64 images) et 21 retouches de taches. L0_C23 a les mêmes réglages que C22 et C24.
  - **Même zone, RAW contre TIFF** : le RAW baisse de 0,5 à 1,8 % par image ; le TIFF fait +5,8, +10,9, +4,6, **−7,2**, +4,8 % en vert de C20 à C24.
- **Essai sans Dehaze** (9 images, L0 C18 à C26, **Dehaze 0 et Noirs 0**, Adobe RGB 16 bits) :

| Mesure | Avec Dehaze +45 | Sans Dehaze |
| --- | --- | --- |
| C22→C23, vert | −4,9 % | **+0,4 %** |
| C23→C24, vert | +6,2 % | **+0,5 %** |
| Bruit de tuiles | 3 à 6 % | 0,3 à 1 % |
| Rouge dans le ciel (moyenne, sur 65 535) | 0 (écrêté) | 14 633 |
| Motif de bord de chaque image | ±2 % | ±0,5 à 1 % |

- **Réexport complet sans Dehaze et vue d'ensemble à 6 000 px** (2026-10-17, 222 images, Dehaze 0, Noirs −10, Ombres −20, Contraste +25, balance 5 500 K teinte 0) : réglages **uniformes sur les 222** après remise à plat de 2 images dont un *Point Color* avait été posé par erreur (L2_C14, L3_C06). Rendu à 6 000 px : ***nona*** 215 s, ***multiblend*** 16 à 19 s, panorama de 5 903 × 1 352 px. Ondulation du ciel (crête-à-crête, luminance) : **1,18 → 0,84 %** sur la ligne 0 seule, **2,54 → 0,85 %** plus bas, **sans** correction de gain. Les colonnes très visibles au contraste ×8 sont nettement atténuées, il en reste de faibles.
- **Couleurs « ternes » sur ce rendu réduit** : ***multiblend*** n'écrit aucun profil ; les TIFF sont en Adobe RGB, lus comme du sRGB. Avec le profil Adobe RGB rendu à la réduction (`vips thumbnail … --import-profile --export-profile srgb`), la saturation d'une zone de ciel passe de **0,65 à 0,82** (rouge 76 → 40 sur 255). Les valeurs ne sont pas modifiées par l'assemblage, seule l'étiquette manque. Une part du rendu moins marqué vient aussi, **sans doute**, du retrait de Dehaze (le rendu avec Dehaze avait une saturation de 1,00 : bleu hors gamut) ; la part de chaque cause n'est pas séparée.
- **Ce que cela apporte** : les écarts d'image à image, le rouge écrêté et une grande partie du motif de bord disparaissent quand la **Correction de la brume** disparaît. Le guide interdit donc ce curseur sur les images (**2B**, **6A.1**).
- **Hypothèse, non prouvée** : *Dehaze* estime la brume sur chaque image, donc **même valeur ne veut pas dire même transformation**, et il amplifie de 5 à 10 fois de petites variations du RAW dans un bleu déjà hors gamut. Le contrôle d'uniformité des réglages de **2E** ne voit pas ce défaut.
- **Quatre exports complets comparés ensuite** (222 images chacun, rendu d'ensemble à 6 000 px, RAW neutre en témoin). Les réglages enregistrés sont **uniformes** dans chacun (0 champ divergent hors Dust Removal et Point Color) :

| Export | Brume | Curseurs de tonalité | Ondulation du ciel, ligne 0 (y 1 000-2 000 / 2 500-3 500) | Écarts de luminosité entre voisines, ligne 1 (vert) |
| --- | :---: | --- | --- | --- |
| A | 0 | Contraste +25, Ombres −20, Noirs −10 | 0,80 % / 0,82 % | −7 à +9 % |
| B | 0 | Contraste +25, Hautes lumières −100, Exposition +0,30, Blancs −10 | 0,40 % / 0,35 % | −11 à +7 % |
| C | **+24** | tous à 0 | 0,66 % / 1,03 % | ≤ 3,7 % (sauts de teinte : C30→C31 −11 % en bleu) |
| **D** | **0** | **tous à 0** | **0,32 % / 0,51 %** | **−1,3 à +1,3 %** (bruit 0,2 à 0,8 %) |

  - **RAW neutre** (*dcraw*, mêmes multiplicateurs) : C14 à C18 de la ligne 1 plates à ±0,6 % ; **la prise de vue est régulière**. Les sauts de A et B viennent donc du développement, **malgré des réglages enregistrés identiques**.
  - **Deux effets indépendants** : la **brume** crée les colonnes du ciel et les sauts de teinte (export C, même à +24) ; les **curseurs de tonalité** créent les sauts de luminosité de la ligne 1, qui mêle crête et ciel (exports A et B). L'export D, sans l'un ni l'autre, est homogène : les lignes 0 et 1 sont continues au rehaussement, aucune image ne sort du lot sur la ligne 0 (écarts en vert de +0,6 % en médiane, MAD 0,41).
  - **Ce qui a tenu dans D** : balance des blancs fixe (6 100 K, teinte −10), Vibrance +15, Mixage des couleurs, Calibration, teinte des ombres, filtre Dust Removal, retouches de taches. **Point Color** sur 8 images (L1 C06-C07, L2 C05 à C10) : pas de raccord sur la ligne 2 ; sauts de teinte de 3 à 4 % aux bords des images retouchées de la ligne 1 (C05→C06 +3,2 %, C07→C08 −3,8 %).
- **Ce que cela ne démontre pas** : l'essai de 9 images a retiré **Dehaze et Noirs ensemble**. **Dans A et B, les curseurs de tonalité sont groupés** : Contraste +25 est commun aux deux, mais sa part, celle des Ombres, des Hautes lumières, de l'Exposition et des Blancs ne sont **pas séparées** (il n'y a pas eu de bissection). Courbe à points, Texture et Clarté ne sont pas testées. Le rendu complet à 90 112 px n'est pas refait avec le développement D. Seules les lignes 0, 1 et 2 sont mesurées en détail ; à droite de la ligne 1 (arbres), le bruit des tuiles atteint 3 à 8 %.
- **Statut** : ✅ Mesuré (exports A à D) ; la part de chaque curseur de tonalité 🔬 à tester (bissection).

### M-16 — Rendu complet des 222 images à 90 112 px avec le développement validé (brume et tonalité à 0)

- **Question** : le rendu complet, fait avec le développement retenu à l'issue de M-15, est-il homogène, et que coûte-t-il comparé au rendu fait avec Dehaze ? (issue #46)
- **Mesures** (2026-10-18, machine de référence, 222 images de 3 456 × 5 184 px, projet `complet.pto`) :
  - ***nona*** : **12 080 s (3 h 21)**, ≈ 54 s par image, pic de RAM **13,5 Go**, 222 intermédiaires pour **35,1 Go**, aucune erreur ;
  - ***multiblend*** `--cache-threshold=4G` : **1 305 s (21 min 45)**, code 0, « pic de RAM » du journal 23,4 Go (trompeur avec le cache : il compte aussi le fichier de cache), RAM libre au lancement 19,3 Go ; intermédiaires supprimés à la fin (35,1 Go) ;
  - panorama : **88 658 × 20 312 px**, 4 bandes 16 bits, BigTIFF LZW de 13 709 994 436 octets (**12,8 Gio**).
  - Comparaison avec le rendu fait avec Dehaze (M-11 et rendu du 2026-10-17, même projet) : *nona* 12 487 s et *multiblend* 1 253 s (soit −3 % et +4 %), panorama de 11,4 Gio (**+12 %** ici).
- **Homogénéité du ciel** (profil horizontal en 16 bits, repliement sur la période d'une image de 2 436 px, crête-à-crête de la luminance, bandes de 1 000 px de haut) : **0,295 %** (y 1 000-2 000) et **0,552 %** (y 2 500-3 500), contre **2,39 %** pour le rendu avec Dehaze sur la bande 2 500-3 500. Cohérent avec la vue d'ensemble à 6 000 px (0,32 % et 0,51 %). Au rehaussement, ni colonne ni plaque ; seul subsiste un grain fin et régulier.
- **Extraits à 100 %** (ciel, feuillage, trois trous, paire saine 156-157) : ni couture, ni double image, ni raccord visible ; le toit et les poteaux sont nets.
- **Ce que cela apporte** : le développement validé en M-15 donne bien, à pleine résolution, un panorama homogène ; le coût de calcul est inchangé (la différence tient au temps de *nona*, à 3 % près).
- **Ce que cela ne démontre pas** : les **trous** de prise de vue (135-136, 165-166, 199-200) n'ont **pas été localisés avec certitude** (coordonnées estimées d'après la grille, aucune bande visible dans les extraits) ; les **poussières** et les 8 images en Point Color n'ont pas été jugées une à une ; le rendu n'est pas comparé pixel à pixel à l'ancien ; la RAM libre pendant la fusion n'a pas été relevée en continu.
- **Statut** : ✅ Mesuré.

---

## 🔬 Tests à faire

### T-01 — *enblend* et les fichiers de plus de 4 Go

- **Résolu** : voir [M-06](#m-06--enblend-lit-le-bigtiff-mais-ne-sait-pas-écrire-plus-de-4-go). **Réponse négative** : *enblend* 4.3 lit le BigTIFF mais ne sait pas écrire un TIFF de plus de 4 Go. La fiche garde son numéro pour ne pas décaler les suivantes ; la suite est en [T-15](#t-15--alternative-à-un-tiff-unique-de-plus-de-4-go).
- **Statut** : ✅ Mesuré.

### T-02 — RAM du fusionneur à 2 Gpx

- **Question** : *multiblend* (retenu, D-07) tient-il en 32 Go sur une toile de 90 112 × 22 528 px (2 030 Mpx), pour 37, 111 puis 222 images ?
- **État** : *enblend* (abandonné pour cette taille) : **20,3 Go** à 45 056 px pour 222 images (M-01), **23,8 à 24,1 Go dès 20 images** à 90 112 px (M-06). ***multiblend*** : **8,2 Go pour 20 images** (M-07), **6,3 Go pour 12 images** (fenêtre A), **6,5 Go pour 12 images** (ligne 0, M-08) et **12,9 Go pour 37 images** (ligne 0 entière, 86 217 × 5 933 px, 233 s, BigTIFF LZW de 3,44 Go, sans couture visible à l'aperçu). **La RAM suit la taille de la boîte englobante**, pas le nombre d'images : 168 Mpx → 6,5 Go, 511 Mpx → 12,9 Go. **Extrapolation, à deux points seulement** : ≈ 3,4 Go + 0,019 Go par Mpx, soit ≈ **26 Go pour 3 lignes** (≈ 1,3 Gpx) et ≈ **40 Go pour 222 images** (≈ 1,95 Gpx), donc **au-dessus des 32 Go** : le rendu complet risque de passer sur le disque. **Mesuré le 2026-10-10 sur 111 images (M-09) : 24,6 Go à 1,008 Gpx** (prévu : 26), d'où un ajustement corrigé de ≈ 0,9 Go + 0,0235 Go/Mpx et **≈ 47 Go pour 222 images** (et non 40). Aucune mesure sur 222 images.
- **Test** : ***rendre_projet.ps1*** `-Fusionneur multiblend -BigTiff -CompressionEnblend lzw` sur une ligne (37 images), puis **trois lignes (111, lignes 0 à 2 : elles contiennent la jonction de ciel à vérifier, M-08)**, puis 222, en relevant le pic de RAM du journal `rendu_log.txt`. **Avant de lancer** : aucun *nona*, *enblend* ni *multiblend* en cours (un rendu peut prendre 15 Go de RAM et plus). Le disque : ≈ 60 Go libres sur D:.
- **Critère** : pic < ≈ 28 Go à 222 images (marge sur les 32 Go) ; sinon essayer `--cache-threshold`.
- **Si ça échoue** : `--cache-threshold=…G` de *multiblend* (cache sur disque), puis rendu par blocs (T-15, piste 3). **`--cache-threshold` essayé sur 111 images (M-10)** : il plafonne la mémoire du processus (4,1 Go à `4G`) et laisse le résultat identique, mais la RAM libre du système tombe à ≈ 0 et la durée à cache plus grand que la RAM n'est **pas** mesurée.
- **Statut** : ✅ Mesuré à 222 images (M-11) : **mémoire privée 4,2 Go avec `--cache-threshold=4G`, cache de 33 Go sur disque, 1 273 s**. Sans cache, le critère (< 28 Go) n'aurait pas été tenu (≈ 37 Go).

### T-03 — Durée du rendu complet à 90 112 px

- **État** : ***nona*** ≈ 50 s par image à 90 112 px (mesuré sur la fenêtre à 100 %), soit ≈ 3 h pour 222 images (**extrapolation**). **Confirmé sur la ligne 0 (37 images, images 0 à 36)** : **1 903 s** (≈ 51,4 s par image), **13,5 Go de RAM**, 37 intermédiaires BigTIFF de **5,79 Go** au total (≈ 156 Mo par image), code 0 ; le coût par image et la RAM sont **linéaires et stables** de 12 à 37 images, soit ≈ **3 h 10** pour 222 images. Intermédiaires dans `50_pleine_res\ligne_L0\rendu` (projet `ligne_L0_5184.pto`). ***multiblend*** sur ces 37 images : **233 s** (≈ 6,3 s par image, comme sur 12 images : 76 s), soit ≈ **23 min** pour 222 images **si la RAM ne bascule pas sur le disque** (voir T-02). ***multiblend*** : **109 s pour 20 images** (M-07, ≈ 5,5 s par image) et **68 s pour 12 images** (≈ 5,7 s par image, essai de ***rendre_projet.ps1***). Pour ***enblend***, la mesure à 12 images (23 s par image) ne se transposait pas (M-04) : **ne pas extrapoler** *multiblend* sans les sous-ensembles de T-02. **Palier de 111 images (M-09, 2026-10-10)** : ***nona*** 74 images en **3 762 s** (50,8 s par image, 13,5 Go) en recyclant les 37 de la ligne 0 (≈ 5 665 s au total) ; ***multiblend*** **623 s** (5,6 s par image), **24,6 Go**, BigTIFF de 6,87 Go : **linéaire**, sans signe de bascule sur le disque. **Aucune estimation fiable pour 222 images** (la RAM de *multiblend* dépasserait 32 Go).
- **Mesuré sur 222 images (M-11, 2026-10-10)** : ***nona*** ≈ **3 h 13** au total (11 575 s ; 5 910 s pour les 111 dernières images), ***multiblend*** **21 min** avec cache disque : soit **≈ 3 h 35 de calcul** pour le panorama complet, sans recyclage.
- **Test** : les sous-ensembles de T-02 donnent la tendance.
- **Statut** : ✅ Mesuré (M-11).

### T-04 — Superposition du HDR et de la pleine résolution

- **Question** : la page autonome superpose-t-elle correctement deux pyramides de tailles différentes (HDR 20 000 × 5 000 px et pleine résolution 90 112 × 22 528 px) ?
- **Hypothèse** : *OpenSeadragon* place deux images dans un même repère et rééchantillonne à l'affichage, à condition qu'elles aient **le même cadre** (même rapport 4:1, même recadrage). Un recadrage fait sur le HDR seul décalerait les deux sources.
- **Test** : pyramide du HDR (export du DNG en TIFF 16 bits Adobe RGB à 20 000 px, sans recadrage, puis ***tuiler.ps1***) et, en attendant la pleine résolution, `complet.dzi` (45 056 px, même cadre 4:1) ; ouvrir `index.html?hdr=…&full=…`. Juger : alignement, saut de tonalité à la bascule (T-05), fluidité (T-11).
- **Point d'attention (2026-10-10, M-11)** : le panorama complet de *multiblend* est **rogné à la zone utilisée** (88 658 × 20 312 px) et ne stocke **pas sa position** dans la toile de 90 112 × 22 528 px ; le HDR, lui, a le cadre de sa propre toile. Pour superposer, **relever l'origine** (plus petit bord gauche et plus petit haut des 222 images, `vips find_trim` sur les intermédiaires ; un panorama de 360° peut passer d'un bord à l'autre) et la reporter à la visionneuse, ou recadrer le HDR à l'identique.
- **Origine relevée (2026-10-10)** : le panorama complet est placé en **(1 454 ; 1 111)** dans la toile de 90 112 × 22 528 px (haut le plus haut de la ligne 0 = 1 111 ; bord droit de l'image 0 = 90 112, donc gauche = 90 112 − 88 658 = 1 454). **Validé** par le profil de la jonction 0/1 (images 12 et 49) avec cette origine : hors recouvrement, le fichier fusionné colle à la source à ±0,25 %. Dans le cadre d'un HDR qui couvrirait la toile entière (largeur 1) : x = 0,016135, y = 0,012329, largeur = 0,983864.
- **Le HDR exporté est recadré (mesuré, 2026-10-10)** : `40_hdr\TIFF\pano_20000_E0-HDR.tif` fait **19 976 × 4 994 px** alors que le DNG fait 20 000 × 5 000 : *Lightroom* indique « Dimensions du fichier 20 000 × 5 000 » et « Dimensions actuelles 19 976 × 4 994 » (**recadrage enregistré dans les réglages**, appliqué par un export « sans redimensionner »). **Mesure du décalage** (vignettes de 300 × 200 px à l'échelle du HDR, recherche du décalage qui minimise l'écart des contours) en 5 points de x = 1 864 à x = 18 066 : décalage **constant de (+11 ; +3) px HDR**, donc un **recadrage** et non un changement d'échelle (aucune dérive sur 16 000 px). En supposant le recadrage **centré** (12 px à gauche, 3 px en haut, soit la moitié de 24 × 6), le décalage résiduel tombe à **(−1 ; 0) px** aux mêmes 5 points. Le sixième point (ciel uni, sans contours) est inexploitable.
- **Cadre retenu pour la page autonome** (en largeurs du HDR de 19 976 px) : x = (1 454 × 20 000 / 90 112 − 12) / 19 976 = **0,015555**, y = (1 111 × 20 000 / 90 112 − 3) / 19 976 = **0,012194**, largeur = 88 658 × 20 000 / 90 112 / 19 976 = **0,985060** : `?box=0.015555,0.012194,0.985060`. **Précision** : ±1 px HDR (≈ 4,5 px pleine résolution), mesurée avec un recadrage supposé centré. **Vérifié à l'œil** à fort zoom (cheminée) : arêtes simples à 50 % de fondu, arbres qui se prolongent sans décalage à la limite des tuiles pleine résolution déjà chargées. Pour s'en passer : annuler le recadrage dans *Lightroom* (Développement, Rogner) et réexporter à 20 000 × 5 000 px ; le cadre redevient 0,016135 / 0,012329 / 0,983864.
- **Critère** : alignement au pixel près à fort zoom, sans décalage visible.
- **Si ça échoue** : déclarer à la visionneuse la position de chaque image (`x`, `y`, `width` d'*OpenSeadragon*), ou reporter le recadrage à l'identique sur les deux.
- **Statut** : 🔬 À tester (issue #2).

### T-05 — Raccord de tonalité entre le HDR et la pleine résolution

- **Hypothèse** : le HDR (fusionné et développé dans Lightroom, rendu tone-mappé en 8 bits) et la pleine résolution (une seule exposition) n'auront pas exactement le même rendu : le passage de l'un à l'autre produirait un **saut de tonalité** visible.
- **Pistes** (non testées) : développer les deux avec les mêmes réglages et choisir le niveau de bascule dans une zone sans fort contraste ; transférer la tonalité du HDR sur la pleine résolution en appliquant à celle-ci le rapport entre les deux images, floutées et réduites.
- **Test** : observer la bascule dans la page autonome (T-04).
- **Observé le 2026-10-10** par l'utilisateur, à l'œil, avec le curseur de fondu de la page autonome (HDR 19 976 × 4 994 px et pleine résolution 88 658 × 20 312 px, cadre `box` de T-04, pleine résolution tuilée **avec** le profil Adobe RGB, voir T-10) : **« très bon »**, pas de saut de tonalité gênant constaté.
  - **Valeur limitée** : jugement à l'œil d'une personne, sur un écran, sans mesure ; une seule scène. Aucun écart de tonalité chiffré entre les deux sources. Sans le profil Adobe RGB à l'étape de tuilage, le résultat aurait été différent (≈ 3 niveaux sur 255 de moins en saturation, T-10).
- **Statut** : ✅ Jugé acceptable à l'œil (2026-10-10), non mesuré.

### T-06 — 20 000 px suffisent-ils au HDR ?

- **Hypothèse** : un visiteur zoome en **multipliant** l'agrandissement, cran après cran. Ce qui compte n'est pas la part des pixels que couvre le HDR, mais la part des **crans de zoom**.
- **Calcul** (non observé) :

| Écran (panorama en pleine largeur) | Zoom où le HDR (20 000 px) cesse d'être net | Zoom maximal (90 112 px) | Part des crans servie par le HDR |
| --- | :---: | :---: | :---: |
| 4K, 3 840 px de large | × 5,2 | × 23,5 | ≈ 52 % |
| Full HD, 1 920 px | × 10,4 | × 46,9 | ≈ 61 % |

Pour un écran 4K, le milieu géométrique de l'échelle de zoom tombe à √(3 840 × 90 112) ≈ **18 600 px** : un HDR de 20 000 px couvrirait donc à lui seul la première moitié du parcours. L'alignement des niveaux à 45 056 px (la moitié exacte de la pleine résolution) n'était qu'une convention : le plan est de superposer deux pyramides de tailles différentes (T-04).

- **Test** : regarder le HDR à l'écran 4K, en zoomant jusqu'à la bascule : le HDR paraît-il encore net à × 5 ?
- **Critère** : netteté perçue jusqu'à la bascule, sans que le HDR paraisse flou avant que la pleine résolution ne prenne le relais.
- **Si ça échoue** : agrandir le HDR (T-07).
- **Statut** : 🔬 À tester (raisonnement par le calcul seulement).

### T-07 — HDR plus large que 20 000 px

- **État** : décision de rester à 20 000 px (D-01). Le coût suit grossièrement la **surface** de la toile. Coût **extrapolé** si l'on y revient, en supposant les calques traités l'un après l'autre (base : 7 × 2 h 55 à 45 056 px, M-01) :

| Largeur | Part du coût à 45 056 px | Durée estimée | Export à 1:1 |
| :---: | :---: | :---: | --- |
| 20 000 px | 20 % | ≈ 5 h (**mesuré**) | ≈ 1 100 px |
| 30 000 px | 44 % | ≈ 9 h | ≈ 1 700 px |
| 36 758 px | 67 % | ≈ 14 h | 2 048 px (export L) |
| 45 056 px (plafond de Lightroom, 507 Mpx) | 100 % | ≈ 20 h | ≈ 2 560 px (supprimé : à réexporter) |

- **Éviter le sur-échantillonnage** : choisir l'export qui donne du 1:1 pour la largeur voulue.
- **Inconnues** : la fusion HDR de Lightroom sur 7 calques de 507 Mpx n'a **jamais été essayée** ; la RAM de 20,3 Go par calque interdit de les mener en parallèle.
- **Statut** : 🔬 À tester seulement si T-06 échoue.

### T-08 — Crénelage de *nona* à forte réduction

- **État** : ***nona*** n'applique pas d'anti-crénelage (son aide : « only the non-antialiasing interpolators of panotools are supported »). Réduire des sources de 5184 px à ≈ 21 % pendant la reprojection **pourrait** produire du crénelage ou du moiré sur les détails fins (feuillages, tuiles). Le HDR à 20 000 px, rendu depuis l'export 2048 (réduit à 54 %), n'a montré aucun défaut.
- **Test** : rendre une même fenêtre de deux façons (depuis l'export H réduit par *nona*, depuis l'export L réduit par Lightroom) et comparer à 100 %.
- **Statut** : 🔬 À tester.

### T-09 — Finitions à pleine résolution

- **Question** : comment retoucher les trous (135-136, 165-166, 199-200, 29-30), le bord supérieur en escalier et les poussières du capteur sur un panorama de 2 Gpx ?
- **État** : ***Lightroom*** est exclu (512 Mpx). Pistes **non testées** : ***Photoshop*** en PSB (*Photoshop 2022* installé ; 2,16 Gpx en 8 bits RGB ≈ 6,5 Go en mémoire avant calques et historique) ; retouche par blocs (une ligne d'images à la fois) puis report ; retouche sur le rendu de mesure à 45 056 px puis report.
- **À décider avant** le rendu complet de la pleine résolution.
- **Statut** : 🔬 À tester.

### T-10 — Tuilage à 2 Gpx

- **État** : à 45 056 px, 2 613 tuiles pour 146 Mo, 0,7 Go de RAM (M-02). À 90 112 × 22 528 px : ≈ 7 800 tuiles au niveau le plus fin (176 × 44) et ≈ 10 400 au total, soit **4 fois la surface** (**extrapolation**). RAM, durée, poids : inconnus. Fichier temporaire de la conversion : ≈ 8 Go.
- **Test** : tuiler la pleine résolution une fois rendue.
- **Mesuré le 2026-10-10** sur `complet_multiblend.tif` (88 658 × 20 312 px, 12,81 Go), avec `page-autonome\tuiler.ps1` (tuiles de 512 px, JPEG Q = 90), RAM libre de ≈ 19 Go au départ :

| Étape | Durée | Pic de RAM | Détail |
| --- | :---: | :---: | --- |
| `icc_transform` (Adobe RGB → sRGB, 8 bits, **avec `-ProfilEntree`**) | **48 s** | 1,5 Go | fichier temporaire de **6 870 Mo** (supprimé à la fin) |
| `dzsave` | **14 s** | 6,8 Go | **9 311 tuiles, 518 Mo**, 18 niveaux (0 à 17), 6 960 tuiles au niveau le plus fin (174 × 40, comme attendu), **aucune tuile vide** |

  - **Le panorama fusionné par *multiblend* ne porte aucun profil ICC** (le HDR exporté de *Lightroom* et l'ancien `complet.tif` d'*enblend* portent Adobe RGB, 560 octets). Un premier tuilage, fait avec `--embedded` seul, n'a donc **pas converti** les couleurs : sur une zone de forêt, le rouge moyen passait de 120,7 (sans conversion) à 116,8 (avec) sur 255, soit ≈ 3 niveaux, davantage sur les couleurs saturées : la pleine résolution aurait paru plus terne que le HDR. **Corrigé** : `tuiler.ps1 -ProfilEntree` fournit le profil Adobe RGB (extrait de l'export HDR, `60_tuiles\profils\AdobeRGB_export_Lightroom.icc`), qui ne sert que si le TIFF n'en porte pas. La pyramide a été **refaite** (518 Mo au lieu de 494 Mo).
  - **Total : 62 s** pour 1,80 Gpx : bien en dessous de l'extrapolation (4 fois la surface de 45 056 px : ≈ 10 400 tuiles). Les 9 311 tuiles viennent de la zone utilisée (88 658 × 20 312 px), pas de la toile entière.
  - Pyramide : `60_tuiles\complet_90112\complet.dzi` et `complet_files\`. **Contrôle visuel** : une tuile du niveau le plus fin (conifères) montre le détail à 100 % ; la tuile d'ensemble (niveau 11) montre le panorama entier, sans couture visible.
  - Le pic de 6,8 Go de `dzsave` compte probablement le fichier temporaire mappé en mémoire (même effet que pour *multiblend*, M-10) ; la RAM libre du système n'a pas été relevée, et le système n'a montré aucun incident.
- **Affichage essayé le 2026-10-10** dans la page autonome (`index.html?src=…complet.dzi`, serveur `python -m http.server` en local, navigateur Chromium piloté, fenêtre de 1 600 × 900) : la pyramide **s'ouvre** (88 658 × 20 312 px annoncés), le panorama entier s'affiche d'emblée, et un **zoom sur une cheminée** (≈ 0,46 fois la taille d'origine à l'écran) charge ses tuiles en **≈ 0,6 s** ; les briques, une tuile de toit et une silhouette à la fenêtre d'une grange lointaine se lisent nettement. Au total, **183 requêtes de tuiles** (niveaux 9 à 17), **≈ 16 Mo** transférés, médiane de **3 ms** et maximum de 67 ms par tuile. Seule erreur de console : `favicon.ico` (404), sans rapport.
  - **Valeur limitée** : serveur local (pas de latence réseau), un seul parcours (vue d'ensemble puis un zoom), pas de panoramique continu chronométré, pas d'autre navigateur ; la mémoire du navigateur n'a pas été relevée (`performance.memory` donne 5 Mo, non significatif). **La fluidité réelle reste à vérifier (T-11).**
  - **Observation** : sur le toit au premier plan, le bord d'un pan montre un **petit décrochement en escalier** à fort zoom ; le premier plan proche est le cas où une parallaxe est attendue. **Constaté aussi par l'utilisateur** (2026-10-10), qui juge qu'il faut tant zoomer que cela **ne justifie pas de s'y attarder** : cause non analysée, **accepté**, pas de correction prévue.
- **Non vérifié** : le poids et l'affichage d'une pyramide HDR superposée.
- **Statut** : ✅ Mesuré (2026-10-10) : tuilage à 1,8 Gpx en WebP en ≈ 1 min 50 (62 s en JPEG) ; **WebP Q85 retenu par le propriétaire**.
- **WebP à la place du JPEG (essai du 2026-10-10, demande de l'utilisateur : Piwigo sait gérer le WebP via un module)**. `tuiler.ps1 -Format webp -Qualite 85`. Le format des tuiles de la visionneuse est indépendant du module WebP de Piwigo (qui concerne les photos) ; OpenSeadragon lit le format indiqué par le `.dzi` (`Format="webp"`).
  - **Essai sur trois extraits de 2 048 × 2 048 px** (forêt, ciel, toit), comparés à la source en sRGB 8 bits : à **qualité égale (Q80)**, le WebP est **13 % (forêt), 29 % (ciel) et 39 % (toit) plus léger** que le JPEG, pour un PSNR identique (35,3 dB sur la forêt). **JPEG Q90 contre WebP Q85** : −40 % de poids sur la forêt, mais **2,7 à 3,4 dB de PSNR en moins** : une part du gain vient d'une fidélité moindre. Codage du WebP environ **8 fois plus lent** (≈ 350 ms contre ≈ 45 ms par extrait de 2 048 px).
  - **Pyramides complètes en WebP Q85** : pleine résolution **239 Mo contre 518 Mo en JPEG (−54 %)**, HDR **18 Mo contre 38 Mo** ; `dzsave` **56 s contre 14 s** (plus 8 s d'aplatissement). Écart moyen entre une tuile JPEG et la tuile WebP correspondante : **2,5 à 3,5 niveaux sur 255** (pleine résolution), 1 à 5 (HDR). Déployées sur le sous-domaine à côté des JPEG : `tuiles/complet_90112_webp/` et `tuiles/hdr_20000_webp/`.
  - **Deux pièges rencontrés** : (1) le WebP **garde le canal alpha** : sans aplatissement, les bords partiellement transparents laissent voir un **halo vert vif** (le surdépassement de la fusion, M-08) et les trous laissent voir le HDR dessous, qui y contient des blocs parasites ; `tuiler.ps1` **aplatit sur noir**, comme le JPEG, **seulement si l'image a 4 bandes** ; (2) `vips flatten` appliqué à une image RGB à **3 bandes** prend le bleu pour un alpha et **abîme l'image** (écart de 50 à 63 niveaux avec le JPEG, constaté sur le HDR) : d'où la condition sur le nombre de bandes. Le trou de prise de vue est, après correction, **identique au rendu JPEG** (barre noire propre).
  - **Non vérifié** (avant la décision) : le jugement visuel de l'utilisateur (JPEG Q90 ou WebP Q85 : **rendu depuis, WebP retenu**), la qualité optimale (seul Q85 a été tuilé en entier ; Q75 à Q90 sont comparés sur extraits), la fluidité (tuiles plus légères mais décodage plus lent côté navigateur), les navigateurs autres que Chromium, la lecture du WebP par les navigateurs anciens (la prise en charge est générale pour les navigateurs récents, **non testée ici**).
  - **Décision du propriétaire (2026-10-10) : « on conserve le WebP comme ça »** : **WebP, qualité 85, tuiles de 512 px**, comme format de référence (valeurs par défaut de `tuiler.ps1` ; `-Format jpg -Qualite 90` reste possible). Les pyramides WebP déployées sont celles de référence ; **les pyramides JPEG ont été retirées du serveur de test le 2026-10-10** (restent en local, `60_tuiles\complet_90112` et `hdr_20000`). **Pistes restantes** : un repli JPEG pour les navigateurs sans WebP (non testé), et un seuil de qualité réglable si une autre scène l'exige.

### T-11 — Fluidité, navigateurs et couleur à l'œil

- **Non vérifié** : fluidité du déplacement dans la page autonome (rien n'est chronométré) ; autres navigateurs que celui du test ; conversion Adobe RGB → sRGB jugée à l'œil, par comparaison avec le rendu dans *Lightroom*.
- **Prévu** (décision de l'utilisateur, 2026-10-10) : la fluidité sera **éprouvée sur une page autonome servie depuis son serveur** (`ssh o2switch`, `galerie.julien-moreau.fr`), donc avec une vraie latence réseau et un vrai hébergement, pas en local. À relever alors : temps de chargement des premières tuiles, fluidité au panoramique et au zoom, poids transféré (≈ 16 Mo pour la vue d'ensemble puis un zoom, en local), navigateur et connexion utilisés. Les pyramides à y déposer : `60_tuiles\complet_90112\` (518 Mo, 9 311 tuiles) et `60_tuiles\hdr_20000\` (38 Mo, 556 tuiles), plus `page-autonome\`.
- **Déployé le 2026-10-10** sur le sous-domaine `giga-pano.julien-moreau.fr` (racine `~/giga-pano.julien-moreau.fr/`, 576 Mo ; 9 311 et 556 tuiles comptées sur place) : `http://giga-pano.julien-moreau.fr/index.html?hdr=tuiles/hdr_20000/hdr.dzi&full=tuiles/complet_90112/complet.dzi&box=0.015555,0.012194,0.985060`. Archive de 591 Mo copiée en **35 s** par `scp`. Page marquée « noindex » (`robots.txt` et en-tête `X-Robots-Tag`). **HTTPS non utilisé** : le certificat d'AutoSSL n'était pas émis (certificat auto-signé) ; **l'utilisateur a décidé de laisser la page de test en HTTP** (page de test limitée, 2026-10-10). Le protocole du vrai site Piwigo reste celui de ce site.
- **Premier relevé depuis le poste de développement, en HTTP** (HTTP/1.1, requêtes **séquentielles**, 40 tuiles du niveau 17 de 130 Ko environ) : médiane **103 ms**, maximum **138 ms**, **4,2 s** pour les 40 ; fichiers de 200 octets (`.dzi`) en 50 à 100 ms. **Valeur limitée** : un seul client, un seul réseau, aucun test de fluidité réel (le navigateur ouvre 6 requêtes en parallèle, `imageLoaderLimit`) ; **la fluidité reste à juger par l'utilisateur**, de préférence en HTTPS (HTTP/2) et sur sa connexion habituelle.
- **Jugé par l'utilisateur le 2026-10-10 : « la fluidité est parfaite », validé à 100 %.** Sur la page déployée (HDR 19 976 × 4 994 px superposé à la pleine résolution de 88 658 × 20 312 px), depuis son poste et sa connexion. **Valeur limitée** : ressenti d'une personne, sans chronométrage ; le protocole (HTTP ou HTTPS) et le navigateur n'ont pas été relevés, et le certificat d'AutoSSL n'était peut-être pas encore émis (donc probablement HTTP/1.1, le cas le moins favorable) ; un seul panorama, un seul réseau, un seul visiteur : **aucun test de charge** (plusieurs visiteurs en même temps).
- **Tactile validé par l'utilisateur le 2026-10-10** : « le tactile fonctionne sur mon téléphone » (page de test ouverte sur son téléphone). **Valeur limitée** : un seul appareil, modèle et navigateur non relevés, jugement sans mesure ; **fait avec les tuiles JPEG** (le WebP n'était pas encore en ligne), **puis refait avec les tuiles WebP : validé aussi** (« je valide le WebP sur mon téléphone aussi »). **Tous les essais de l'utilisateur ont été faits sous Firefox** (version non relevée), poste et téléphone.
- **Charge à plusieurs visiteurs** : non mesurée, **peu de leviers** (hébergement mutualisé) ; décision de l'utilisateur de ne pas s'y attarder (2026-10-10).
- **Reste non vérifié** : les autres navigateurs, la conversion Adobe RGB → sRGB comparée au rendu de *Lightroom* (jugée « très bonne » à l'œil sur la bascule HDR / pleine résolution, T-05), le WebP (voir T-10).
- **Statut** : ✅ Fluidité validée par l'utilisateur (2026-10-10) ; reste partiel pour le reste.

### T-12 — Ouverture d'un TIFF de 507 Mpx dans Lightroom

- **Résolu** : voir [M-05](#m-05--ouverture-dun-tiff-de-507-mpx-dans-lightroom). La fiche garde son numéro pour ne pas décaler les suivantes.
- **Statut** : ✅ Mesuré.

### T-13 — Vignettage et option Calques de *Hugin*

- **Question 1** : l'option d'assemblage **Calques ... sans correction d'exposition** applique-t-elle la correction de vignettage ? On l'ignore ; un test avant/après le dira. Pour juger l'effet, on assemble en attendant avec la sortie « Corrigé en exposition, faible plage dynamique ».
- **Question 2** : le préréglage « Haute plage dynamique, exposition fixe » a aussi modifié la **courbe de réponse de la caméra** (colonnes `Ra` à `Re` : −3,296 / −0,103 / 0,42 / −0,139 / 0,208, alors qu'elles valaient 0). Avec une seule exposition, cette courbe est mal contrainte : si le rendu a une dynamique ou une teinte inhabituelle, remettre `Ra` à `Re` à 0. Effet non isolé.
- **Question 3** : l'activation du profil d'objectif dans Lightroom rend-elle l'étape **3F** « inutile ou secondaire » ? **Non testé** : le défaut résiduel mesuré est de l'ordre d'un niveau de gris sur 255, avec le profil activé.
- **Statut** : 🔬 À tester.

### T-14 — Coût de l'interface de *Hugin* pendant *nona*

- **État** : pendant ***enblend***, le coût de l'interface est négligeable (≈ 0,6 % d'un cœur). Pendant *nona* (journal « Sortie détaillée » affiché ou non, fenêtres réduites ou non), la comparaison **n'a pas été faite** ; les astuces du guide pour économiser les ressources sont un retour d'expérience, non chiffré.
- **Test** : ***mesurer_charge.ps1*** pendant la reprojection, dans les deux configurations.
- **Statut** : 🔬 À tester.

### T-15 — Alternative à un TIFF unique de plus de 4 Go

- **Question** : comment produire la pleine résolution sachant qu'*enblend* ne peut pas écrire plus de 4 Go (M-06) ?
- **À garder en tête** : le but est une **pyramide de tuiles**, pas un fichier géant. Un TIFF de 13 à 16 Go n'est qu'un intermédiaire avant `vips dzsave`.
- **Ce que M-06 établit déjà** (acquis, à ne pas refaire) :
  - *nona* écrit du BigTIFF sans difficulté (1 034 s, 13,4 Go de RAM pour 20 images à 90 112 px) ;
  - *enblend* **lit** le BigTIFF et fusionne les 20 images ;
  - *enblend* **n'écrit que du TIFF classique** (*vigra*), donc rien au-delà de 4 Go, et son aide 4.3 n'offre aucune option BigTIFF ;
  - le rendu complet en un seul fichier (≈ 13 Go en LZW, extrapolation) est donc **fermé** avec *enblend* en TIFF ;
  - **le test a coûté ≈ 25 min** (*nona* 17 min, *enblend* 8 min jusqu'à l'échec) au lieu de plusieurs heures de rendu complet : le protocole « compression coupée pour forcer le dépassement » a fait son travail.
- **Raison de chercher un autre outil plutôt que de contourner** : un rendu par blocs obligerait à gérer soi-même les jonctions (chevauchement, fondu, couture) que le fusionneur gère d'ordinaire. C'est du rafistolage, acceptable seulement si aucun outil n'écrit directement la sortie.
- **Pistes, par ordre de faisabilité et de rapidité** (toutes non testées) :

| Ordre | Piste | Effort | Durée de l'essai | Ce qu'on apprend |
| :---: | --- | --- | --- | --- |
| 1 | ***enblend* avec sortie PNG ou EXR** (`-o x.png`) : la limite de 4 Go tient peut-être au seul format TIFF, pas à *enblend*. *libvips* relit ensuite le fichier pour `dzsave` | une ligne de commande | ≈ 8 min, avec les intermédiaires de M-06 s'ils sont conservés | Si oui, rien ne change dans la chaîne. À vérifier : taille d'un PNG 16 bits à 2 Gpx, RAM (le pic de 24 Go restera) |
| 2 | ***multiblend*** (David Horman, horman.net/multiblend) à la place d'*enblend* : lit les sorties de *nona*, fusion multi-bandes avec couture, conçu pour les très grands panoramas (bien moins de RAM, plus rapide), option `--bigtiff` et `--tempdir` **à confirmer par `--help`** | un exécutable à télécharger, une commande | < 8 min probablement | RAM, durée et qualité de couture sur les 20 images, à comparer à *enblend* (ciel surtout). Réserves : outil à mainteneur unique, 16 bits à confirmer. Touche aussi T-02 et T-03 |
| 3 | **Rendre par blocs** (une ligne d'images, ou un groupe de colonnes) avec *nona* puis *enblend* ou *multiblend* : chaque sortie reste sous 4 Go en LZW ; assemblage dans ***libvips*** et tuilage sans fichier géant | script à écrire, jonctions à contrôler | ≥ 1 h | Faisable avec n'importe quel fusionneur. Point dur : la **jonction entre blocs** (chevauchement et fondu sur la zone commune, sinon couture visible) |
| 4 | **Masques de couture d'*enblend*** (`--save-masks`) puis fusion dans ***libvips*** par blocs, avec écriture directe en BigTIFF ou en tuiles | lourd : la fusion multi-bandes est à réécrire | une demi-journée | Dernier recours côté *Hugin* |
| 5 | ***Autopano Giga*** (licence disponible) : sortie native très grande taille (PSB ou tuiles), **à confirmer** | reprise d'un outil | inconnue | **Dernier recours** : l'outil est abandonné et l'auteur du projet n'y était pas parvenu, c'est la raison du passage à *Hugin* |

- **Écartés** : `-f` d'*enblend* (« manually set the size and position of the output »), qui n'avait pas réduit la toile lors d'un essai précédent, et dont la zone resterait au-delà de 4 Go en LZW ; sortie JPEG (65 535 px de côté maximum) ; *smartblend* (ancien, 32 bits), ImageMagick et GIMP (ni couture intelligente ni fusion multi-bandes).
- **Enchaînement** : si 1 réussit, rien ne change. Si 1 échoue et 2 réussit, on remplace *enblend* par *multiblend* dans ***rendre_projet.ps1***. Si les deux échouent, on passe à 3, en connaissant les limites de chaque outil.
- **Avant tout essai** : vérifier qu'aucun `nona` ni `enblend` ne tourne (un rendu *Hugin* peut occuper 15 Go de RAM et plus), et que les 20 intermédiaires BigTIFF de M-06 sont encore sur disque (sinon, 17 min de *nona* à refaire).
- **Test** : pistes 1 et 2 sur les 20 images de M-06 (images 129 à 138 et 166 à 175, 90 112 × 22 528 px) ; relever succès ou échec, durée, pic de RAM (***mesurer_charge.ps1***), taille du fichier, puis contrôle visuel des coutures à 100 %.
- **Critère** : fichier ou pyramide complète, sans couture visible, pic de RAM compatible avec les 32 Go (T-02).
- **Résultat des pistes 1 et 2** (2026-10-09, voir [M-07](#m-07--multiblend-écrit-le-bigtiff--enblend-vers-png-plante)) :
  - piste 1 (*enblend* vers PNG) : **plantage** à l'écriture après 477 s, aucun fichier ; cause non établie, voie non praticable ;
  - piste 2 (*multiblend*) : **réussie** sur les 20 images, 109 s, 8,2 Go de RAM, BigTIFF de 1,65 Go, jonctions invisibles sur les deux zones contrôlées. **Piste retenue.**
- **Décision** : *multiblend* remplace *enblend* pour la pleine résolution ([D-07](#-décisions-et-leurs-raisons)). Il est installé **hors du dossier temporaire**, dans `D:\Outils\multiblend\` (à côté de *libvips*).
- **Script adapté** : ***rendre_projet.ps1*** accepte `-Fusionneur multiblend` (défaut : `enblend`, inchangé). *multiblend* n'ayant pas de fichier de réponse, le script lui passe les noms relatifs (`f_0000.tif`…) depuis le dossier de rendu : 222 images tiennent en ≈ 3 000 caractères, très en dessous des 32 767 de Windows. **Essai du script** sur la fenêtre A (12 images, 90 112 px, `-BigTiff -CompressionEnblend lzw`) : *nona* 614 s et 13,4 Go, ***multiblend* 68 s et 6,3 Go**, intermédiaires supprimés après succès ; à comparer aux **272 s d'*enblend*** sur les mêmes images (guide, étape **6B**), soit **4 fois plus rapide**. La RAM d'*enblend* n'a pas été relevée sur cette fenêtre.
- **Reste à faire** : (a) rendu à l'échelle avec *multiblend* : une ligne (37 images), trois lignes (111), puis 222, avec RAM et durée (T-02, T-03), éventuellement avec `--cache-threshold` ; (b) enchaîner `vips dzsave` sur la sortie BigTIFF ; (c) **fait en grande partie** ([M-08](#m-08--ciel--multiblend-contre-enblend---blend-colorspaceidentity)) : le ciel est équivalent à celui d'*enblend* `IDENTITY` à l'intérieur (0,05 %), avec un halo de *multiblend* près d'une bordure de couverture, à vérifier sur une jonction **intérieure** entre lignes au palier de 111 images ; (d) contrôler les jonctions sur plus de zones. Les pistes 3 à 5 ne servent plus tant que (a) passe.
- **Fait le 2026-10-10** : (a) **réussi** aux trois paliers (37, 111 et 222 images) avec `--cache-threshold=4G` à 222 images ([M-09](#m-09--palier-de-trois-lignes-111-images--durée-et-ram-de-nona-et-de-multiblend), [M-10](#m-10--multiblend---cache-threshold--la-ram-du-processus-est-plafonnée-le-fichier-est-identique), [M-11](#m-11--rendu-complet-des-222-images-à-90-112-px--nona-et-multiblend---cache-threshold4g)) ; (b) **réussi** ([T-10](#t-10--tuilage-à-2-gpx)) ; (c) **confirmé** sur deux jonctions de ciel intérieures ; (d) **partiel** : les lignes 3 à 5, les bords et les trous ne sont pas mesurés. Les pistes 3 à 5 n'ont pas servi.
- **Statut** : ✅ *multiblend* retenu et validé jusqu'au panorama complet de 222 images (2026-10-10) ; contrôle des jonctions partiel.

### T-17 — Fondu automatique selon le zoom (HDR / pleine résolution)

- **Question** : l'opacité de la pleine résolution, pilotée par le zoom au lieu d'un curseur, donne-t-elle une bascule agréable ? (décision du propriétaire du 2026-10-10 : on prototype ; **repli** : le curseur manuel, déjà jugé parfait.)
- **Prototype** (page autonome, `&fondu=auto`, réglable par `&z0=` et `&z1=`, défauts 0,8 et 1,6) : zoom `z` = pixels écran par pixel du HDR ; opacité = `clamp((ln z − ln z0) / (ln z1 − ln z0), 0, 1)`, donc **linéaire en logarithme du zoom** (même vitesse à chaque cran).
- **Mesuré en local (2026-10-10)** : opacité **0** à la vue d'ensemble (z = 0,13) et à z = 0,5 ; **0,32** à z = 1 ; **0,585** à z = 1,2 ; **1** à z = 1,6 et au-delà. À la vue d'ensemble la pleine résolution ne charge que **5 tuiles** (niveaux grossiers) contre 11 pour le HDR. **À 58 % de fondu**, pas de dédoublement ni de halo visible, sur une scène (toit, cheminée, forêt).
- **Déployé** sur `giga-pano.julien-moreau.fr` : `…/index.html?hdr=tuiles/hdr_20000/hdr.dzi&full=tuiles/complet_90112/complet.dzi&box=0.015555,0.012194,0.985060&fondu=auto` ; l'URL sans `fondu=auto` garde le curseur manuel.
- **Non vérifié** : le **jugement du propriétaire** (le critère qui compte) ; l'effet sur la fluidité (la pleine résolution charge ses tuiles pendant le fondu) ; les seuils 0,8 et 1,6, qui sont un **premier réglage non optimisé** ; une seule scène ; zoom molette ou tactile (le « zoom » du tactile n'est pas essayé).
- **Jugé par le propriétaire le 2026-10-10 : « le fondu auto fonctionne très bien ».** **Décision** : le **fondu automatique est le mode par défaut du plugin**, et il doit être **débrayable** : une fois débrayé, la main revient sur le **curseur HDR / pleine résolution** (le comportement du banc d'essai sans `fondu=auto`). **Modalités décidées (2026-10-10)** : le débrayage est un **réglage de l'administrateur** (pas un bouton visiteur) ; les seuils gardent leurs **valeurs actuelles par défaut (0,8 et 1,6)** avec **un champ pour les ajuster** dans l'administration. Le seuil bas doit rester > 0 et < au seuil haut. **Réglages globaux** (décidé le 2026-10-10 : un seul jeu pour tout le plugin). Non prototypé : le banc d'essai n'a que les paramètres d'URL `fondu=auto`, `z0` et `z1`.
  - **Valeur limitée** : jugement à l'œil sur le panorama de test, avec les seuils par défaut (0,8 et 1,6), non optimisés.
- **Statut** : ✅ Validé par le propriétaire (2026-10-10), mode par défaut, débrayable par l'administrateur, seuils réglables.

### T-16 — Coût d'un contrôleur PHP pour servir les tuiles

- **Question** : un contrôleur PHP en `PATH_INFO` (modèle APG, qui rejoue les droits de Piwigo) sert-il les tuiles aussi fluidement que des fichiers statiques ? C'est l'option 2 de l'issue #2 (stockage et service des tuiles), à mesurer **après** le choix du service statique pour démarrer (décision du propriétaire, 2026-10-10).
- **Ordre de grandeur à tenir** : une vue d'ensemble puis un zoom = **183 requêtes de tuiles**, 6 en parallèle (`imageLoaderLimit`), ≈ 16 Mo ; en statique, médiane de 3 ms par tuile en local et 103 ms par tuile mesurés depuis le poste vers le serveur (HTTP, séquentiel). Chaque tuile passerait par le démarrage de PHP et de Piwigo (ou d'un script allégé).
- **Test** : un petit script PHP qui lit les mêmes tuiles (sans Piwigo, puis avec le contrôle de droits), servi par le même sous-domaine de test ; relever le temps par tuile, le débit parallèle et la charge du serveur ; comparer au statique sur le même parcours (vue d'ensemble puis zoom) et juger la fluidité.
- **Critère** : fluidité jugée équivalente par l'utilisateur, et un surcoût par tuile qui reste faible devant le temps réseau.
- **Si ça échoue** : servir en statique avec une URL non devinable (jeton aléatoire dans le chemin), ou un contrôle d'accès au niveau du serveur web (`.htaccess`).
- **Non vérifié** : tout. **Statut** : 🔬 À tester (dépend de la première étape du plugin pour la partie « avec droits »).

---

## 🗃️ Pistes jamais essayées

| Fiche | Piste | Remarque |
| :---: | --- | --- |
| **P-01** | **Paramètres d'objectif depuis la base *lensfun*** (onglet *Objectif* de *Hugin*) pour le vignettage et la distorsion | Dépend de la présence de l'objectif dans la base. Repli quand Lightroom n'a pas de profil |
| **P-02** | **Image de référence (*flat-field*)** : photographier une surface uniforme avec le même objectif, la même focale et la même ouverture (f/10), puis la donner à *Hugin* | Bonne méthode si l'on refait des panoramas avec cet objectif. Non essayée |
| **P-03** | **Piles automatiques de Lightroom** (*Photo → Piles → Mettre en pile automatiquement par heure de prise de vue*, intervalle de 1 à 2 s) pour isoler la vue centrée quand la prise de vue est moins rigoureuse | La séparation temporelle est **mesurée** (rafales à 0,09-0,13 s ; positions séparées d'au moins 3,9 s) ; le comportement d'une pile repliée à l'export est **à confirmer** sur un petit échantillon |
| **P-04** | **Fusion HDR dans Lightroom par position**, puis assemblage de 222 images HDR (au lieu de 1554) | Non testé : la fusion automatique doit donner un rendu identique d'une position à l'autre, ce qui n'est pas garanti |
| **P-05** | **Rotule sans respecter le point nodal** : optimiser une translation de la caméra (TrX, TrY, TrZ) dans *Hugin* | Délicat et déconseillé sur un panorama de cette taille. Pour un paysage lointain à 200 mm, la parallaxe est faible (analyse, non testée). Non essayée |
| **P-06** | **Grille numérotée autrement que dans l'ordre de prise de vue**, ou sens de rotation différent | Aucune étape du guide n'a été éprouvée sur autre chose qu'une grille numérotée dans l'ordre, de droite à gauche |
| **P-07** | **Garder la vue centrée à 45 056 px** (`complet.tif`, qui s'ouvre dans *Lightroom*, M-05) comme support de retouche ou comme niveau intermédiaire entre le HDR (20 000 px) et la pleine résolution (90 112 px) | Idées, rien d'essayé. Une retouche faite sur ce rendu ne se reporte pas automatiquement sur la pleine résolution (voir T-09). Source non refaisable à l'identique (D-02) |

---

## 📌 Décisions et leurs raisons

| Fiche | Décision (date) | Raison | Pour revenir dessus |
| :---: | --- | --- | --- |
| **D-01** | **HDR figé à 20 000 px** (2026-10-09) | Déjà produit et validé dans Lightroom ; 45 056 px coûterait ≈ 20 h pour un gain jugé marginal ; la pleine résolution sert le détail. **Conséquence acceptée** : à 20 000 px, le HDR reste en dessous du panorama Lightroom du 50 mm (26 362 px) en définition ; le détail vient de la pleine résolution, pas du HDR | T-06, T-07 |
| **D-02** | **Deux exports : L (2048 px, 1554 images) et H (pleine taille 5184 px, 222 vues centrées)** ; l'export 2560 est supprimé (2026-10-09) | L porte la géométrie du maître (erreur moyenne 0,32 px) et le HDR ; H ne sert que la pleine résolution. Le 2560 n'avait servi qu'aux rendus de mesure à 45 056 px | Refaire un export Lightroom |
| **D-03** | **Deux pyramides superposées** plutôt qu'une seule (2026-10-09) | Une pyramide unique exigerait que le HDR soit exactement la moitié de la pleine résolution (45 056 px) | T-04 |
| **D-04** | **Maître optimisé sur l'export L, transposé à chaque rendu** (`extraire_sous_projet` → `redimensionner_projet` → `deplacer_projet --images`) | La géométrie est en angles. Validé sur la fenêtre à 100 % (aucune dérive visible) et sur le rendu à 45 056 px | — |
| **D-05** | **Ranger les images intermédiaires dès que le rendu est fait** ; les `.pto` restent (2026-10-09) | Une image reprojetée pèse autant que toute la toile ; un `.pto` est léger et garde l'historique | Option `-GarderIntermediaires` de ***rendre_projet.ps1*** |
| **D-06** | **Plus de paliers intermédiaires** (36 758 px, 45 056 px) comme étapes du guide (2026-10-09) | Le HDR étant figé à 20 000 px, seules restent la fenêtre à 100 % et le rendu complet. Les mesures du palier à 45 056 px restent en M-01 comme justification | — |
| **D-07** | **Fusion de la pleine résolution par *multiblend*, pas par *enblend*** (2026-10-09) | *enblend* 4.3 n'écrit que du TIFF classique (4 Go au plus) et plante vers PNG (M-06, M-07) ; or le panorama complet fait ≈ 13 Go. *multiblend* écrit du BigTIFF, en 109 s et 8,2 Go de RAM pour 20 images, sans couture visible aux jonctions contrôlées (M-07). Un rendu par blocs aurait demandé de gérer soi-même les jonctions (« rafistolage »). *Autopano Giga*, qui avait échoué avant le passage à *Hugin*, n'a pas été repris. Le reste de la chaîne (vue centrée à 45 056 px, HDR) **gardait *enblend*** avec `--blend-colorspace=IDENTITY` : **révisé par D-08** | Si la tonalité de *multiblend* au ciel est mauvaise (T-15 c) ou si la RAM dépasse 32 Go à 222 images (T-02) : rendu par blocs (T-15, piste 3) ou masques de couture d'*enblend* (piste 4) |
| **D-08** | **Fusion par *multiblend* à toutes les échelles ; *enblend* réservé aux petits panoramas simples traités dans l'interface de *Hugin*** (2026-10-12) | À 222 images et 20 000 px (E0 complet), *multiblend* fusionne en **140 s** contre **1 572 s** (11 fois plus vite), avec 3,5 Go de RAM contre 4,0 Go. Qualité : ombres, ciel, bord extérieur, trou et raccords du ciel indiscernables ; *multiblend* **respecte la tonalité des images** (écart moyen de 0,16 % au centre des images, contre 0,84 % pour *enblend*) ; le halo de bordure de M-08 ne se reproduit pas ; retour dans *Lightroom* identique une fois le profil Adobe RGB recopié (M-12, issue #31). **Conséquences** : sortir de *Hugin* pour le rendu (*nona* `--ignore-exposure`, puis `fusionner_par_exposition.ps1` ou `rendre_projet.ps1 -Fusionneur multiblend`) ; recopier l'EXIF et le profil sur les calques HDR ; plus de `--blend-colorspace=IDENTITY` (sans objet pour *multiblend*) | Si une scène révèle des raccords visibles propres à *multiblend* (feuillage dense, trou), ou si la fusion HDR complète dans *Lightroom* diffère de celle d'*enblend* : revenir à *enblend* pour le cas concerné (le guide le garde comme voie simple) |

---

**Version** : 1.1
**Dernière mise à jour** : 2026-10-12

---

## 📝 Journal de mise au point (retiré du guide le 2026-10-11)

Passages qui figuraient dans le [guide](../../docs/GUIDE.md) et qui relèvent de la mise au point (statuts, résultats de tests, historique, état d'avancement). Ils sont conservés **mot pour mot**, avec leur origine ; le guide ne garde que la procédure.

### J-01 — Où en est la méthode (introduction du guide)

*Origine : guide, Introduction.*

**Où en est la méthode ?** Les Phases 1 à 5 sont **validées** sur un cas réel : le résultat est propre jusqu'à 20 000 px de large (HDR produit), sauf trois trous de prise de vue qu'aucun logiciel ne peut combler (voir [Limites](../../docs/GUIDE.md#-ce-que-ça-ne-fait-pas)). La **pleine résolution** (≈ 90 000 px de large, près de 2 milliards de pixels) est **rendue en entier**, tuilée et **affichée** sur ce panorama, en ≈ 8 h 40 de calcul pour les trois grands rendus ([Phase 6](../../docs/GUIDE.md#-phase-6--pleine-résolution), [Phase 7](../../docs/GUIDE.md#-phase-7--tuiler), et le tableau « Ce qu'il faut pour refaire ce panorama ») ; ses finitions et le plugin *Piwigo* restent à faire.

### J-02 — Alternatives écartées pour l'export

*Origine : guide, étape **2E**.*

**Alternatives écartées** (les pistes jamais essayées sont au [carnet](TESTS-ANALYSES.md#-pistes-jamais-essayées))

| Option | Avantage | Inconvénient |
| --- | --- | --- |
| Export JPEG 8 bits | Très léger (environ 1 Mo par image) | Perte de précision dans les ombres, pénalisante pour la fusion HDR. Acceptable **pour la validation de la vue centrée seulement** |
| Laisser ***Hugin*** lire les RAW | Pas d'export | Développement automatique non maîtrisé, différent de celui de Lightroom |

### J-03 — Tests du script verifier_ordre.py sur séries synthétiques

*Origine : guide, étape **2E**.*

*Testé sur des séries synthétiques* (vue centrée au milieu avec un pas de 1/3 IL, en dernière position, en première position, motif irrégulier, rafale cassée par une image manquante) *et sur l'export précédent de 1554 images* (motif +0, −3, −2, −1, +1, +2, +3 IL, pas de 1 IL : conforme).

### J-04 — Valeurs de référence et résultat mesuré de la correction du vignettage

*Origine : guide, étape **3F**.*

**Valeurs de référence** relevées sur `30_phase1_centree\pano_grille_opt4.tif` (6000 × 1500 px, vignettage non corrigé, zone ci-dessus) : ondulation de luminosité écart-type 0,94 (*mesurer_bandes_ciel*), amplitude 7,6 niveaux ; aucun saut supérieur à 6 niveaux (*localiser_sauts_ciel*) ; couleur : B/R écart-type 0,37 %, G/R 0,15 % (*comparer_couleur*).

**Résultat mesuré** : deux rendus de la vue centrée à 6000 px de large, avant et après la correction (`pano_grille_opt_ciel30-2.tif` et `-3.tif`), comparés sur une zone de ciel pur (x 3900-4900, y 100-200) avec ***comparer_rendus.py*** et ***comparer_couleur.py*** :

| Mesure (niveaux sur 255) | Avant | Après |
| --- | :---: | :---: |
| Luminosité moyenne de la zone | référence | **+2,2** (la correction éclaircit) |
| Ondulation de luminosité, écart-type | 0,46 | 0,37 (−20 %) |
| Ondulation de luminosité, crête à crête | 2,35 | 2,07 |
| Ondulation de couleur B/R, écart-type | 0,24 % | 0,22 % |
| Ondulation de couleur G/R, écart-type | 0,32 % | 0,35 % |

Écart de gain entre images voisines du ciel (***mesurer_gain_paires.py***, 21 paires de la ligne du haut, même portion de ciel vue dans les deux images) : rapport moyen **1,002**, écart-type 0,5 %, soit moins d'un niveau de gris (la mesure est limitée par l'arrondi à l'entier).

**Conclusion** : la correction du vignettage est bien appliquée (elle éclaircit de 2 niveaux et réduit l'ondulation d'environ 20 %), mais **le défaut résiduel est de l'ordre d'un niveau de gris sur 255** : les images voisines ont la même exposition à moins de 1 % près. Ce niveau n'est visible que sur un ciel lisse, très contrasté ou fortement retouché (fusion HDR, Dehaze, Texture, Clarté), qui amplifie ces écarts. Les mesures ne justifient pas d'optimiser l'exposition par image.

### J-05 — Résultat de l'affinage des images faibles

*Origine : guide, étape **3G**.*

**Résultat obtenu sur ce panorama** (222 images `_E0`, export 1365 × 2048, profil d'objectif Lightroom) :

| Étape | Erreur moyenne | Écart-type |
| --- | :---: | :---: |
| Passe 1 : positions | 0,66 | 1,82 |
| Passe 2 : + objectif (v, a, b, c) | 0,65 | 1,82 |
| **Affinage des 9 images faibles** | **0,32** | **0,50** |

Rendu à 6000 px avant et après l'affinage : les deux « ombres » (traînées grises qui prolongeaient une crête dans le ciel, aux images 30 et 31) ont disparu et la crête est nette. Dans l'objectif optimisé, le champ de vue reste à 6,867° (la valeur théorique d'un 200 mm) et la distorsion est faible (a = −0,0006, b = 0,0029, c = −0,0032) : la correction du profil d'objectif dans Lightroom a normalisé la géométrie. *(La mesure de l'effet sur les « tranches » de tonalité n'a pas pu être faite proprement : les poussières du capteur contaminent la zone mesurée.)*

Les derniers défauts de la vue centrée sont des **limites de prise de vue** : trois ou quatre paires qui ne se recouvrent pas (135-136, 165-166, 199-200 et, après l'affinage, 29-30), à retoucher, le bord supérieur en escalier à recadrer, et les poussières du capteur à traiter en finition.

### J-06 — Option --coarse-mask d'enblend

*Origine : guide, étape **4A**.*

> *Au cas où* : l'option `--coarse-mask` d'***enblend*** est censée accélérer le calcul des raccords. Mesurée ici (7 calques, 5000 px de large, 1554 images), elle n'a **rien changé** ni à la durée (environ 22 minutes avec ou sans) ni, à l'œil, au rendu après fusion HDR dans Lightroom. Elle n'est donc pas utilisée.

### J-07 — Temps mesurés du HDR (nona, enblend)

*Origine : guide, Phase 5.*

### Temps mesurés (machine de référence : Windows 11, 32 Go de RAM)

| Opération | Taille | Durée |
| --- | --- | --- |
| Ouverture de `pano_HDR_opt4.pto` dans *Hugin* | 1554 images | *non chronométrée* (très lente) |
| Assemblage des 7 calques (nona + enblend) | 5000 px de large | **22 min** : *nona* ≈ 6-7 min (1554 images reprojetées, environ 3,7 par seconde), puis *enblend* ≈ 15 min (7 calques) |
| Espace temporaire pendant le rendu | 5000 px de large | ≈ 0,6 Go (1554 intermédiaires de 0,5 Mo) ; les 7 fichiers finaux pèsent 37 à 42 Mo chacun |
| Reprojection *nona* des 1554 images | 20 000 px de large | **69 min** (11:39 → 12:48), soit 13 images par minute : seulement ×10,6 par rapport à 5000 px, alors que les surfaces sont ×16 |
| Intermédiaires *nona* | 20 000 px de large | **12,1 Go** (8,0 Mo en moyenne), contre 10 Go projetés |
| Fusion *enblend*, **premier calque** | 20 000 px de large | **27 min** (12:48 → 13:15), fichier de 652 Mo, RAM d'*enblend* de 1 à 2 Go : ×12,9 par rapport aux ≈ 2 min par calque à 5000 px (surface ×16) |
| Fusion *enblend*, 7 calques | 20 000 px de large | **3 h 52** (12:48 → 16:40), soit ≈ 33 min par calque en moyenne : les trois premiers ont pris 27 min chacun, les suivants plus (on ne le sait pas précisément : *Hugin* réécrit les 7 fichiers à la toute fin) |
| **Rendu complet des 7 calques** | 20 000 px de large | **≈ 5 h** (≈ 11:38 → 16:40) : *nona* 1 h 09 + *enblend* 3 h 52. Fichiers finaux : 557 à 652 Mo chacun, **4,2 Go** pour les 7. Aucun intermédiaire restant |
| Assemblage de la vue centrée seule (222 images) | 6000 px de large | *quelques minutes (non chronométré)* |

### J-08 — Résultats des tests de rendu des calques HDR à 5000 px

*Origine : guide, Phase 5.*

**Résultats du test avec `pano_HDR_opt4.pto` (géométrie finale, 5000 × 1250 px)** : les **7 fichiers finaux** `pano_HDR_opt4_exposure_0000.tif` à `0006.tif` sont bien produits, en TIFF 16 bits RGBA compressé LZW (37 à 42 Mo), avec le même ordre que précédemment (luminosité moyenne croissante 0000 = normale, 0001 à 0003 = −3 à −1 IL, 0004 à 0006 = +1 à +3 IL). **Tant que le rendu tourne, on ne voit que des fichiers `_exposure_layers_NNNN.tif`** : ce sont les 1554 images intermédiaires reprojetées (0,5 Mo chacune), pas les couches ; les 7 fichiers finaux n'apparaissent qu'après le passage d'*enblend*.

**Résultats du premier test (5000 × 1250 px, projet `pano_HDR_opt.pto`)** :

| Point | Constat |
| --- | --- |
| Nombre de fichiers | **7** : `pano_HDR_opt_exposure_0000.tif` à `0006.tif` (option Calques seule cochée, préfixe court : plus d'erreur 206) |
| Ordre | L'ordre suit les piles, pas la luminosité : 0000 = normale, 0001 à 0003 = −3, −2, −1 EV, 0004 à 0006 = +1, +2, +3 EV (vérifié par la luminosité moyenne) |
| Format | TIFF 16 bits **RGBA** (canal alpha pour les zones sans image), profil Adobe RGB conservé, 40 à 45 Mo chacun à 5000 px |
| EXIF d'exposition | **Absents** (temps de pose, ouverture, ISO, compensation) |
| Lightroom | **La fusion HDR fonctionne** après recopie de l'EXIF d'exposition (voir ci-dessous) |

### J-09 — Ce que le premier test HDR a révélé

*Origine : guide, Phase 5.*

**Ce que ce test a révélé** : la fusion HDR de Lightroom met en évidence des « colonnes » de tonalité dans le ciel, à chaque raccord. Le défaut existe **déjà avant la fusion HDR** (il se voit sur l'exposition normale) ; la fusion ne fait que l'amplifier. C'est précisément l'intérêt de la démarche progressive : les rendus petits (5000 px, quelques minutes) servent à repérer les défauts **avant** de payer le rendu à 20 000 px. La correction proposée est à l'étape [**3F**](../../docs/GUIDE.md#3f--corriger-le-vignettage-tonalité-du-ciel).

### J-10 — Validation du HDR à 20 000 px dans Lightroom

*Origine : guide, Phase 5.*

Les 7 calques de 20 000 × 5 000 px (≈ 5 h de rendu, 4,2 Go) ont été importés dans Lightroom, avec l'EXIF d'exposition recopié depuis les originaux (commande ci-dessus), puis fusionnés (*Photo → Fusion de photos → HDR*) : **import, fusion et affichage sans défaut constaté**. Cela valide la chaîne complète : export Lightroom (TIFF 16 bits, profil d'objectif activé) → *Hugin* (maître validé sur la vue centrée, dérivé à 7 expositions) → 7 calques → fusion HDR Lightroom. Le canal alpha (zones sans image) ne gêne pas Lightroom.

### J-11 — Ce qui restait à valider (fin de Phase 5)

*Origine : guide, Phase 5.*

### Ce qui reste à valider

Les finitions à pleine résolution ([T-09](TESTS-ANALYSES.md#t-09--finitions-à-pleine-résolution)), le coût de l'interface pendant *nona* ([T-14](TESTS-ANALYSES.md#t-14--coût-de-linterface-de-hugin-pendant-nona)) et un HDR plus large ([T-07](TESTS-ANALYSES.md#t-07--hdr-plus-large-que-20-000-px)) sont au [carnet](TESTS-ANALYSES.md).

### J-12 — Fenêtre à 100 % : résultat vérifié et mesures

*Origine : guide, étape **6B**.*

Résultat vérifié (maître optimisé sur l'export 2048) : 12 images, 547 points de contrôle conservés, chemins `..\..\..\Export-TIFF-H\L3_C22_E0.tif`. Le rendu se lance ensuite dans ***Hugin*** (ou directement avec ***nona*** puis ***enblend*** `--blend-colorspace=IDENTITY`) .

### J-13 — Fenêtre à 100 % : résultat mesuré

*Origine : guide, étape **6B**.*

**Résultat mesuré de la fenêtre A à 100 %** (12 images de 3456 × 5184 px, toile de 90 112 × 22 528 px, rendu direct avec ***nona*** puis ***enblend*** `--blend-colorspace=IDENTITY` ; le fichier final est un TIFF 16 bits LZW de 1 030 Mo à la taille de toute la toile, dont 129 Mpx seulement sont occupés) :

| Mesure | Valeur |
| --- | --- |
| ***nona*** | **605 s** (≈ 50 s par image) ; **13,7 Go de RAM** au pic, parce que chaque image reprojetée est écrite sur **toute la toile** (2 Gpx), pas rognée ; 12 fichiers intermédiaires, 2,0 Go en LZW |
| ***enblend*** | **272 s** (≈ 23 s par image) ; message `unable to run Dijkstra optimizer` sans gravité |
| Total | **14 min 40 s** |
| Netteté à 100 % | Détail de l'herbe, du tas de bois et de la bâche lisibles pixel par pixel (zone inspectée sur le fichier) |
| Trou 135-136 | **Bande noire de 144 px** à 100 % (colonnes 8 689 à 8 832 de la zone), soit environ 0,30° au pas de 487 px/° : exactement le recouvrement négatif mesuré dans le maître (−0,30°). **La géométrie du maître se transpose donc à la pleine taille sans dérive visible** ; les haies de part et d'autre du trou se prolongent, décalées de la largeur du trou |
| Autres raccords de la fenêtre | Aucun défaut visible à l'échelle de l'aperçu (toile de 16 300 × 8 100 px réduite à 1 800 px) |

**Second rendu, 2026-10-17** : mêmes 12 images, mais exportées depuis les **copies virtuelles retouchées** (étape **6A.1** : rendu propre et nettoyage des poussières), renommées par ***renommer_par_raw.py***, rendues avec ***nona*** puis ***multiblend*** :

| Mesure | Valeur |
| --- | --- |
| ***nona*** | **609 s** (≈ 51 s par image) ; **13,4 Go de RAM** au pic ; 12 intermédiaires, 1,76 Go |
| ***multiblend*** | **68 s** ; **6,1 Go de RAM** au pic ; code de sortie 0 ; intermédiaires supprimés |
| Total | **≈ 11 min 20 s** (contre 14 min 40 s avec *enblend*) ; panorama de 16 190 × 7 993 px (zone occupée), 907 Mo |
| Trou 135-136 | Bande vide de **140 à 145 px** dans le canal alpha (lignes y = 1 200 et 2 000 de la rangée L3) : identique au premier rendu ; **le projet maître reste valable** avec un nouvel export H |
| Netteté, raccords | Herbe et feuillage lisibles à 100 % (deux extraits de 1 200 × 800 px) ; aucune couture ni saut de tonalité sur l'aperçu à 1 800 px |

### J-14 — Affichage : ce qui a été vérifié sur ce panorama

*Origine : guide, Phase 7.*

**Vérifié sur ce panorama** : la pyramide complète s'ouvre, le zoom à 100 % charge les tuiles du niveau le plus fin et le rendu est net ; la mini-carte, l'indicateur de zoom et le tactile fonctionnent ; le trou connu (135-136) apparaît en bande noire. La fluidité a été jugée **parfaite** par l'utilisateur sur un hébergement mutualisé réel, avec les navigateurs *Firefox* (poste et téléphone) et *Chromium* ; *Safari* n'est pas essayé.

### J-15 — Superposition : ce qui a été jugé sur ce panorama

*Origine : guide, Phase 7.*

**Validé sur ce panorama** (jugement de l'utilisateur, à l'œil, avec les seuils par défaut) : l'alignement, le raccord de tonalité (« très bon ») et le fondu automatique (« fonctionne très bien »). Des seuils plus justes pour un autre panorama se règlent par `&z0=` et `&z1=`. Détail et limites : [T-04](TESTS-ANALYSES.md#t-04--superposition-du-hdr-et-de-la-pleine-résolution), [T-05](TESTS-ANALYSES.md#t-05--raccord-de-tonalité-entre-le-hdr-et-la-pleine-résolution), [T-11](TESTS-ANALYSES.md#t-11--fluidité-navigateurs-et-couleur-à-lœil), [T-17](TESTS-ANALYSES.md#t-17--fondu-automatique-selon-le-zoom-hdr--pleine-résolution).

### J-16 — Plugin Piwigo : état annoncé dans le guide

*Origine : guide, Phase 7.*

Il sera intégré à un plugin ***Piwigo*** à développer (issue de suivi du dépôt), à partir des choix tirés du banc d'essai : tuiles **servies en statique** (donc publiques par leur URL ; un contrôleur avec droits est à mesurer, [T-16](TESTS-ANALYSES.md#t-16--coût-dun-contrôleur-php-pour-servir-les-tuiles)), *OpenSeadragon* via le magasin d'actifs commun, panorama **rattaché à une photo**, import par dépôt manuel des pyramides puis déclaration dans l'administration, fondu automatique **par défaut et débrayable** par l'administrateur (seuils réglables, réglages globaux). Rien de tout cela n'est encore développé.

### J-17 — Statuts de phase (état au 2026-10-10)

*Origine : guide, lignes « Statut » des en-têtes de Phase 2 à 7.*

| **Statut** | ✅ Validé sur ce panorama |

| **Statut** | ✅ Validé sur ce panorama |

| **Statut** | ✅ Validé : géométrie transposée sans dérive à la pleine taille (fenêtre à 100 %) |

| **Statut** | ✅ Assemblage validé. Les finitions (**5D**) décrivent la retouche à faire ; elle n'a pas été menée à pleine résolution ([T-09](TESTS-ANALYSES.md#t-09--finitions-à-pleine-résolution)) |

| **Statut** | ✅ Validé à 20 000 px : 7 calques, fusion HDR dans *Lightroom* sans défaut constaté |

| **Statut** | ✅ **Fait** sur ce panorama : la géométrie du maître se transpose à la pleine taille (fenêtre à 100 %, **6B**), et le rendu complet des 222 images prend **≈ 3 h 35** (≈ 3 h 15 pour *nona*, 21 min pour *multiblend*) avec **13,5 Go de RAM** pour *nona*, **4 Go** pour *multiblend* grâce à un cache disque de ≈ 33 Go. **Reste** : les finitions (trous, bord supérieur, poussières) ; le tuilage est décrit en [Phase 7](../../docs/GUIDE.md#-phase-7--tuiler) |

| **Statut** | 🔬 **En cours.** Validé : le tuilage du panorama complet en **WebP** (1,80 Gpx : ≈ 1 min 50, 9 311 tuiles, 239 Mo) et l'affichage d'une pyramide de 507 Mpx. La pyramide complète s'ouvre dans la page autonome et charge ses tuiles en moins d'une seconde (essai local). **Validé sur ce panorama** : la superposition du HDR et de la pleine résolution (alignement à ±1 px HDR), le raccord de tonalité (jugé très bon à l'œil) et la **fluidité sur un hébergement réel** (jugée parfaite par l'utilisateur). **À démontrer** : les autres navigateurs et la charge à plusieurs visiteurs, puis l'intégration au plugin *Piwigo* (voir le [carnet](TESTS-ANALYSES.md)) |

### J-18 — Préréglages Lightroom : état au 2026-10-11

*Origine : guide, étapes **0C** et **2D** (réserve retirée du texte).*

Les trois préréglages de `lightroom/presets/` (export H, export L, développement) ont été **écrits à la main** d'après le format des préréglages Lightroom existants ; ils n'ont **pas encore été chargés dans Lightroom**. À vérifier au premier usage : réglages appliqués (profil, aberrations, 5 500 K / +10 ; ZIP, Adobe RGB, 2 048 px côté long pour L), dossier de destination. Les libellés de menus de l'étape **5C** (Synchroniser le dossier, mode Ajouter, export du TIFF HDR) suivent le comportement habituel de Lightroom Classic et sont également à confirmer au premier passage.

**Mise à jour du 2026-10-17** : ces fichiers écrits à la main sont **remplacés** par les préréglages réels de l'utilisateur, recopiés depuis son *Lightroom Classic* 15.4.1 (préréglages stockés avec le catalogue) : « PANO TIFF (H) E0 », « PANO TIFF (L) HDR » et le développement « PANO – 1DX + 70-200 II – WB 5500K » au format `.xmp`. Les deux exports passent en **Choisir le dossier ultérieurement**, avec les sous-dossiers `Export-TIFF-H` et `Export-TIFF-L`. **Vérifié** sur un essai de 3 copies virtuelles avec le préréglage H : 3456 × 5184 px, TIFF 16 bits Deflate, Adobe RGB, profil d'objectif, aucun recadrage, réglages identiques, renommage par RAW correct. **À vérifier** au prochain export L : la taille du côté long (le préréglage porte `size_maxHeight = 2048` et `size_maxWidth = 1000`, en mode « côté long »).
