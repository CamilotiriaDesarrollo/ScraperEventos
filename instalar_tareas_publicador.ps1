# Registra las 2 tareas del bot publicador en el Task Scheduler de Windows.
#
# Tareas que instala (diarias, lun-dom):
#   08:30 - Cola Bogota   (publica hoy primero, luego mañana, etc. hasta las 8:30 PM)
#   08:30 - Cola Pereira  (mismo orden cronológico, intervalo ~60 min)
#
# Intervalos anti-spam (definidos en config.py, NO se sobreescriben aquí):
#   Bogotá:  14-16 min entre publicaciones
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
    -ExecutionTimeLimit (New-TimeSpan -Hours 13)

$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

$Tareas = @(
    @{
        Nombre      = "PlanD_Cola_Bogota"
        Hora        = "08:30"
        Argumentos  = "`"$Script`" --canal Bogota --ciudad Bogota"
        Descripcion = "Bot publicador - Cola Bogota diaria (8:30 AM a 10 PM, 35-45 min entre publicaciones)"
    },
    @{
        Nombre      = "PlanD_Cola_Pereira"
        Hora        = "08:30"
        Argumentos  = "`"$Script`" --canal Pereira --ciudad Pereira"
        Descripcion = "Bot publicador - Cola Pereira diaria (8:30 AM a 10 PM, 65-80 min entre publicaciones)"
    }
)

foreach ($t in $Tareas) {
    $existing = Get-ScheduledTask -TaskName $t.Nombre -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Reemplazando tarea existente: $($t.Nombre)"
        Unregister-ScheduledTask -TaskName $t.Nombre -Confirm:$false
    }

    $PsArgs = "-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"& '$Python' $($t.Argumentos)`""
    $Action  = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument $PsArgs `
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

# Desactivar sleep e hibernacion automatica en AC para que el bot no se interrumpa
Write-Host ""
Write-Host "Configurando energia: desactivando sleep/hibernate automatico en AC..." -ForegroundColor Yellow
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /hibernate off
Write-Host "Energia configurada: sleep/hibernate desactivados en AC." -ForegroundColor Cyan
