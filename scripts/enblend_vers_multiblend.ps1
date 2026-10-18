# Adaptateur : fait passer multiblend pour enblend aupres de Hugin.
#
# CONTEXTE
#     Hugin appelle enblend avec une ligne de commande a la syntaxe d'enblend ; multiblend n'a pas la meme.
#     Hugin permet de choisir l'executable de fusion (Preferences > Enblend/Enfuse > Personnalise) : on lui
#     donne enblend_vers_multiblend.cmd, qui lance ce script. Il traduit les options connues, ignore les autres
#     (en les consignant dans le journal) et appelle multiblend. Pas de param() : tous les arguments de Hugin
#     arrivent tels quels dans $args.
#
# TRADUCTION
#     -o X / --output=X          -> -o X
#     --compression=lzw|packbits -> --compression=LZW|PACKBITS (deflate, jpeg : non pris en charge, LZW a la place pour deflate)
#     -w / --wrap[=mode]         -> --wrap[=mode]
#     -l N / --levels=N          -> --levels N
#     @fichier                   -> son contenu est lu : un nom d'image par ligne
#     --                         -> fin des options, le reste est la liste des images
#     autres options             -> ignorees (seam, masque, colorspace... propres a enblend), listees dans le journal
#     --bigtiff                  -> ajoute seul quand les images pesent ensemble plus de 3 Go (la toile fera plus de 4 Go)
#
# ENVIRONNEMENT
#     MULTIBLEND_EXE             chemin de multiblend.exe (defaut D:\Outils\multiblend\multiblend.exe)
#     MULTIBLEND_OPTIONS         options ajoutees telles quelles, ex. "--cache-threshold=12G"
#
# SORTIES
#     %TEMP%\enblend_vers_multiblend.log : arguments recus, commande lancee, code de sortie. Le code de sortie de
#     multiblend est rendu a Hugin.
#
# (Fichier volontairement sans accents : il se lance aussi bien avec Windows PowerShell qu'avec PowerShell 7.)

$multiblend = if ($env:MULTIBLEND_EXE) { $env:MULTIBLEND_EXE } else { 'D:\Outils\multiblend\multiblend.exe' }
$journal = Join-Path $env:TEMP 'enblend_vers_multiblend.log'
"=== $(Get-Date -Format s)  recu : $($args -join ' ')" | Out-File $journal -Append -Encoding utf8

if ($args.Count -eq 1 -and $args[0] -eq '--version') {   # Hugin interroge enblend ainsi au demarrage
    'enblend (adaptateur multiblend)'
    exit 0
}

$sortie = $null
$options = @()
$images = @()
$ignorees = @()
$finOptions = $false
$i = 0
while ($i -lt $args.Count) {
    $a = [string]$args[$i]
    if ($finOptions) { $images += $a }
    elseif ($a -eq '--') { $finOptions = $true }
    elseif ($a -eq '-o' -or $a -eq '--output') { $i++; $sortie = [string]$args[$i] }
    elseif ($a -like '--output=*') { $sortie = $a.Substring(9) }
    elseif ($a -like '--compression=*') {
        $c = $a.Substring(14).ToUpper()
        if ($c -eq 'LZW' -or $c -eq 'PACKBITS') { $options += "--compression=$c" }
        elseif ($c -eq 'DEFLATE') { $options += '--compression=LZW'; $ignorees += "$a (remplace par LZW)" }
        else { $ignorees += $a }
    }
    elseif ($a -eq '-w' -or $a -eq '--wrap') { $options += '--wrap' }
    elseif ($a -like '--wrap=*') { $options += $a }
    elseif ($a -eq '-l' -or $a -eq '--levels') { $i++; $options += @('--levels', [string]$args[$i]) }
    elseif ($a -like '--levels=*') { $options += @('--levels', $a.Substring(9)) }
    elseif ($a.StartsWith('@')) {
        $images += (Get-Content -LiteralPath $a.Substring(1) | Where-Object { $_.Trim() } | ForEach-Object { $_.Trim().Trim('"') })
    }
    elseif ($a -in '-f', '-m', '-b', '-d') { $i++; $ignorees += "$a $($args[$i])" }   # options d'enblend a valeur separee
    elseif ($a.StartsWith('-') -and -not (Test-Path -LiteralPath $a)) { $ignorees += $a }
    else { $images += $a }
    $i++
}

if (-not $sortie -or $images.Count -eq 0) {
    "ERREUR : sortie ou images manquantes (sortie=$sortie, images=$($images.Count))" | Out-File $journal -Append -Encoding utf8
    [Console]::Error.WriteLine('enblend_vers_multiblend : sortie ou images manquantes (voir ' + $journal + ')')
    exit 2
}

$poids = ($images | ForEach-Object { if (Test-Path -LiteralPath $_) { (Get-Item -LiteralPath $_).Length } else { 0 } } | Measure-Object -Sum).Sum
if ($poids -gt 3GB) { $options += '--bigtiff' }
if ($env:MULTIBLEND_OPTIONS) { $options += ($env:MULTIBLEND_OPTIONS -split '\s+' | Where-Object { $_ }) }

$commande = @($options) + @('-o', $sortie) + $images
"ignore : $($ignorees -join ' ')" | Out-File $journal -Append -Encoding utf8
"lance : $multiblend $($options -join ' ') -o $sortie  ($($images.Count) images, $([math]::Round($poids / 1GB, 2)) Go)" | Out-File $journal -Append -Encoding utf8

& $multiblend @commande
$code = $LASTEXITCODE
"code de sortie : $code" | Out-File $journal -Append -Encoding utf8
exit $code
