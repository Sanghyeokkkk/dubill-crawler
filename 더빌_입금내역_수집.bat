@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title Dubill Deposit Collector
cd /d "%~dp0"
echo ============================================
echo  Dubill deposit collection starting...
echo  When Chrome opens: just log in (do 2FA if asked).
echo  Everything else runs automatically.
echo ============================================
echo.
"%~dp0.venv\Scripts\python.exe" dubill_crawler.py
echo.
echo ============================================
echo  Done. Press any key to close this window.
echo ============================================
pause >nul
