@echo off
chcp 65001 >nul
title Dubill Schedule Setup
echo ============================================
echo   더빌 크롤러 자동 실행 스케줄 등록
echo   매일 09 / 10 / 12 / 13 / 16 / 17 시 (하루 6회)
echo ============================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0스케줄_등록.ps1"
echo.
echo 취소(스케줄 삭제)하려면:  스케줄_삭제.bat
echo.
pause
