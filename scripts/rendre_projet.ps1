# Rend un projet Hugin (.pto) avec nona puis enblend (ou multiblend), en chronometrant chaque etape et en relevant le pic de RAM de chaque programme.
#
# CONTEXTE
#     Phase 6 (pleine resolution) et tests de rendu. Enchaine la reprojection (nona) et la fusion, sans passer par
#     l'interface de Hugin. enblend n'ecrit pas plus de 4 Go (M-06) ; multiblend ecrit du BigTIFF (M-07) : pour la
#     pleine resolution on utilise -Fusionneur multiblend. Attention : multiblend n'a pas d'equivalent a
#     --blend-colorspace=IDENTITY, ce reglage ne s'applique qu'a enblend.
#
# MODE OPERATOIRE
#     1. nona reprojette chaque image sur la toile du projet : f_NNNN.tif dans le dossier Sortie (saute avec -SansNona) ;
#     2. le fusionneur assemble ces images en <Nom>.tif. Le fichier de reponse d'enblend (liste_enblend.txt) evite la
#        limite de longueur de ligne de commande de Windows (erreur 206) avec beaucoup d'images ; multiblend recoit
#        la liste en ligne de commande (noms relatifs) ;
#     3. nettoyage (PAR DEFAUT) : une fois le panorama ecrit, les f_NNNN.tif (ex. 8,9 Go pour 222 images a 45 056 px)
#        et liste_enblend.txt sont supprimes. Securite : rien n'est supprime si le fusionneur n'a pas rendu le code 0
#        ou si le panorama est absent ou vide.
#
# ENTREES (parametres)
#     -Projet                  projet Hugin (.pto) a rendre
#     -Sortie                  dossier de rendu (cree si besoin)
#     -Nom                     nom du panorama produit, sans extension (defaut "panorama")
#     -BigTiff                 nona --bigtiff : intermediaires > 4 Go (pleine resolution)
#     -CompressionEnblend      "lzw" ou "deflate" : force la compression de sortie du fusionneur
#     -Fusionneur              enblend (defaut) ou multiblend (D:\Outils\multiblend\multiblend.exe)
#     -OptionsMultiblend       options ajoutees a multiblend, ex. "--cache-threshold=12G" (memoire au-dela de 12 Go sur disque)
#     -SansNona                reutilise les f_NNNN.tif deja presents (comparer deux fusionneurs sans refaire nona)
#     -GarderIntermediaires    conserve f_NNNN.tif et liste_enblend.txt apres une fusion reussie, pour relancer le
#                              fusionneur avec d'autres options sans refaire nona (47 min pour 222 images a 45 056 px)
#     -NettoyerIntermediaires  obsolete : encore accepte, sans effet
#     -Lisible                 apres une fusion reussie, ecrit aussi une copie lisible du panorama (TIFF classique 16 bits
#                              avec le profil de couleur des images, et JPEG sRGB) par rendre_lisible.ps1 ; ignore au-dela
#                              d'environ 700 Mpx (fenetres et echantillons seulement, pas la pleine resolution)
#     Programmes appeles : C:\Program Files\Hugin\bin\nona.exe et enblend.exe ; multiblend (variables $hb, $multiblend).
#
# SORTIES
#     Dans le dossier Sortie : le panorama <Nom>.tif (taille de la TOILE du projet, ligne p) et rendu_log.txt (durees,
#     pics de RAM, codes de sortie, bilan du nettoyage). Le journal est aussi affiche a la fin.
#     Avec -GarderIntermediaires : en plus les f_NNNN.tif et liste_enblend.txt.
#     Avec -Lisible : en plus <Nom>_lisible.tif et <Nom>_sRGB.jpg.
#
# EXEMPLE
#     .\rendre_projet.ps1 -Projet "...\fenetre.pto" -Sortie "...\rendu" -Nom "fenetre" -GarderIntermediaires
#     .\rendre_projet.ps1 -Projet "...\fenetre_A_5184.pto" -Sortie "...\rendu" -Nom fenetre_A_multiblend -BigTiff `
#         -CompressionEnblend lzw -Fusionneur multiblend -SansNona -Lisible
#     .\rendre_projet.ps1 -Projet "...\complet.pto" -Sortie "...\rendu" -Nom complet_multiblend -BigTiff `
#         -CompressionEnblend lzw -Fusionneur multiblend -OptionsMultiblend '--cache-threshold=4G' -SansNona
#
# (Fichier volontairement sans accents : il se lance aussi bien avec Windows PowerShell qu'avec PowerShell 7.)
param(
    [Parameter(Mandatory = $true)][string]$Projet,
    [Parameter(Mandatory = $true)][string]$Sortie,
    [string]$Nom = "panorama",
    [switch]$BigTiff,                 # nona --bigtiff : intermediaires > 4 Go (pleine resolution)
    [string]$CompressionEnblend = "", # ex. "lzw" ou "deflate" : force la compression de sortie d'enblend
    [ValidateSet('enblend', 'multiblend')][string]$Fusionneur = 'enblend',  # multiblend : seul a ecrire plus de 4 Go (BigTIFF)
    [string[]]$OptionsMultiblend = @(), # options ajoutees a multiblend, ex. "--cache-threshold=12G" (memoire au-dela de 12 Go sur disque)
    [switch]$SansNona,                # reutilise les f_NNNN.tif deja presents (comparer deux fusionneurs sans refaire nona)
    [switch]$GarderIntermediaires,    # conserve f_NNNN.tif et liste_enblend.txt apres une fusion reussie
    [switch]$NettoyerIntermediaires,  # obsolete : le nettoyage est le comportement par defaut
    [switch]$Lisible                  # copie lisible du panorama (TIFF classique + JPEG sRGB), voir rendre_lisible.ps1
)

