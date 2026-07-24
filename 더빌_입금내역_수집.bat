@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title Dubill Deposit Collector
cd /d "%~dp0"
REM Use local .venv if present (main PC); otherwise system python (USB / other PC)
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
echo ============================================
echo  Dubill deposit collection starting...
echo  When Chrome opens: just log in (do 2FA if asked).
echo  Everything else runs automatically.
echo ============================================
echo.
"%PY%" dubill_crawler.py
echo.
echo ============================================
echo  Done. Press any key to close this window.
echo ============================================
pause >nul
