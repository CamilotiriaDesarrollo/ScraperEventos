# Registra las 2 tareas del bot publicador en el Task Scheduler de Windows.
#
# Tareas que instala (diarias, lun-dom):
#   08:00 - Cola Bogota   (publica hoy primero, luego mañana, etc. hasta las 10 PM)
#   08:00 - Cola Pereira  (mismo orden cronológico, intervalo ~60 min)
#
# Intervalos anti-spam (definidos en config.py, NO se sobreescriben aquí):
#   Bogotá:  19-22 min entre publicaciones
#   Pereira: 55-70 min entre publicaciones
#
# Wake Timer: el PC se despierta desde Sleep automáticamente a las 8 AM.
# REQUISITO: dejar el PC en Sleep (no Shutdown). Inicio > Encender > Suspender.
# Una sola vez en Windows: Configuración > Sistema > Energía >
#   "Permitir temporizadores de reactivación" = Habilitado.
#
# MultipleInstances = IgnoreNew: si el bot quedó pausado en memoria por un
# suspend y el PC despierta a las 8 AM, no se lanza una segunda instancia.
#
# Uso: clic derecho > "Ejecutar con PowerShell"
#      o desde terminal: powershell -ExecutionPolicy Bypass -File instalar_tareas_publicador.ps1

$Python  = "C:\Users\camil\AppData\Local\Programs\Python\Python310\python.exe"
$Script  = Join-Path $PSScriptRoot "bot_publicador.py"
$WorkDir = $PSScriptRoot
$LogDir  = Join-Path $PSScriptRoot "logs"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -WakeToRun `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 15)

$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

$Tareas = @(
    @{
        Nombre      = "PlanD_Cola_Bogota"
        Hora        = "08:00"
        Argumentos  = "`"$Script`" --canal TEST --ciudad Bogota"
        Descripcion = "Bot publicador - Cola Bogota diaria (8 AM a 10 PM, ~20 min/post)"
    },
    @{
        Nombre      = "PlanD_Cola_Pereira"
        Hora        = "08:00"
        Argumentos  = "`"$Script`" --canal TEST --ciudad Pereira"
        Descripcion = "Bot publicador - Cola Pereira diaria (8 AM a 10 PM, ~60 min/post)"
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

# Eliminar tareas de alertas si quedaron de versiones anteriores
foreach ($vieja in @("PlanD_Alertas_Bogota", "PlanD_Alertas_Pereira")) {
    if (Get-ScheduledTask -TaskName $vieja -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $vieja -Confirm:$false
        Write-Host "Eliminada tarea obsoleta: $vieja" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "2 tareas registradas. Verificar con:" -ForegroundColor Cyan
Write-Host "  Get-ScheduledTask | Where-Object TaskName -like 'PlanD_*'" -ForegroundColor Cyan
Write-Host ""
Write-Host "WAKE TIMER - para encendido automatico desde Sleep:" -ForegroundColor Yellow
Write-Host "  1. Una sola vez: Configuracion > Sistema > Energia >" -ForegroundColor Yellow
Write-Host "     'Permitir temporizadores de reactivacion' = Habilitado" -ForegroundColor Yellow
Write-Host "  2. Al terminar de trabajar: Inicio > Encender > Suspender" -ForegroundColor Yellow
Write-Host "     (NO Apagar - el Wake Timer no funciona con Apagar)" -ForegroundColor Yellow
