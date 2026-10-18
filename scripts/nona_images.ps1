# Rend avec nona seulement certaines images d'un projet Hugin (.pto), une par une, en chronometrant chaque appel et en relevant le pic de RAM.
#
# CONTEXTE
#     Phase 6 (pleine resolution). Sert a completer des intermediaires f_NNNN.tif deja presents (rendus d'un test
#     precedent, meme projet pour ces images) sans les refaire, ou a rendre un grand projet image par image pour
#     limiter la memoire. La fusion se fait ensuite avec rendre_projet.ps1 -SansNona.
#
# MODE OPERATOIRE
#     Pour chaque image de -De a -A : saute l'image si f_NNNN.tif existe deja et n'est pas vide ; sinon lance
#     nona pour cette seule image (compression LZW), releve le pic de memoire, et s'arrete a la premiere erreur.
#     nona ecrit d'abord tmp_NNNN.tif, renomme en f_NNNN.tif seulement quand l'image est terminee : une image
#     interrompue en cours d'ecriture ne peut pas passer pour rendue.
#     Le script peut etre relance apres une interruption : il supprime les tmp_*.tif restants et reprend ou il
#     s'est arrete. Pour interrompre : arreter le script PUIS le processus nona.exe, qui continuerait seul.
#
# ENTREES (parametres)
#     -Projet    projet Hugin (.pto) a rendre
#     -Sortie    dossier de rendu (cree si besoin) ; recoit les f_NNNN.tif
#     -De, -A    premiere et derniere image a rendre (numeros du projet, bornes comprises)
#     -BigTiff   (option) ecrit des TIFF BigTIFF : necessaire quand une image reprojetee depasse 4 Go
#     -Hugin     (option) dossier bin de Hugin (defaut C:\Program Files\Hugin\bin)
#     -IgnorerExposition   (option) nona --ignore-exposure : ne corrige pas l'exposition (Eev) des images ; indispensable pour
#                          les calques HDR " sans correction d'exposition " (sinon toutes les expositions sortent identiques et
#                          saturees) ; inutile pour une vue centree en une seule exposition
#     Programme appele : C:\Program Files\Hugin\bin\nona.exe (variable $nona, en tete de script).
#
# SORTIES
#     Dans le dossier Sortie : les images reprojetees f_NNNN.tif (chacune a la taille de toute la toile) et le
#     journal rendu_log.txt (ajoute a la suite : debut, une ligne par image, bilan avec duree totale, pic de RAM,
#     nombre d'images rendues et deja presentes, fin). Code de sortie 1 si nona echoue.
#
# EXEMPLE
#     .\nona_images.ps1 -Projet "...\projet.pto" -Sortie "...\rendu" -De 37 -A 110 -BigTiff
#
# (Fichier volontairement sans accents : il se lance aussi bien avec Windows PowerShell qu'avec PowerShell 7.)
param(
    [Parameter(Mandatory = $true)][string]$Projet,
    [Parameter(Mandatory = $true)][string]$Sortie,
    [Parameter(Mandatory = $true)][int]$De,
    [Parameter(Mandatory = $true)][int]$A,
    [switch]$BigTiff,
    [switch]$IgnorerExposition,
    [string]$Hugin = 'C:\Program Files\Hugin\bin'   # dossier bin de Hugin (nona.exe)
)

$nona = Join-Path $Hugin 'nona.exe'
New-Item -ItemType Directory $Sortie -Force | Out-Null
$log = Join-Path $Sortie 'rendu_log.txt'
$t0 = Get-Date
"debut : $(Get-Date -Format s)  nona seul, images $De a $A  projet : $Projet" | Out-File $log -Append -Encoding utf8
$pic = 0
$rendues = 0
$sautees = 0

# Restes d'une interruption : images commencees mais pas terminees
$restes = @(Get-ChildItem -LiteralPath $Sortie -Filter 'tmp_*.tif' -File)
foreach ($r in $restes) { Remove-Item -LiteralPath $r.FullName -Force }
if ($restes.Count) { "reprise : {0} image(s) inachevee(s) supprimee(s) ({1})" -f $restes.Count, ($restes.Name -join ', ') | Out-File $log -Append -Encoding utf8 }

for ($i = $De; $i -le $A; $i++) {
    $fichier = Join-Path $Sortie ('f_{0:D4}.tif' -f $i)
    $provisoire = Join-Path $Sortie ('tmp_{0:D4}.tif' -f $i)
    if ((Test-Path -LiteralPath $fichier) -and (Get-Item -LiteralPath $fichier).Length -gt 0) { $sautees++; continue }
    $arguments = @('-z', 'LZW', '-i', "$i", '-o', "`"$Sortie\tmp_`"", "`"$Projet`"")
    if ($BigTiff) { $arguments = @('--bigtiff') + $arguments }
    if ($IgnorerExposition) { $arguments = @('--ignore-exposure') + $arguments }
    $p = Start-Process -FilePath $nona -ArgumentList $arguments -NoNewWindow -PassThru
    $null = $p.Handle
    while (-not $p.HasExited) {
        $p.Refresh()
        if ($p.WorkingSet64 -gt $pic) { $pic = $p.WorkingSet64 }
        Start-Sleep -Seconds 2
    }
    if ($p.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $provisoire)) {
        "ECHEC image $i : code de sortie $($p.ExitCode), $provisoire absent" | Out-File $log -Append -Encoding utf8
        exit 1
    }
    Move-Item -LiteralPath $provisoire -Destination $fichier -Force
    $rendues++
    ("image {0} : ok ({1:N0} s depuis le debut)" -f $i, ((Get-Date) - $t0).TotalSeconds) | Out-File $log -Append -Encoding utf8
}

("nona (images {0} a {1}) : {2:N0} s, pic de RAM {3:N1} Go, {4} rendues, {5} deja presentes" -f $De, $A, ((Get-Date) - $t0).TotalSeconds, ($pic / 1GB), $rendues, $sautees) |
    Out-File $log -Append -Encoding utf8
"fin : $(Get-Date -Format s)" | Out-File $log -Append -Encoding utf8
