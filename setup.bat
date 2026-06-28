@echo off
chcp 65001 >nul
title Dubill Crawler - Setup
cd /d "%~dp0"
echo ============================================
echo  Dubill Crawler setup
echo  (Python 3.x and Google Chrome must be installed first)
echo ============================================
echo.
echo [1/2] Creating virtual environment (.venv)...
python -m venv .venv
if errorlevel 1 (
  echo.
  echo  ERROR: 'python' not found. Install Python 3.12 and check "Add to PATH".
  pause
  exit /b 1
)
echo [2/2] Installing required packages...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
echo.
echo ============================================
echo  Setup complete!
echo  Next:
echo   1) Copy config.example.py to config.py and fill in your info
echo   2) Put service_account.json in this folder
echo   3) Run the collector (double-click the collector .bat)
echo ============================================
pause
