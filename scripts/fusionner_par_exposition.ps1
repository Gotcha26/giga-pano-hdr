# Fusionne, avec enblend ou multiblend, les images reprojetees par nona (f_NNNN.tif) en un panorama PAR EXPOSITION :
# les images dont le numero modulo -Expos vaut k forment le groupe k (E0 .. E6), comme les calques de Hugin
# (" calques raccordes ayant une exposition similaire "). Produit les 7 calques d'un HDR a importer dans Lightroom ; permet
# aussi de comparer les deux fusionneurs (issue #31).
# (Fichier volontairement sans accents : il se lance aussi bien avec Windows PowerShell qu'avec PowerShell 7.)
#
# Contexte : un projet HDR a 7 expositions groupees en piles (generer_pto_hdr.py, propager_geometrie.py) numerote
# ses images pile par pile, E0 a E6 ; le groupe d'exposition k est donc l'ensemble des images de rang k modulo 7.
# Les f_NNNN.tif sont ceux de nona_images.ps1 (ou de rendre_projet.ps1 -GarderIntermediaires).
# IMPORTANT : pour un HDR, les rendre avec nona_images.ps1 -IgnorerExposition (nona --ignore-exposure), comme le fait
# Hugin pour ses calques sans correction d'exposition. Sinon nona ramene toutes les expositions au meme niveau
# et sature les images : les groupes sortent blancs et identiques.
#
# Mode operatoire : pour chaque groupe, lance le fusionneur, releve la duree, le pic de memoire du processus et la
# RAM libre minimale du systeme, et ecrit <Prefixe>_E<k>.tif dans le dossier -Sortie. Rien n'est supprime.
#
# Entrees (parametres) :
#   -Rendu        dossier des f_NNNN.tif
#   -Sortie       dossier des panoramas produits (cree si besoin)
#   -Fusionneur   enblend (defaut : --blend-colorspace=IDENTITY, la reference) ou multiblend
#   -Prefixe      debut du nom des fichiers produits (defaut : le nom du fusionneur)
#   -Expos        nombre d'expositions par pile (defaut 7)
#   -Groupes      numeros de groupes a fusionner (defaut : tous, 0 a Expos-1)
#   -OptionsFusionneur  options ajoutees au fusionneur, ex. "--wideblend" pour multiblend
#   -ExportExif   dossier des TIFF L_C_E de l'export L : pour chaque groupe k, recopie sur le panorama produit l'EXIF
#                 d'exposition ET le profil de couleur (Adobe RGB) de L0_C00_E<k>.tif, avec exiftool. Indispensable pour
#                 un HDR : multiblend n'ecrit aucun profil, et Lightroom classe les expositions d'apres l'EXIF.
#   Programmes appeles : C:\Program Files\Hugin\bin\enblend.exe, D:\Outils\multiblend\multiblend.exe (variables
#   $enblend, $multiblend, en tete de script).
#
# Sorties : <Sortie>\<Prefixe>_E0.tif ... et <Sortie>\<Prefixe>_log.txt (une ligne par groupe : images, duree,
# pic de RAM du processus, RAM libre minimale, code de sortie, taille du fichier). Le journal est aussi affiche.
# Attention : multiblend ecrit la boite englobante des images, pas la toile entiere (voir son TIFF avec vipsheader).
#
# Exemple : .\fusionner_par_exposition.ps1 -Rendu "...\rendu" -Sortie "...\fusion" -Fusionneur multiblend
param(
    [Parameter(Mandatory = $true)][string]$Rendu,
    [Parameter(Mandatory = $true)][string]$Sortie,
    [ValidateSet('enblend', 'multiblend')][string]$Fusionneur = 'enblend',
    [string]$Prefixe = '',
    [int]$Expos = 7,
    [int[]]$Groupes = @(),
    [string[]]$OptionsFusionneur = @(),
    [string]$ExportExif = ''
)