$hb = 'C:\Program Files\Hugin\bin'
$multiblend = 'D:\Outils\multiblend\multiblend.exe'
New-Item -ItemType Directory $Sortie -Force | Out-Null
$log = Join-Path $Sortie 'rendu_log.txt'
if ($SansNona) { $ajout = @{ Append = $true } } else { $ajout = @{} }   # -SansNona : le journal du premier rendu est conserve
"debut : $(Get-Date -Format s)  projet : $Projet  fusionneur : $Fusionneur$(if ($OptionsMultiblend) { ' ' + ($OptionsMultiblend -join ' ') })$(if ($SansNona) { '  (sans nona)' })" | Out-File $log -Encoding utf8 @ajout

function Lancer($exe, $arguments, $etiquette, $dossier = $null) {
    $t = Get-Date
    $demarrage = @{ FilePath = $exe; ArgumentList = $arguments; NoNewWindow = $true; PassThru = $true }
    if ($dossier) { $demarrage.WorkingDirectory = $dossier }
    $p = Start-Process @demarrage
    $null = $p.Handle   # sans cette lecture, ExitCode peut rester vide une fois le processus termine
    $pic = 0
    while (-not $p.HasExited) {
        $p.Refresh()
        if ($p.WorkingSet64 -gt $pic) { $pic = $p.WorkingSet64 }
        Start-Sleep -Seconds 2
    }
    $s = ((Get-Date) - $t).TotalSeconds
    ("{0} : {1:N0} s, pic de RAM {2:N1} Go, code de sortie {3}" -f $etiquette, $s, ($pic / 1GB), $p.ExitCode) |
        Out-File $log -Append -Encoding utf8
    return $p.ExitCode
}

$argsNona = @('-z', 'LZW', '-o', "`"$Sortie\f_`"", "`"$Projet`"")
if ($BigTiff) { $argsNona = @('--bigtiff') + $argsNona }
if (-not $SansNona) { $null = Lancer "$hb\nona.exe" $argsNona 'nona' }

$tuiles = Get-ChildItem $Sortie -Filter 'f_*.tif' | Sort-Object Name | ForEach-Object { $_.FullName }
"nona : {0} images reprojetees{1}" -f $tuiles.Count, $(if ($SansNona) { ' (deja presentes)' }) | Out-File $log -Append -Encoding utf8
$liste = Join-Path $Sortie 'liste_enblend.txt'

if ($Fusionneur -eq 'multiblend') {
    # multiblend n'a pas de fichier de reponse : la liste passe en ligne de commande (32 767 caracteres au plus).
    # Lance depuis le dossier de rendu, avec des noms relatifs (f_0000.tif), 222 images tiennent en ~3 000 caracteres.
    $argsFusion = @()
    if ($BigTiff) { $argsFusion += '--bigtiff' }
    if ($CompressionEnblend) { $argsFusion += "--compression=$($CompressionEnblend.ToUpper())" }
    $argsFusion += $OptionsMultiblend
    $argsFusion += @('-o', "`"$Sortie\$Nom.tif`"")
    $argsFusion += ($tuiles | ForEach-Object { Split-Path $_ -Leaf })
    $codeEnblend = Lancer $multiblend $argsFusion 'multiblend' $Sortie
} else {
    $tuiles | Out-File $liste -Encoding ascii      # un chemin par ligne, SANS guillemets (le fichier de reponse d'enblend les refuse)
    $argsEnblend = @('--blend-colorspace=IDENTITY', '-o', "`"$Sortie\$Nom.tif`"", "`"@$liste`"")
    if ($CompressionEnblend) { $argsEnblend = @("--compression=$CompressionEnblend") + $argsEnblend }
    $codeEnblend = Lancer "$hb\enblend.exe" $argsEnblend 'enblend'
}

if ($GarderIntermediaires) {
    "nettoyage : intermediaires conserves (-GarderIntermediaires)" | Out-File $log -Append -Encoding utf8
} else {
    $panorama = Join-Path $Sortie "$Nom.tif"
    if ($codeEnblend -eq 0 -and (Test-Path -LiteralPath $panorama) -and (Get-Item -LiteralPath $panorama).Length -gt 0) {
        $octets = ($tuiles | ForEach-Object { (Get-Item -LiteralPath $_).Length } | Measure-Object -Sum).Sum
        foreach ($f in $tuiles) { Remove-Item -LiteralPath $f -Force }
        Remove-Item -LiteralPath $liste -Force -ErrorAction SilentlyContinue
        ("nettoyage : {0} intermediaires et liste_enblend.txt supprimes, {1:N1} Go liberes" -f $tuiles.Count, ($octets / 1GB)) |
            Out-File $log -Append -Encoding utf8
    } else {
        "nettoyage ignore : enblend n'a pas rendu le code 0 ou le panorama est absent ou vide (intermediaires conserves)" |
            Out-File $log -Append -Encoding utf8
    }
}
if ($Lisible) {
    $panorama = Join-Path $Sortie "$Nom.tif"
    if ($codeEnblend -eq 0 -and (Test-Path -LiteralPath $panorama) -and (Get-Item -LiteralPath $panorama).Length -gt 0) {
        try {
            & (Join-Path $PSScriptRoot 'rendre_lisible.ps1') -Panorama $panorama -Projet $Projet | Out-File $log -Append -Encoding utf8
        } catch {
            "lisible : echec, $($_.Exception.Message)" | Out-File $log -Append -Encoding utf8
        }
    } else {
        "lisible ignore : la fusion n'a pas abouti" | Out-File $log -Append -Encoding utf8
    }
}
"fin : $(Get-Date -Format s)" | Out-File $log -Append -Encoding utf8
Get-Content $log
