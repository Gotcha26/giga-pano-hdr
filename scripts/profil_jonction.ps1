# Profil vertical d'une jonction entre deux images, par bandes de 50 lignes : compare le panorama fusionne (multiblend) aux deux images sources reprojetees.
#
# CONTEXTE
#     Phase 6 (controle de la fusion). Permet de verifier objectivement une jonction : hors du recouvrement, le
#     fichier fusionne doit coller a la source seule (cela valide l'origine OrigX/OrigY) ; dans le recouvrement, un
#     ecart anormal repere un halo ou un decalage de tonalite.
#
# MODE OPERATOIRE
#     Recadre la meme zone de la toile dans le fichier fusionne et dans les deux images reprojetees (f_NNNN.tif de
#     nona), isole l'alpha et la bande bleue, moyenne par bandes de 50 lignes (avec libvips), puis compare.
#     Les positions utiles des images se lisent avec : vips find_trim "f_NNNN.tif[page=0]" --background 0 --threshold 1
#     (gauche, haut, largeur, hauteur ; les intermediaires de nona sont des toiles entieres, sans decalage dans le TIFF).
#
# ENTREES (parametres)
#     -Rendu     dossier de rendu (contient les f_NNNN.tif et le fichier fusionne)
#     -Fusion    nom du fichier fusionne (ex. lignes_L0-L2_multiblend.tif)
#     -ImgA, -ImgB   numeros des deux images sources (f_NNNN.tif)
#     -X0, -Y0   coin haut gauche de la zone, en pixels DE LA TOILE (la toile du projet, 90 112 x 22 528)
#     -W, -H     largeur et hauteur de la zone, en pixels (defauts 3000 et 2800)
#     -OrigX, -OrigY   coin haut gauche du fichier fusionne dans la toile (boite englobante de toutes les images :
#                le plus petit bord gauche et le plus petit haut). Un panorama de 360 degres peut passer d'un bord a l'autre.
#     -Nom       prefixe des fichiers temporaires (defaut "jonction")
#     Programme appele : D:\Outils\libvips\vips-dev-8.18\bin\vips.exe (variable $v, en tete de script).
#
# SORTIES
#     A l'ecran : un tableau ";" par bande (numero, y dans la toile, couverture de A et de B en %, valeur moyenne de la
#     bande bleue sur 65 535 du fichier fusionne et des deux sources, ecart du fichier fusionne a chaque source en %).
#     Les fichiers intermediaires vont dans %TEMP%\profil_jonction.
#
# PIEGE
#     Sur ce poste, libvips lit les nombres avec la virgule decimale ; ne lui passer que des entiers.
#
# EXEMPLE
#     .\profil_jonction.ps1 -Rendu "...\rendu" -Fusion lignes_L0-L2_multiblend.tif -ImgA 12 -ImgB 49 `
#         -X0 59711 -Y0 4224 -W 3000 -H 2800 -OrigX 2146 -OrigY 1111
#
# (Fichier volontairement sans accents : il se lance aussi bien avec Windows PowerShell qu'avec PowerShell 7.)
param(
    [Parameter(Mandatory = $true)][string]$Rendu,
    [Parameter(Mandatory = $true)][string]$Fusion,
    [Parameter(Mandatory = $true)][int]$ImgA,
    [Parameter(Mandatory = $true)][int]$ImgB,
    [Parameter(Mandatory = $true)][int]$X0,
    [Parameter(Mandatory = $true)][int]$Y0,
    [int]$W = 3000,
    [int]$H = 2800,
    [Parameter(Mandatory = $true)][int]$OrigX,
    [Parameter(Mandatory = $true)][int]$OrigY,
    [string]$Nom = 'jonction'
)
$S = Join-Path $env:TEMP 'profil_jonction'
New-Item -ItemType Directory -Force $S | Out-Null
$v = 'D:\Outils\libvips\vips-dev-8.18\bin\vips.exe'
$bande = 50
$n = [math]::Floor($H / $bande)

function Lire-Colonne($csv) {
    return @(Get-Content $csv | ForEach-Object { [double](($_ -split '\t|;')[0] -replace ',', '.') })
}

function Profil($fichier, $x, $y, $etiquette) {
    # recadre, separe alpha et couleur, moyenne par bande de la couleur masquee et du masque
    $c = "$S\${Nom}_${etiquette}_crop.v"
    & $v extract_area $fichier $c $x $y $W $H
    $alpha = "$S\${Nom}_${etiquette}_a.v"
    & $v extract_band $c $alpha 3
    $masque = "$S\${Nom}_${etiquette}_m.v"
    & $v relational_const $alpha $masque more 0          # 0 ou 255
    $res = @{}
    foreach ($b in 0, 2) {
        $bd = "$S\${Nom}_${etiquette}_b$b.v"
        & $v extract_band $c $bd $b
        $pm = "$S\${Nom}_${etiquette}_pm$b.v"
        & $v multiply $bd $masque $pm                     # couleur x (0 ou 255)
        & $v shrink $pm "$S\${Nom}_${etiquette}_s$b.v" $W $bande
        & $v csvsave "$S\${Nom}_${etiquette}_s$b.v" "$S\${Nom}_${etiquette}_pm$b.csv"
        $res["c$b"] = Lire-Colonne "$S\${Nom}_${etiquette}_pm$b.csv"
    }
    & $v shrink $masque "$S\${Nom}_${etiquette}_sm.v" $W $bande
    & $v csvsave "$S\${Nom}_${etiquette}_sm.v" "$S\${Nom}_${etiquette}_sm.csv"
    $res["m"] = Lire-Colonne "$S\${Nom}_${etiquette}_sm.csv"
    return $res
}

$po = Profil "$Rendu\$Fusion" ($X0 - $OrigX) ($Y0 - $OrigY) 'out'
$pa = Profil ("$Rendu\" + ('f_{0:D4}.tif' -f $ImgA)) $X0 $Y0 'a'
$pb = Profil ("$Rendu\" + ('f_{0:D4}.tif' -f $ImgB)) $X0 $Y0 'b'

"bande ; y_toile ; couverture A % ; couverture B % ; sortie (bleu) ; A ; B ; ecart sortie-A % ; ecart sortie-B %"
for ($i = 0; $i -lt $n; $i++) {
    $cm = $po.m[$i]; $am = $pa.m[$i]; $bm = $pb.m[$i]
    $so = if ($cm -gt 0) { $po.c2[$i] / $cm } else { [double]::NaN }
    $sa = if ($am -gt 0) { $pa.c2[$i] / $am } else { [double]::NaN }
    $sb = if ($bm -gt 0) { $pb.c2[$i] / $bm } else { [double]::NaN }
    $ea = if ($am -gt 200) { ($so - $sa) / $sa * 100 } else { [double]::NaN }
    $eb = if ($bm -gt 200) { ($so - $sb) / $sb * 100 } else { [double]::NaN }
    "{0} ; {1} ; {2:N0} ; {3:N0} ; {4:N0} ; {5:N0} ; {6:N0} ; {7:N2} ; {8:N2}" -f $i, ($Y0 + $i * $bande), ($am / 2.55), ($bm / 2.55), $so, $sa, $sb, $ea, $eb
}
