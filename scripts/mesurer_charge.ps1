# Mesure la charge processeur et memoire de Hugin, du processeur de traitement par lots, de nona et d'enblend pendant un rendu.
#
# CONTEXTE
#     Outil de mesure. Sert a comparer deux configurations d'un rendu (journal affiche ou non, fenetres visibles ou
#     reduites) pour savoir si l'une d'elles ralentit le calcul. A lancer pendant un rendu en cours.
#
# MODE OPERATOIRE
#     Toutes les -Pas secondes, pendant -Duree secondes, releve la charge totale de la machine et, pour chacun des
#     processus enblend, nona, hugin, PTBatcherGUI et dwm, la charge CPU et la memoire (working set). Affiche ensuite
#     les moyennes.
#
# ENTREES (parametres)
#     -Etiquette   texte qui nomme la mesure dans l'affichage (defaut "mesure")
#     -Duree       duree de la mesure, en secondes (defaut 90)
#     -Pas         intervalle entre deux releves, en secondes (defaut 3)
#     Liste des processus suivis : variable $noms, en tete de script.
#
# SORTIES
#     Affichage a l'ecran seulement (rien n'est ecrit) : charge totale de la machine (moyenne, min, max, en % ;
#     16 threads) puis, par processus, CPU moyen et maximal et RAM moyenne en Mo.
#     La charge d'un processus est exprimee en % d'UN coeur (200 = deux coeurs entierement occupes).
#
# EXEMPLE
#     .\mesurer_charge.ps1 -Etiquette "journal affiche, fenetres visibles" -Duree 90 -Pas 3
#
# (Fichier volontairement sans accents : il se lance aussi bien avec Windows PowerShell qu'avec PowerShell 7.)
param(
    [string]$Etiquette = "mesure",
    [int]$Duree = 90,
    [int]$Pas = 3
)

$noms = 'enblend', 'nona', 'hugin', 'PTBatcherGUI', 'dwm'
$mesures = @()
$fin = (Get-Date).AddSeconds($Duree)
while ((Get-Date) -lt $fin) {
    $total = (Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'").PercentProcessorTime
    $proc = Get-CimInstance Win32_PerfFormattedData_PerfProc_Process | Where-Object { $noms -contains ($_.Name -replace '#\d+$', '') }
    $ligne = [ordered]@{ Total = [double]$total }
    foreach ($n in $noms) {
        $p = $proc | Where-Object { ($_.Name -replace '#\d+$', '') -eq $n }
        $ligne["cpu_$n"] = [double](($p | Measure-Object PercentProcessorTime -Sum).Sum)
        $ligne["ram_$n"] = [double](($p | Measure-Object WorkingSet -Sum).Sum) / 1MB
    }
    $mesures += [pscustomobject]$ligne
    Start-Sleep -Seconds $Pas
}

Write-Host ("=== {0} : {1} echantillons sur {2} s ===" -f $Etiquette, $mesures.Count, $Duree)
Write-Host ("Charge totale de la machine : moyenne {0:N1} %  (min {1:N0}, max {2:N0})" -f `
    ($mesures | Measure-Object Total -Average).Average, `
    ($mesures | Measure-Object Total -Minimum).Minimum, ($mesures | Measure-Object Total -Maximum).Maximum)
foreach ($n in $noms) {
    $cpu = $mesures | Measure-Object "cpu_$n" -Average -Maximum
    $ram = $mesures | Measure-Object "ram_$n" -Average
    Write-Host ("  {0,-13} CPU moyen {1,6:N1} % d'un coeur (max {2,5:N0})   RAM moyenne {3,7:N0} Mo" -f $n, $cpu.Average, $cpu.Maximum, $ram.Average)
}
