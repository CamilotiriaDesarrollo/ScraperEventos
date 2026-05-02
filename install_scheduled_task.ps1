# Registra el bot como tarea programada de Windows.
# Corre todos los días a las 08:00 AM hora local.
# Para instalar: clic derecho en este archivo > "Ejecutar con PowerShell"
#                (o desde una terminal: powershell -ExecutionPolicy Bypass -File install_scheduled_task.ps1)

$TaskName  = "ScraperEventos_Diario"
$BatPath   = Join-Path $PSScriptRoot "run_scraper.bat"
$WorkDir   = $PSScriptRoot

if (-not (Test-Path $BatPath)) {
    Write-Error "No se encontro run_scraper.bat en $BatPath"
    exit 1
}

# Borrar si ya existe
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Eliminando tarea previa '$TaskName'..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$Action    = New-ScheduledTaskAction -Execute $BatPath -WorkingDirectory $WorkDir
$Trigger   = New-ScheduledTaskTrigger -Daily -At 08:00
$Settings  = New-ScheduledTaskSettingsSet `
                -AllowStartIfOnBatteries `
                -DontStopIfGoingOnBatteries `
                -StartWhenAvailable `
                -RunOnlyIfNetworkAvailable `
                -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Bot de scraping de eventos culturales (Pereira y Bogota)"

Write-Host ""
Write-Host "Tarea '$TaskName' registrada. Se ejecutara diariamente a las 08:00 AM." -ForegroundColor Green
Write-Host "Verifica con: Get-ScheduledTask -TaskName $TaskName" -ForegroundColor Cyan
Write-Host "Ejecutar manualmente: Start-ScheduledTask -TaskName $TaskName" -ForegroundColor Cyan
Write-Host "Eliminar: Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false" -ForegroundColor Cyan
