@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
REM Scheduled auto-run (no pause, logs to file). Manual run uses the Korean-named .bat.
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
echo ==== %date% %time% start ==== >> "logs\schedule.log"
"%~dp0.venv\Scripts\python.exe" dubill_crawler.py >> "logs\schedule.log" 2>&1
echo ==== %date% %time% end (exit=%errorlevel%) ==== >> "logs\schedule.log"
