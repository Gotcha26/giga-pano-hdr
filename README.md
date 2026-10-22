# giga-pano-hdr

Méthode, scripts et étude de cas pour assembler un **giga-panorama HDR** pris en grille à la rotule : géométrie dans ***Hugin***, fusion par ***multiblend***, HDR dans ***Lightroom***, pleine résolution en BigTIFF, pyramides de tuiles avec ***libvips***. Windows, PowerShell et Python.

---

## 📋 Pour qui ?

- Photographes qui prennent un panorama de **plusieurs centaines d'images** en grille régulière (lignes × colonnes, plusieurs expositions par position).
- Ceux dont le panorama à 100 % **dépasse ce qu'un logiciel grand public sait ouvrir** (plus de 500 Mpx, plusieurs Go) et qui veulent quand même le montrer, zoomable jusqu'au pixel.
- Ceux qui ont de grandes zones de **ciel uniforme**, où l'assistant de ***Hugin*** se perd.

## 🤚 Ce que ça ne fait PAS

- Ça n'assemble pas tout seul : la méthode enchaîne ***Lightroom***, ***Hugin***, des scripts et ***libvips***, avec des contrôles entre chaque étape.
- Ça ne comble pas un trou de prise de vue et ne remplace pas une prise de vue soignée.
- Ça s'arrête aux tuiles : afficher et publier dépend de la visionneuse choisie.

---

## ✨ Trois choses, bien séparées

```mermaid
flowchart LR
    G["docs/GUIDE.md<br/>la méthode générale"] --> S["scripts/<br/>les outils, par étape"]
    G --> E["etudes-de-cas/<br/>la méthode appliquée, chiffrée"]
    S --> E
```

| Vous voulez… | Ouvrez |
| --- | --- |
| **Comprendre et refaire** la méthode, phase par phase, sans les chiffres d'un panorama précis | [`docs/GUIDE.md`](docs/GUIDE.md) |
| **Voir ce que ça donne en vrai** :<ul><li>222 positions × 7 expositions</li><li>200 mm</li><li>Durées</li><li>RAM</li><li>Tailles</li><li>Incidents</li></ul> | [`etudes-de-cas/2026-06-19-wattenberg-200mm/ETUDE-DE-CAS.md`](etudes-de-cas/2026-06-19-wattenberg-200mm/ETUDE-DE-CAS.md) |
| Les **mesures, hypothèses et décisions** de cette étude de cas | [`…/TESTS-ANALYSES.md`](etudes-de-cas/2026-06-19-wattenberg-200mm/TESTS-ANALYSES.md) |
| **Quel script pour quelle étape**, et sa portée (générique ou paramétré par la grille) | [`scripts/INDEX.md`](scripts/INDEX.md) |

Le guide donne la **procédure** et ses raisons. L'étude de cas donne les **valeurs** (grille, pas, tailles d'export, noms de fichiers) et ce qui a été **mesuré** (durées, RAM, disque, défauts). Les deux suivent la même numérotation d'étapes (**3E**, **6C.4**…), que les scripts citent aussi.

---

## 🚀 Démarrage rapide

1. Cloner ce dépôt et ouvrir le **lanceur** depuis `scripts\` :
   ```powershell
   cd D:\Depots\giga-pano-hdr\scripts
   python panorama.py
   ```
   Menu **Préparer** : il affiche les versions de ***Hugin***, ***multiblend***, ***Python*** (+ ***Pillow***), ***ExifTool***, ***libvips***, propose d'installer ce qui manque, et crée l'arborescence d'un **nouveau panorama**. Les autres menus suivent les phases du guide et ouvrent chaque script avec ses arguments préremplis.
   1 bis. Ou l'**interface web** : `pip install nicegui` puis `python panorama_web.py` (depuis `scripts\`). ***NiceGUI*** s'installe dans les paquets de l'utilisateur : lancer avec `python` simple, pas `python -I`, qui les ignore.
2. Un script se lance aussi seul : **sans argument** dans un terminal, il affiche le menu de ses arguments ; **avec des arguments**, il fait ce que dit le guide :
   ```powershell
   python verifier_ordre.py "$T\Export-TIFF-L" --grille <lignes> <colonnes>
   ```
3. Suivre le [guide](docs/GUIDE.md) dans l'ordre, ou aller droit à l'[aide-mémoire](docs/GUIDE.md#aide-mémoire--la-séquence-complète) pour la séquence complète des commandes.

---

## 📁 Structure du dépôt

```
giga-pano-hdr\
├── README.md                              ← ce fichier : l'aiguillage
├── LICENSE, LICENSE-docs                  ← MIT (scripts), CC BY 4.0 (documentation)
├── docs\
│   ├── GUIDE.md                           ← la méthode générale (phases 0 à 7)
│   └── NETTOYAGE-ancien-depot.md          ← à faire dans l'ancien dépôt, après la clôture de son issue #46
├── scripts\                               ← 46 scripts .py / .ps1 / .cmd et les lanceurs, un dossier (ils s'appellent entre eux)
│   ├── panorama.py                        ← le lanceur : menus par phase, Phase 0 outillée
│   ├── pilotage\                          ← kit partagé : couleurs, menus, configuration, outils, arguments
│   └── INDEX.md                           ← quel script pour quoi, portée de chacun
├── tests\                                 ← tests unitaires des scripts qui ont des fonctions pures
└── etudes-de-cas\
    └── 2026-06-19-wattenberg-200mm\       ← un dossier par panorama étudié
        ├── ETUDE-DE-CAS.md                ← la méthode appliquée, phase par phase
        ├── TESTS-ANALYSES.md              ← le carnet : M-xx, T-xx, P-xx, D-xx, J-xx
        ├── donnees\table_raw_LCE.csv      ← correspondance RAW → L_C_E
        └── lightroom\presets\             ← les préréglages Lightroom qui ont servi
```

---

## 🛠️ Tests et garde-fous

```powershell
python -I -m unittest discover -s tests -v     # kit de pilotage, lanceur, scripts pilotés, fonctions pures des scripts de contrôle
python scripts\verifier_renvois.py             # numérotation du guide : identifiants cités, liens internes, restes de l'ancien système (0 écart attendu)
```

---

## 📚 Pour aller plus loin

- La visionneuse qui affiche ces panoramas est un autre projet (plugin ***Piwigo*** *GigaPanoramaViewer*) ; ce dépôt n'en dépend pas.
- Le lanceur et les menus de pilotage ne font qu'**orienter et préremplir** : les scripts restent pilotables en ligne de commande, et le guide reste la référence ([Configuration : les scripts](docs/GUIDE.md#️-configuration--les-scripts)).

---

## 👏 Crédits

Julien Moreau, avec ***Claude Code***. Les logiciels tiers (***Hugin***, ***multiblend***, ***libvips***, ***ExifTool***, ***OpenSeadragon***) appartiennent à leurs auteurs.

---

## 📜 Licence

Libre, avec citation de l'auteur et de la source :

| Contenu | Licence | En clair |
| --- | --- | --- |
| Scripts (`scripts/`, `tests/`) | [MIT](LICENSE) | Utilisez, modifiez, redistribuez<br>conservez la mention de copyright |
| Documentation (`docs/`, `etudes-de-cas/`, ce README) | [CC BY 4.0](LICENSE-docs) | Partagez, adaptez<br>créditez Julien Moreau et pointez vers ce dépôt |

---

**Version** : 1.1
**Dernière mise à jour** : 2026-10-18
