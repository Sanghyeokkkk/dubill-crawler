"""더빌(TheBill) 크롤러 설정 예시.

이 파일을 config.py 로 복사한 뒤 값을 채우세요:
    copy config.example.py config.py

config.py 에는 로그인 비밀번호가 들어가므로 외부에 공유하지 마세요.
"""

import os

# ── 더빌 로그인 ──────────────────────────────────────────
THEBILL_MAIN_URL = "https://www.thebill.co.kr/main.jsp"
THEBILL_ID = "여기에_아이디"
THEBILL_PW = "여기에_비밀번호"

# 가맹점(상점) ID — 다운로드 파일명 앞부분 (예: 30058059_20260612.xls)
MERCHANT_ID = "30058059"

# ── 조회 기간 ────────────────────────────────────────────
# 오늘 기준 며칠 전부터 조회할지 (예: 3 = 3일 전 ~ 오늘)
DAYS_AGO = 3

# ── 다운로드/저장 위치 ───────────────────────────────────
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
OUTPUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deposits.csv")

# ── 동작 옵션 ────────────────────────────────────────────
HEADLESS = False        # 2FA가 있으므로 False 필수 (창이 보여야 인증 가능)
TIMEOUT = 20            # 일반 요소 대기 최대 시간(초)
LOGIN_WAIT = 180        # 로그인(2FA 포함) 완료까지 대기(초)
RESULT_WAIT = 4         # 조회 결과 로딩 대기(초)
DOWNLOAD_WAIT = 30      # 엑셀 다운로드 완료 대기(초)

# 크롬 프로필 폴더: 한 번 2FA 하면 다음부터 로그인/인증을 기억(세션 유지).
# 비우면("") 매번 새 세션(매번 2FA). 기본은 프로젝트 내 전용 폴더.
CHROME_PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile")

# ── API 동기화(선택) ─────────────────────────────────────
ENABLE_API_SYNC = False  # True 로 하면 파싱 후 아래 API로 POST 전송
API_SYNC_URL = "https://www.pixel-haus.co.kr/api/public/bank-deposits/sync"

# ── 구글 시트 연동 ───────────────────────────────────────
ENABLE_SHEETS_SYNC = True  # True 면 파싱 후 구글 시트에 자동 입력
# 구글 서비스 계정 키 파일(JSON) 경로 — 설정 가이드 참고
SERVICE_ACCOUNT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "service_account.json")
# 데이터를 넣을 구글 시트 주소(전체 URL 붙여넣기)
SPREADSHEET_URL = "여기에_구글시트_URL"
WORKSHEET_NAME = "더빌_입금내역"   # 탭(시트) 이름 (없으면 자동 생성)
