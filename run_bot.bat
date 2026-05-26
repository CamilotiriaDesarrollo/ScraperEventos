@echo off
cd /d "c:\Users\camil\Desktop\Scrapper EVENTOS"
set LOGFILE=logs\task_run.log
"C:\Users\camil\AppData\Local\Programs\Python\Python310\python.exe" bot_publicador.py %* >> "%LOGFILE%" 2>&1