# Aktualisiert das Archiv, startet den lokalen Server und oeffnet das Dashboard.
# Ende: Enter druecken (oder Fenster schliessen).
Set-Location $PSScriptRoot

Write-Host "Hole aktuelle Pegeldaten ..."
python fetch.py
if ($LASTEXITCODE -ne 0) { Write-Host "Hinweis: Abruf fehlgeschlagen (offline?). Es werden die vorhandenen Daten angezeigt." }

$port = 8000
$srv = Start-Process python -ArgumentList "-m", "http.server", $port -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 1
Start-Process "http://localhost:$port/index.html"

Write-Host ""
Write-Host "Dashboard laeuft unter http://localhost:$port/index.html"
Read-Host "Zum Beenden Enter druecken" | Out-Null
Stop-Process -Id $srv.Id -ErrorAction SilentlyContinue
