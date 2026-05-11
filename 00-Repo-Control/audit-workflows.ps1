$root = "c:\Users\Ruzava\Desktop\Bastien-Antigravity"
$dirs = Get-ChildItem -Path $root -Directory | Where-Object { $_.Name -ne '.git' -and $_.Name -ne 'obsidian-brain' }

foreach ($d in $dirs) {
    $wf = Join-Path $d.FullName ".github\workflows"
    if (Test-Path $wf) {
        $files = (Get-ChildItem $wf -File | Select-Object -ExpandProperty Name) -join ", "
        Write-Output "$($d.Name): $files"
    } else {
        Write-Output "$($d.Name): NO WORKFLOWS"
    }
}
