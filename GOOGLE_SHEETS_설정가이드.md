# 구글 시트 자동 연동 설정 가이드

크롤러가 구글 시트에 자동으로 입금내역을 입력하려면, **서비스 계정(로봇 계정)** 을
하나 만들어서 그 계정에게 시트 편집 권한을 주면 됩니다. 한 번만 설정하면 됩니다.

소요 시간: 약 10분. 아래 순서대로만 따라 하세요.

---

## 1단계. 구글 클라우드 프로젝트 만들기
1. https://console.cloud.google.com/ 접속 (구글 로그인)
2. 상단 프로젝트 선택 → **새 프로젝트** → 이름 예: `dubill-crawler` → 만들기

## 2단계. API 2개 켜기
좌측 메뉴 **API 및 서비스 → 라이브러리** 에서 검색 후 각각 **사용** 클릭:
- `Google Sheets API`
- `Google Drive API`

## 3단계. 서비스 계정 만들기
1. **API 및 서비스 → 사용자 인증 정보** 이동
2. 상단 **+ 사용자 인증 정보 만들기 → 서비스 계정**
3. 이름 예: `dubill-bot` → 만들고 계속 → (역할은 비워도 됨) → 완료

## 4단계. 키(JSON) 내려받기  ⭐가장 중요
1. 방금 만든 서비스 계정 클릭 → **키** 탭
2. **키 추가 → 새 키 만들기 → JSON → 만들기**
3. JSON 파일이 다운로드됨 →
   - 파일 이름을 **`service_account.json`** 으로 변경
   - 이 폴더(`C:\Users\Puser\crawler-app\`)에 넣기

## 5단계. 서비스 계정 이메일 복사
- 서비스 계정 화면에 있는 이메일 (예: `dubill-bot@dubill-crawler.iam.gserviceaccount.com`)
- 이 이메일을 복사해 둡니다.

## 6단계. 기존 [OPS] 시트 공유 (새 탭은 자동 생성됨)
1. 기존 **[OPS] 픽셀 관리시트** 열기
2. 우측 상단 **공유** 클릭
3. 5단계의 **서비스 계정 이메일**을 붙여넣고 권한을 **편집자**로 → 보내기
4. 브라우저 주소창의 시트 **URL 전체**를 복사
   (예: `https://docs.google.com/spreadsheets/d/1AbC.../edit#gid=0`)

> 더빌 데이터는 이 시트 안에 **"더빌_입금내역" 이라는 새 탭**으로 자동 생성되어
> 쌓입니다. 기존 운영 데이터(다른 탭)는 건드리지 않으니 안전합니다.

## 7단계. config.py 에 시트 주소 입력
`C:\Users\Puser\crawler-app\config.py` 열어서:
```python
SPREADSHEET_URL = "여기에_복사한_시트_URL_붙여넣기"
```

---

## 설정 확인 (테스트)
설정이 끝나면 아래로 테스트할 수 있습니다 (가짜 입금 3건이 시트에 올라감):
```powershell
& "C:\Users\Puser\dubill-pms\.venv\Scripts\python.exe" make_test_xls.py
& "C:\Users\Puser\dubill-pms\.venv\Scripts\python.exe" dubill_crawler.py --parse-only test_deposits.xlsx
```
→ 구글 시트의 "입금내역" 탭에 3줄이 자동으로 추가되면 성공!

## 정리
필요한 것 2가지만 기억하세요:
1. `service_account.json` 파일을 이 폴더에 두기 (4단계)
2. 시트를 서비스계정 이메일과 **편집자**로 공유 + URL을 config.py 에 넣기 (6~7단계)
