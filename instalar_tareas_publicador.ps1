# Registra las 4 tareas del bot publicador en el Task Scheduler de Windows.
#
# Tareas que instala:
#   08:01 AM — Cola Bogotá   (corre todo el día, 8 AM–10 PM, ~20 min/post)
#   08:01 AM — Cola Pereira  (corre todo el día, 8 AM–10 PM, ~60 min/post)
#   09:00 AM — Alertas Bogotá   (eventos que ocurren HOY en Bogotá)
#   09:00 AM — Alertas Pereira  (eventos que ocurren HOY en Pereira)
#
# Uso: clic derecho > "Ejecutar con PowerShell"
#      o desde terminal: powershell -ExecutionPolicy Bypass -File instalar_tareas_publicador.ps1

$Python   = "python"
$Script   = Join-Path $PSScriptRoot "bot_publicador.py"
$WorkDir  = $PSScriptRoot
$LogDir   = Join-Path $PSScriptRoot "logs"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 15)

$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

$Tareas = @(
    @{
        Nombre      = "PlanD_Cola_Bogota"
        Hora        = "08:01"
        Argumentos  = "$Script --canal Bogota --ciudad Bogota"
        Descripcion = "Bot publicador — Cola completa Bogota (8 AM–10 PM, ~20 min/post)"
    },
    @{
        Nombre      = "PlanD_Cola_Pereira"
        Hora        = "08:01"
        Argumentos  = "$Script --canal Pereira --ciudad Pereira"
        Descripcion = "Bot publicador — Cola completa Pereira (8 AM–10 PM, ~60 min/post)"
    },
    @{
        Nombre      = "PlanD_Alertas_Bogota"
        Hora        = "09:00"
        Argumentos  = "$Script --canal Bogota --ciudad Bogota --alertas"
        Descripcion = "Bot publicador — Alertas HOY Bogota (9 AM)"
    },
    @{
        Nombre      = "PlanD_Alertas_Pereira"
        Hora        = "09:00"
        Argumentos  = "$Script --canal Pereira --ciudad Pereira --alertas"
        Descripcion = "Bot publicador — Alertas HOY Pereira (9 AM)"
    }
)

foreach ($t in $Tareas) {
    $existing = Get-ScheduledTask -TaskName $t.Nombre -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Reemplazando tarea existente: $($t.Nombre)"
        Unregister-ScheduledTask -TaskName $t.Nombre -Confirm:$false
    }

    $Action  = New-ScheduledTaskAction `
        -Execute $Python `
        -Argument $t.Argumentos `
        -WorkingDirectory $WorkDir

    $Trigger = New-ScheduledTaskTrigger -Daily -At $t.Hora

    Register-ScheduledTask `
        -TaskName $t.Nombre `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description $t.Descripcion | Out-Null

    Write-Host "OK  $($t.Nombre)  ($($t.Hora))" -ForegroundColor Green
}

Write-Host ""
Write-Host "4 tareas registradas. Verificar con:" -ForegroundColor Cyan
Write-Host "  Get-ScheduledTask | Where-Object TaskName -like 'PlanD_*'" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANTE: antes de activar, configurar en .env:" -ForegroundColor Yellow
Write-Host "  WA_CANAL_BOGOTA = nombre exacto del canal Bogota en WhatsApp" -ForegroundColor Yellow
Write-Host "  WA_CANAL_PEREIRA = nombre exacto del canal Pereira en WhatsApp" -ForegroundColor Yellow
