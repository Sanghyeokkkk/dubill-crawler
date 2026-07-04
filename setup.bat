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
echo [2/3] Installing required packages...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo [3/3] Creating desktop shortcut...
powershell -NoProfile -Command "$ws=New-Object -ComObject WScript.Shell; $sc=$ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'),'더빌 입금내역 수집.lnk')); $sc.TargetPath=Join-Path '%~dp0' '더빌_입금내역_수집.bat'; $sc.WorkingDirectory='%~dp0'.TrimEnd('\'); $sc.IconLocation='shell32.dll,44'; $sc.Description='더빌 입금내역 자동 수집'; $sc.Save()"

echo.
echo ============================================
echo  Setup complete!
echo  Desktop shortcut created: "더빌 입금내역 수집"
echo  Next:
echo   1) Copy config.example.py to config.py and fill in your info
echo   2) Put service_account.json in this folder
echo   3) Double-click the desktop icon to run
echo ============================================
pause
