@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
REM Scheduled auto-run (no pause, logs to file). Manual run uses the Korean-named .bat.
cd /d "%~dp0"
REM Use local .venv if present; otherwise system python (USB / other PC)
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
if not exist "logs" mkdir "logs"
echo ==== %date% %time% start ==== >> "logs\schedule.log"
"%PY%" dubill_crawler.py >> "logs\schedule.log" 2>&1
echo ==== %date% %time% end (exit=%errorlevel%) ==== >> "logs\schedule.log"
