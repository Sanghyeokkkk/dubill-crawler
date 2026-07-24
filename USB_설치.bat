@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title Dubill Crawler - USB Setup
cd /d "%~dp0"
echo ============================================
echo   Dubill Crawler - setup on THIS PC
echo   (Python 3.x and Google Chrome required)
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo  [ERROR] Python not found.
  echo  Install Python 3.12+ from https://www.python.org/downloads/
  echo  IMPORTANT: check "Add Python to PATH" during install.
  echo.
  pause
  exit /b 1
)
echo Python found:
python --version
echo.

echo Installing required packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo  [ERROR] Package install failed. Check your internet connection.
  pause
  exit /b 1
)

echo.
echo ============================================
echo   Setup complete on this PC!
echo   Now double-click:  더빌_입금내역_수집.bat
echo ============================================
pause
