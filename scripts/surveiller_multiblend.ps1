# Surveille multiblend pendant un rendu : memoire du processus, RAM libre du systeme, taille de TEMP.
#
# CONTEXTE
#     Phase 6, fusion pleine resolution. multiblend peut consommer beaucoup de RAM et deborder dans un cache sous
#     %TEMP% : ce releve permet de savoir si le rendu a assez de memoire libre et de dimensionner
#     --cache-threshold. A lancer en parallele de rendre_projet.ps1, dans une autre fenetre.
#
# MODE OPERATOIRE
#     Attend que multiblend demarre, puis releve toutes les 20 secondes : memoire (working set et memoire privee) du
#     processus, RAM libre du systeme, taille du dossier TEMP. S'arrete quand multiblend se termine.
#
# ENTREES (parametres)
#     -Sortie    fichier CSV a ecrire (ex. releves.csv)
#
# SORTIES
#     Fichier -Sortie, separateur " ; ", une ligne par releve : heure ; working_set_Go ; prive_Go ; RAM_libre_Go ; TEMP_Go.
#
# EXEMPLE
#     .\surveiller_multiblend.ps1 -Sortie releves.csv   (s'arrete quand multiblend se termine)
#
# (Fichier volontairement sans accents.)
param([string]$Sortie)
# Releve toutes les 20 s : memoire de multiblend (working set, privee), RAM libre du systeme, taille de TEMP.
"heure ; working_set_Go ; prive_Go ; RAM_libre_Go ; TEMP_Go" | Out-File $Sortie -Encoding utf8
$vu = $false
while ($true) {
    $m = Get-Process multiblend -ErrorAction SilentlyContinue
    if ($m) { $vu = $true } elseif ($vu) { break }
    if ($m) {
        $libre = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
        $temp = (Get-ChildItem $env:TEMP -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1GB
        "{0} ; {1:N1} ; {2:N1} ; {3:N1} ; {4:N2}" -f (Get-Date -Format HH:mm:ss), ($m.WorkingSet64 / 1GB), ($m.PrivateMemorySize64 / 1GB), $libre, $temp |
            Out-File $Sortie -Append -Encoding utf8
    }
    Start-Sleep -Seconds 20
}

