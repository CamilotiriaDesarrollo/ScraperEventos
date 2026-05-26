# Registra el listener de control remoto como tarea Windows.
# Corre cada minuto para sincronizar Google Sheets CONTROL tab con el bot.
#
# Uso: clic derecho > "Ejecutar con PowerShell"
#      o desde terminal: powershell -ExecutionPolicy Bypass -File instalar_listener.ps1

$Python  = "C:\Users\camil\AppData\Local\Programs\Python\Python310\python.exe"
$Script  = Join-Path $PSScriptRoot "control_listener.py"
$WorkDir = $PSScriptRoot
$LogDir  = Join-Path $PSScriptRoot "logs"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

# Trigger: cada 1 minuto, indefinidamente
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$PsArgs = "-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"& '$Python' '$Script'`""
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument $PsArgs `
    -WorkingDirectory $WorkDir

$name = "PlanD_ControlListener"

$existing = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Reemplazando tarea existente: $name"
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $name `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Control remoto bot - lee CONTROL tab en Sheets cada minuto" | Out-Null

Write-Host "OK  $name  (cada 1 minuto)" -ForegroundColor Green
Write-Host ""
Write-Host "Verificar con:" -ForegroundColor Cyan
Write-Host "  Get-ScheduledTask -TaskName 'PlanD_ControlListener'" -ForegroundColor Cyan
Write-Host ""
Write-Host ("Ver logs en: " + $LogDir + "\listener.log") -ForegroundColor Cyan