$enblend = 'C:\Program Files\Hugin\bin\enblend.exe'
$multiblend = 'D:\Outils\multiblend\multiblend.exe'
if (-not $Prefixe) { $Prefixe = $Fusionneur }
if ($Groupes.Count -eq 0) { $Groupes = 0..($Expos - 1) }
New-Item -ItemType Directory $Sortie -Force | Out-Null
$log = Join-Path $Sortie "${Prefixe}_log.txt"
"debut : $(Get-Date -Format s)  fusionneur : $Fusionneur $($OptionsFusionneur -join ' ')  rendu : $Rendu" | Out-File $log -Encoding utf8

$images = Get-ChildItem $Rendu -Filter 'f_*.tif' | Sort-Object Name
foreach ($g in $Groupes) {
    $groupe = @($images | Where-Object { ([int]($_.BaseName -replace '^f_', '')) % $Expos -eq $g })
    if ($groupe.Count -eq 0) { "groupe $g : aucune image" | Out-File $log -Append -Encoding utf8; continue }
    $sortieTif = Join-Path $Sortie "${Prefixe}_E$g.tif"
    if ($Fusionneur -eq 'multiblend') {
        $exe = $multiblend
        $arguments = @('--compression=LZW') + $OptionsFusionneur + @('-o', "`"$sortieTif`"") + ($groupe | ForEach-Object { $_.Name })
        $dossier = $Rendu
    } else {
        $liste = Join-Path $Sortie "${Prefixe}_liste_E$g.txt"
        $groupe | ForEach-Object { $_.FullName } | Out-File $liste -Encoding ascii      # un chemin par ligne, sans guillemets
        $exe = $enblend
        $arguments = @('--blend-colorspace=IDENTITY', '--compression=LZW') + $OptionsFusionneur + @('-o', "`"$sortieTif`"", "`"@$liste`"")
        $dossier = $null
    }
    $demarrage = @{ FilePath = $exe; ArgumentList = $arguments; NoNewWindow = $true; PassThru = $true }
    if ($dossier) { $demarrage.WorkingDirectory = $dossier }
    $t = Get-Date
    $p = Start-Process @demarrage
    $null = $p.Handle   # sans cette lecture, ExitCode peut rester vide une fois le processus termine
    $pic = 0
    $libreMin = [double]::MaxValue
    while (-not $p.HasExited) {
        $p.Refresh()
        if ($p.WorkingSet64 -gt $pic) { $pic = $p.WorkingSet64 }
        $libre = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
        if ($libre -lt $libreMin) { $libreMin = $libre }
        Start-Sleep -Seconds 2
    }
    $taille = if (Test-Path -LiteralPath $sortieTif) { (Get-Item -LiteralPath $sortieTif).Length / 1MB } else { 0 }
    ("groupe E{0} : {1} images, {2:N0} s, pic de RAM {3:N1} Go, RAM libre minimale {4:N1} Go, code {5}, {6:N0} Mo" -f `
        $g, $groupe.Count, ((Get-Date) - $t).TotalSeconds, ($pic / 1GB), $libreMin, $p.ExitCode, $taille) |
        Out-File $log -Append -Encoding utf8
    if ($ExportExif -and $p.ExitCode -eq 0 -and (Test-Path -LiteralPath $sortieTif)) {
        $modele = Join-Path $ExportExif ('L0_C00_E{0}.tif' -f $g)
        & exiftool -q -overwrite_original -TagsFromFile $modele -ExposureTime -FNumber -ISO -ExposureCompensation `
            -FocalLength -FocalLengthIn35mmFormat -ExposureProgram -ExposureMode -MeteringMode -ShutterSpeedValue `
            -ApertureValue -LensModel -icc_profile $sortieTif
        "groupe E$g : EXIF et profil de couleur recopies depuis $modele (code $LASTEXITCODE)" | Out-File $log -Append -Encoding utf8
    }
}
"fin : $(Get-Date -Format s)" | Out-File $log -Append -Encoding utf8
Get-Content $log
