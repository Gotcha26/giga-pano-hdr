"""Produit une image qui exagère les petites variations de tonalité d'un rendu (pour voir les « tranches »).

CONTEXTE
    Étape 3F (vignettage). Les scripts de mesure donnent des chiffres ; celui-ci montre à l'œil ce qu'ils
    mesurent : les raccords entre images, invisibles en tonalité normale, apparaissent en grille.

MODE OPÉRATOIRE
    Recadre la zone, la compare à une version très floue (qui retire les grandes variations naturelles du ciel),
    multiplie la différence par un gain autour du gris moyen (128), puis réduit à la largeur demandée.

ENTRÉES
    rendu.tif         panorama assemblé
    sortie.png        image à écrire
    X0 X1 Y0 Y1       zone à rehausser, en pixels
    GAIN              facteur d'amplification (défaut 20)
    RAYON_FLOU        rayon du flou gaussien, en pixels (défaut 60)
    LARGEUR_SORTIE    largeur de l'image produite, en pixels (défaut 1800)

SORTIES
    sortie.png (RVB, gris moyen = pas d'écart) + message « sortie écrit (L x H) ».

EXEMPLE
    python rehausser_ciel.py rendu.tif ciel_rehausse.png 1600 4400 160 220 20 60 1800

Dépendance : Pillow.

Usage : python rehausser_ciel.py rendu.tif sortie.png X0 X1 Y0 Y1 [GAIN=20] [RAYON_FLOU=60] [LARGEUR_SORTIE=1800]
"""
import sys

from PIL import Image, ImageChops, ImageFilter

Image.MAX_IMAGE_PIXELS = None
f, sortie = sys.argv[1], sys.argv[2]
x0, x1, y0, y1 = (int(v) for v in sys.argv[3:7])
gain = float(sys.argv[7]) if len(sys.argv) > 7 else 20.0
rayon = float(sys.argv[8]) if len(sys.argv) > 8 else 60.0
largeur = int(sys.argv[9]) if len(sys.argv) > 9 else 1800

im = Image.open(f).convert("RGB").crop((x0, y0, x1, y1))
flou = im.filter(ImageFilter.GaussianBlur(rayon))
# (im - flou) * gain + 128, canal par canal
diff = ImageChops.subtract(im, flou, scale=1.0 / gain, offset=128)
h = round(diff.height * largeur / diff.width)
diff.resize((largeur, h), Image.LANCZOS).save(sortie)
print(f"{sortie} écrit ({largeur} x {h})")
