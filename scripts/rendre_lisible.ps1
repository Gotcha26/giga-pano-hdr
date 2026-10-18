# Convertit un panorama rendu par multiblend (BigTIFF 16 bits RGBA, sans profil) en fichiers lisibles par Lightroom et les visionneuses.
#
# CONTEXTE
#     Etape 6B (fenetre a 100 %) et rendus de test. multiblend ecrit, avec -BigTiff, un BigTIFF que la plupart des
#     logiciels n'ouvrent pas (Photos de Windows, Lightroom), et il n'ecrit aucun profil de couleur : ouvert tel quel,
#     le panorama serait lu en sRGB (couleurs ternes). Pour juger un echantillon (par exemple les retouches faites dans
#     Lightroom, une fois assemblees), on en fait une copie lisible. Appele par rendre_projet.ps1 -Lisible, ou seul
#     sur un rendu existant.
#
# MODE OPERATOIRE
#     1. lit la taille du panorama (vipsheader) ; au-dela de 4 Go en RGB 16 bits non compresse (environ 700 Mpx),
#        s'arrete sans rien ecrire : ni le TIFF classique ni le JPEG ne le contiendraient (la pleine resolution se
#        regarde par extraits, vips crop, ou en apercu reduit, vips thumbnail) ;
#     2. aplatit la transparence sur noir et ecrit un TIFF CLASSIQUE 16 bits LZW : <nom>_lisible.tif ;
#     3. y copie le profil de couleur d'une image source (exiftool -icc_profile) : celle de -ProfilDepuis, sinon la
#        premiere image du projet -Projet ;
#     4. convertit en sRGB 8 bits : <nom>_sRGB.jpg (qualite 90), pour un coup d'oeil dans n'importe quel logiciel.
#
# ENTREES (parametres)
#     -Panorama       le TIFF rendu (BigTIFF ou classique), par exemple ...\rendu\fenetre_A_multiblend.tif
#     -ProfilDepuis   une image source dont copier le profil de couleur (ex. ...\Export-TIFF-H\L3_C22_E0.tif)
#     -Projet         a defaut de -ProfilDepuis : le projet .pto, dont la premiere image sert de source du profil
#     -Vips           executable vips (defaut D:\Outils\libvips\vips-dev-8.18\bin\vips.exe)
#     Programmes appeles : vips.exe et vipsheader.exe (variable $vips), exiftool (dans le PATH).
#
# SORTIES
#     A cote du panorama : <nom>_lisible.tif (TIFF classique 16 bits, Adobe RGB si les sources le sont, fond noir)
#     et <nom>_sRGB.jpg. Le panorama d'origine n'est pas modifie. Une ligne de bilan est affichee (et renvoyee).
#
# EXEMPLE
#     .\rendre_lisible.ps1 -Panorama "...\fenetre_A\rendu\fenetre_A_multiblend.tif" -Projet "...\fenetre_A\fenetre_A_5184.pto"
#
# (Fichier volontairement sans accents : il se lance aussi bien avec Windows PowerShell qu'avec PowerShell 7.)
param(
    [Parameter(Mandatory = $true)][string]$Panorama,
    [string]$ProfilDepuis = "",
    [string]$Projet = "",
    [string]$Vips = 'D:\Outils\libvips\vips-dev-8.18\bin\vips.exe'   # executable vips
)

$vips = $Vips
$vipsheader = Join-Path (Split-Path $vips) 'vipsheader.exe'

if (-not (Test-Path -LiteralPath $Panorama)) { throw "panorama introuvable : $Panorama" }
$largeur = [long](& $vipsheader -f width $Panorama)
$hauteur = [long](& $vipsheader -f height $Panorama)
$octets = $largeur * $hauteur * 3 * 2
if ($octets -ge 4GB) {
    return ("lisible ignore : {0} x {1} px ({2:N2} Gpx), trop grand pour un TIFF classique ; regarder par extraits (vips crop) ou en apercu (vips thumbnail)" -f $largeur, $hauteur, ($largeur * $hauteur / 1e9))
}

if (-not $ProfilDepuis) {
    if (-not $Projet) { throw "indiquer -ProfilDepuis ou -Projet (source du profil de couleur)" }
    $ligne = Select-String -LiteralPath $Projet -Pattern '^i .*n"([^"]+)"' | Select-Object -First 1
    if (-not $ligne) { throw "aucune image dans le projet : $Projet" }
    $image = $ligne.Matches[0].Groups[1].Value
    if ([IO.Path]::IsPathRooted($image)) { $ProfilDepuis = $image } else { $ProfilDepuis = Join-Path (Split-Path $Projet) $image }
}
if (-not (Test-Path -LiteralPath $ProfilDepuis)) { throw "source du profil introuvable : $ProfilDepuis" }

$dossier = Split-Path $Panorama
$nom = [IO.Path]::GetFileNameWithoutExtension($Panorama)
$tif = Join-Path $dossier "${nom}_lisible.tif"
$jpg = Join-Path $dossier "${nom}_sRGB.jpg"
$t = Get-Date

& $vips flatten $Panorama "${tif}[compression=lzw,predictor=horizontal]" --background "0,0,0"
if ($LASTEXITCODE -ne 0) { throw "vips flatten a echoue (code $LASTEXITCODE)" }
& exiftool -q -overwrite_original -TagsFromFile $ProfilDepuis -icc_profile $tif
if ($LASTEXITCODE -ne 0) { throw "exiftool n'a pas copie le profil (code $LASTEXITCODE)" }
& $vips icc_transform $tif "${jpg}[Q=90]" srgb --embedded --depth 8
if ($LASTEXITCODE -ne 0) { throw "vips icc_transform a echoue (code $LASTEXITCODE)" }

return ("lisible : {0} et {1} ({2} x {3} px, profil de {4}), {5:N0} s" -f (Split-Path $tif -Leaf), (Split-Path $jpg -Leaf), $largeur, $hauteur, (Split-Path $ProfilDepuis -Leaf), ((Get-Date) - $t).TotalSeconds)
