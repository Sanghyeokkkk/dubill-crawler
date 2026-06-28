# 다른 PC에서 설치하기 (SETUP)

이 프로그램을 **새 컴퓨터**에서 돌리려면 아래 순서대로 한 번만 설정하면 됩니다.
(이미 설정된 PC에서는 바탕화면 바로가기만 더블클릭하면 됩니다.)

## 0. 미리 깔려 있어야 하는 것
- **Python 3.12 이상** — https://www.python.org/downloads/
  설치 시 **"Add Python to PATH" 체크** (중요!)
- **Google Chrome** — https://www.google.com/chrome/

## 1. 코드 받기 (git clone)
```powershell
git clone <이 저장소 주소> dubill-crawler
cd dubill-crawler
```
(또는 GitHub에서 ZIP 다운로드 후 압축 해제)

## 2. 설치 (setup.bat 더블클릭)
- `setup.bat` 더블클릭 → 가상환경(.venv) 생성 + 필요한 라이브러리 자동 설치
- (수동: `python -m venv .venv` 후 `.venv\Scripts\python -m pip install -r requirements.txt`)

## 3. 비밀정보 2개 넣기  ⭐ (git에는 안 올라가므로 직접 복사)
1. **config.py** 만들기
   - `config.example.py` 를 복사해 `config.py` 로 이름 변경
   - 안에 더빌 ID/PW, 가맹점ID, 구글시트 URL 입력
2. **service_account.json** 넣기
   - 구글 서비스 계정 키 파일을 이 폴더에 복사
   - (없으면 `GOOGLE_SHEETS_설정가이드.md` 보고 발급)

## 4. 실행
- 수동: `더빌_입금내역_수집.bat` 더블클릭
- 바탕화면 바로가기: 이 .bat 를 가리키도록 새로 만들면 됨

## 5. (선택) 매일 자동 실행 등록
PowerShell에서:
```powershell
$bat = "$PWD\dubill_schedule_run.bat"
$action  = New-ScheduledTaskAction -Execute $bat
$trigger = New-ScheduledTaskTrigger -Daily -At "10:00AM"
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName "DubillDepositSync" -Action $action -Trigger $trigger -Principal $principal -Force
```

---

### 요약
| 단계 | 한 일 |
|------|-------|
| 0 | Python + Chrome 설치 |
| 1 | git clone |
| 2 | setup.bat 실행 |
| 3 | config.py + service_account.json 복사 |
| 4 | 수집 .bat 더블클릭 |

> ⚠️ `config.py` 와 `service_account.json` 은 비밀정보라 GitHub에 올라가지 않습니다.
> 새 PC에서는 **반드시 직접 복사**해야 합니다 (USB나 안전한 경로로).
