@echo off
chcp 65001 >nul
title Dubill Schedule Remove
echo 더빌 자동 실행 스케줄을 삭제합니다...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unregister-ScheduledTask -TaskName 'DubillDepositSync' -Confirm:$false; Write-Host '삭제 완료' -ForegroundColor Yellow"
echo.
pause
