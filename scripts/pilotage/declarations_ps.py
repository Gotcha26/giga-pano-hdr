"""Déclarations d'arguments des scripts PowerShell, portées par le lanceur (les .ps1 n'ont pas de menu).

Un script PowerShell n'a que des paramètres nommés : chaque Arg commence par un tiret. Les chemins d'outils
(« outil:hugin », « outil:multiblend », « outil:vips ») sont préremplis d'après la configuration du poste ou la
détection. L'adaptateur enblend_vers_multiblend.ps1 n'est pas déclaré : c'est Hugin qui l'appelle.
"""

from .arguments import Arg

HUGIN = Arg("-Hugin", "Dossier bin de Hugin", type="dossier", config="outil:hugin")
MULTIBLEND = Arg("-Multiblend", "Exécutable multiblend", type="chemin", config="outil:multiblend")
VIPS = Arg("-Vips", "Exécutable vips", type="chemin", config="outil:vips")

PS = {
    "rendre_projet.ps1": ([
        Arg("-Projet", "Projet .pto à rendre (taille de panorama déjà réglée)", type="pto", phase="4_vue_centree", obligatoire=True),
        Arg("-Sortie", "Dossier de rendu (créé si besoin)", type="dossier", obligatoire=True),
        Arg("-Nom", "Nom du panorama produit, sans extension", defaut="panorama"),
        Arg("-Fusionneur", "enblend ou multiblend", defaut="multiblend"),
        Arg("-BigTiff", "nona --bigtiff : intermédiaires de plus de 4 Go (pleine résolution)", type="drapeau"),
        Arg("-CompressionEnblend", "lzw ou deflate : compression de sortie (lzw avec -BigTiff)"),
        Arg("-OptionsMultiblend", "Options ajoutées à multiblend, séparées par des espaces, ex. --cache-threshold=4G", type="liste"),
        Arg("-SansNona", "Réutilise les f_NNNN.tif déjà présents", type="drapeau"),
        Arg("-GarderIntermediaires", "Conserve les f_NNNN.tif après une fusion réussie", type="drapeau"),
        Arg("-Lisible", "Écrit aussi une copie lisible (TIFF classique + JPEG sRGB)", type="drapeau"),
        HUGIN, MULTIBLEND,
    ], "le dossier de rendu : panorama, journal ; supprime les intermédiaires après une fusion réussie"),
    "nona_images.ps1": ([
        Arg("-Projet", "Projet .pto à rendre", type="pto", phase="5_hdr", obligatoire=True),
        Arg("-Sortie", "Dossier de rendu (f_NNNN.tif)", type="dossier", obligatoire=True),
        Arg("-De", "Première image à rendre", type="entier", defaut=0),
        Arg("-A", "Dernière image à rendre (borne comprise)", type="entier", obligatoire=True),
        Arg("-BigTiff", "TIFF BigTIFF (image reprojetée de plus de 4 Go)", type="drapeau"),
        Arg("-IgnorerExposition", "nona --ignore-exposure : indispensable pour les calques HDR", type="drapeau"),
        HUGIN,
    ], "le dossier de rendu (f_NNNN.tif, rendu_log.txt) ; reprenable après interruption"),
    "fusionner_par_exposition.ps1": ([
        Arg("-Rendu", "Dossier des f_NNNN.tif", type="dossier", obligatoire=True),
        Arg("-Sortie", "Dossier des calques produits", type="dossier", obligatoire=True),
        Arg("-Fusionneur", "enblend ou multiblend", defaut="multiblend"),
        Arg("-Prefixe", "Début du nom des calques produits", defaut="pano_HDR"),
        Arg("-Expos", "Expositions par pile", type="entier", config="expos"),
        Arg("-Groupes", "Groupes à fusionner, séparés par des espaces (défaut : tous)", type="liste"),
        Arg("-OptionsFusionneur", "Options ajoutées au fusionneur, séparées par des espaces", type="liste"),
        Arg("-ExportExif", "Dossier de l'export L : EXIF et profil recopiés sur chaque calque", type="dossier", config="export_l"),
        HUGIN, MULTIBLEND,
    ], "les calques <Prefixe>_E*.tif et le journal dans le dossier de sortie"),
    "rendre_lisible.ps1": ([
        Arg("-Panorama", "Le TIFF rendu par multiblend (BigTIFF sans profil)", type="chemin", obligatoire=True),
        Arg("-ProfilDepuis", "Image source dont copier le profil de couleur", type="chemin", obligatoire=False),
        Arg("-Projet", "À défaut : le projet .pto, dont la première image sert de source du profil", type="pto", obligatoire=False),
        VIPS,
    ], "<nom>_lisible.tif et <nom>_sRGB.jpg à côté du panorama"),
    "surveiller_multiblend.ps1": ([
        Arg("-Sortie", "Fichier CSV des relevés (toutes les 20 s)", type="chemin", obligatoire=True),
    ], "le fichier de relevés"),
    "mesurer_charge.ps1": ([
        Arg("-Etiquette", "Nom de la mesure dans l'affichage", defaut="mesure"),
        Arg("-Duree", "Durée de la mesure, en secondes", type="entier", defaut=90),
        Arg("-Pas", "Intervalle entre deux relevés, en secondes", type="entier", defaut=3),
    ], None),
    "profil_jonction.ps1": ([
        Arg("-Rendu", "Dossier de rendu (f_NNNN.tif et fichier fusionné)", type="dossier", obligatoire=True),
        Arg("-Fusion", "Nom du fichier fusionné", obligatoire=True),
        Arg("-ImgA", "Première image source", type="entier", obligatoire=True),
        Arg("-ImgB", "Seconde image source", type="entier", obligatoire=True),
        Arg("-X0", "Coin haut gauche de la zone, en pixels de la toile", type="entier", obligatoire=True),
        Arg("-Y0", "Coin haut gauche de la zone, en pixels de la toile", type="entier", obligatoire=True),
        Arg("-W", "Largeur de la zone", type="entier", defaut=3000),
        Arg("-H", "Hauteur de la zone", type="entier", defaut=2800),
        Arg("-OrigX", "Origine X du fichier fusionné dans la toile", type="entier", obligatoire=True),
        Arg("-OrigY", "Origine Y du fichier fusionné dans la toile", type="entier", obligatoire=True),
        Arg("-Nom", "Préfixe des fichiers temporaires", defaut="jonction"),
    ], None),
    "tuiler.ps1": ([
        Arg("-Image", "TIFF géant à tuiler", type="chemin", obligatoire=True),
        Arg("-Sortie", "Préfixe de sortie : <Sortie>.dzi et <Sortie>_files", type="chemin", obligatoire=True),
        Arg("-ProfilEntree", "Profil ICC si le TIFF n'en porte pas (multiblend : donner Adobe RGB)", type="chemin"),
        Arg("-Format", "webp ou jpg", defaut="webp"),
        Arg("-Qualite", "Qualité des tuiles", type="entier", defaut=85),
        Arg("-Tuile", "Taille des tuiles, en pixels", type="entier", defaut=512),
        VIPS,
    ], "la pyramide <Sortie>.dzi et le dossier <Sortie>_files"),
}
