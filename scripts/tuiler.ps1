# Tuile une image geante (TIFF) en pyramide Deep Zoom avec libvips.
# Valide sur la vue centree a 45 056 px et sur le panorama complet a 88 658 x 20 312 px (62 s, voir T-10).
#
# Usage : .\tuiler.ps1 -Image "...\ligne_L3.tif" -Sortie ".\tuiles\ligne_L3" [-Vips "D:\Outils\libvips\vips-dev-8.18\bin\vips.exe"] [-ProfilEntree "...\AdobeRGB.icc"]
# Le panorama fusionne par multiblend ne porte AUCUN profil : sans -ProfilEntree, la conversion vers sRGB n'a pas lieu
# et la pleine resolution parait plus terne que le HDR (qui, lui, porte Adobe RGB).
#
# Produit <Sortie>.dzi et le dossier <Sortie>_files\ (tuiles JPEG), en deux temps :
# 1. vips icc_transform : Adobe RGB (profil integre au TIFF) -> sRGB, 16 -> 8 bits, dans un fichier
#    temporaire <Sortie>_srgb.v (non compresse : largeur x hauteur x 4 octets, ex. 2 Go a 45 056 px,
#    8 Go a 90 112 px). L'option --profile de dzsave ne fait qu'integrer un profil sans convertir les
#    pixels : elle ne convient pas.
# 2. vips dzsave : pyramide ; le canal alpha est aplati sur noir (parties vides en noir) : par dzsave en JPEG (defaut),
#    par une etape `vips flatten` en WebP (-Format webp), qui garderait sinon l'alpha (halo vert au bord des trous).
# Releve la duree et le pic de memoire de chaque etape dans <Sortie>_log.txt.
param(
    [Parameter(Mandatory = $true)][string]$Image,
    [Parameter(Mandatory = $true)][string]$Sortie,
    [string]$Vips = 'D:\Outils\libvips\vips-dev-8.18\bin\vips.exe',
    [string]$ProfilEntree = '',   # profil ICC a appliquer si le TIFF n'en porte pas (multiblend n'ecrit aucun profil : donner Adobe RGB)
    [int]$Tuile = 512,
    [int]$Qualite = 85,
    [ValidateSet('jpg', 'webp')][string]$Format = 'webp'   # webp Q85 retenu (2 fois plus leger que jpg Q90) ; jpg : -Format jpg -Qualite 90. Le canal alpha est aplati sur noir dans les deux cas
)

New-Item -ItemType Directory (Split-Path -Parent $Sortie) -Force | Out-Null
$log = "${Sortie}_log.txt"
$tmp = "${Sortie}_srgb.v"
"debut : $(Get-Date -Format s)  image : $Image" | Out-File $log -Encoding utf8

function Lancer([string]$etape, [string[]]$arguments) {
    $t = Get-Date
    $p = Start-Process -FilePath $Vips -ArgumentList $arguments -NoNewWindow -PassThru
    $null = $p.Handle   # sans cette lecture, ExitCode peut rester vide une fois le processus termine
    $pic = 0
    while (-not $p.HasExited) {
        $p.Refresh()
        if ($p.WorkingSet64 -gt $pic) { $pic = $p.WorkingSet64 }
        Start-Sleep -Seconds 2
    }
    ("{0} : {1:N0} s, pic de RAM {2:N1} Go, code de sortie {3}" -f $etape, ((Get-Date) - $t).TotalSeconds, ($pic / 1GB), $p.ExitCode) |
        Out-File $log -Append -Encoding utf8
    return $p.ExitCode
}

$argsIcc = @('icc_transform', "`"$Image`"", "`"$tmp`"", 'srgb', '--embedded', '--depth', 8)
if ($ProfilEntree) { $argsIcc += @('--input-profile', "`"$ProfilEntree`"") }   # sert seulement si aucun profil n'est integre
$code = Lancer 'icc_transform' $argsIcc
$aDiffuser = $tmp
if ($code -eq 0) {
    ("fichier temporaire : {0:N0} Mo" -f ((Get-Item $tmp).Length / 1MB)) | Out-File $log -Append -Encoding utf8
    # Seulement si l'image a un canal alpha (4 bandes) : sur une image RGB a 3 bandes, flatten prendrait le bleu pour un alpha.
    $bandes = (& (Join-Path (Split-Path -Parent $Vips) 'vipsheader.exe') -f bands $tmp)
    if ($Format -eq 'webp' -and "$bandes".Trim() -eq '4') {
        # Le WebP garde l'alpha : sans aplatissement, les bords partiellement transparents laissent voir un halo vert vif
        # (surdepassement de la fusion) et les trous laissent voir le HDR dessous. On aplatit sur noir, comme le fait le JPEG.
        $tmpPlat = "${Sortie}_plat.v"
        $code = Lancer 'flatten' @('flatten', "`"$tmp`"", "`"$tmpPlat`"", '--background', 0)
        if ($code -eq 0) { $aDiffuser = $tmpPlat }
    }
    if ($code -eq 0) {
        $null = Lancer 'dzsave' @('dzsave', "`"$aDiffuser`"", "`"$Sortie`"", '--tile-size', $Tuile, '--overlap', 0,
                                   '--suffix', "`".$Format[Q=$Qualite]`"", '--background', 0)
    }
}
Remove-Item $tmp -ErrorAction SilentlyContinue
Remove-Item "${Sortie}_plat.v" -ErrorAction SilentlyContinue

$nb = (Get-ChildItem "${Sortie}_files" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
$mo = (Get-ChildItem "${Sortie}_files" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB
("{0} tuiles, {1:N0} Mo" -f $nb, $mo) | Out-File $log -Append -Encoding utf8
Get-Content $log
