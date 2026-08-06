# 더빌 크롤러 자동 실행 스케줄 등록 (하루 6회)
# 실행: 스케줄_등록.bat 더블클릭 (또는 이 .ps1 직접 실행)

$bat = Join-Path $PSScriptRoot "dubill_schedule_run.bat"
$times = @("09:00", "10:00", "12:00", "13:00", "16:00", "17:00")

$triggers = $times | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ }
$action = New-ScheduledTaskAction -Execute $bat
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName "DubillDepositSync" -Action $action -Trigger $triggers `
    -Principal $principal -Description "더빌 입금내역 자동 수집 (하루 6회)" -Force | Out-Null

Write-Host ""
Write-Host "스케줄 등록 완료: 매일 09 / 10 / 12 / 13 / 16 / 17 시" -ForegroundColor Green
Write-Host "실행 대상: $bat"
Write-Host ""
Write-Host "※ 실행 시각에 2단계 인증이 뜨면 사람이 인증해야 진행됩니다."
