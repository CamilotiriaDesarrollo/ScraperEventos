@echo off
REM Ejecuta el bot de scraping diario.
REM Programable con Task Scheduler de Windows.

cd /d "%~dp0"

set PYTHON_EXE=C:\Users\ZenBook\AppData\Local\Programs\Python\Python313\python.exe

if not exist "%PYTHON_EXE%" (
    echo ERROR: Python no encontrado en %PYTHON_EXE%
    exit /b 1
)

"%PYTHON_EXE%" main.py >> logs\scraper.log 2>&1
exit /b %ERRORLEVEL%
