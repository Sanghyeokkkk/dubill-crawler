"""더빌(TheBill / NICE정보통신 CMS) 입금내역 크롤러.

실제 운영 자동화의 흐름을 그대로 재현한 버전:
    로그인 → 가상계좌 메뉴 → 입금내역관리 → 입금내역조회(VAS4010)
    → 조회기간 설정 → 조회 → 엑셀다운로드 → .xls 파싱 → CSV(+선택적 API 전송)

엑셀 '표 긁기'가 아니라 더빌이 제공하는 '엑셀 다운로드' 파일을 받아서
파싱하는 방식이라 더 안정적입니다.

실행:
    1) copy config.example.py config.py   (그리고 config.py 값 채우기)
    2) python dubill_crawler.py            (전체 실행: 다운로드+파싱)
    3) python dubill_crawler.py --parse-only 파일경로.xls   (파싱만 테스트)

⚠️ 로그인 입력칸/일부 메뉴의 정확한 셀렉터는 실제 페이지 확인이 필요해
   TODO 로 표시해 두었습니다. parse_deposits() 와 다운로드 처리는 완성본입니다.
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

try:
    import config
except ImportError:
    sys.exit(
        "[오류] config.py 가 없습니다.\n"
        "      먼저 'copy config.example.py config.py' 로 만들고 로그인 정보를 채우세요."
    )


# ════════════════════════════════════════════════════════════════
#  데이터 구조
# ════════════════════════════════════════════════════════════════
@dataclass
class Deposit:
    """입금 한 건 (더빌 입금내역조회 실제 컬럼 기준).

    ※ 더빌의 '등록구분' 컬럼은 가상계좌번호와 값이 동일(중복)해 제외함.
    """
    paid_at: str            # 입금일시
    billing_month: str = "" # 청구월
    settle_date: str = ""   # 정산일
    customer: str = ""      # 고객명 (지점/호실)
    depositor: str = ""     # 출금계좌성명 (실제 입금자명)
    amount: int = 0         # 입금금액
    bank: str = ""          # 가상계좌은행
    vacct: str = ""         # 가상계좌번호
    deposit_type: str = ""  # 입금구분


def log(msg: str) -> None:
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} [INFO] {msg}")


# ════════════════════════════════════════════════════════════════
#  1) 브라우저 준비 (엑셀 자동 다운로드 설정 포함)
# ════════════════════════════════════════════════════════════════
def build_driver() -> webdriver.Chrome:
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    options = Options()
    if config.HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,1000")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # 프로필 폴더 지정 → 2FA/로그인 세션 기억 (다음 실행 때 인증 생략 기대)
    profile = getattr(config, "CHROME_PROFILE_DIR", "")
    if profile:
        os.makedirs(profile, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile}")
    # 다운로드 폴더 지정 + 다운로드 확인창 끄기
    options.add_experimental_option("prefs", {
        "download.default_directory": config.DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    return driver


# ════════════════════════════════════════════════════════════════
#  2) 로그인  →  3) 메뉴 이동  →  4) 조회  →  5) 엑셀 다운로드
# ════════════════════════════════════════════════════════════════
def login(driver: webdriver.Chrome) -> None:
    """더빌 로그인.

    셀렉터(확정): 아이디=loginid, 비밀번호=loginpw, 로그인버튼=btnLogin
    더빌은 2단계 인증(카카오/이메일/휴대폰)이 있으므로, ID/비번 자동 입력 후
    인증은 사용자가 화면에서 직접 처리한다(반자동). HEADLESS=False 필수.
    """
    log("--- Step 1: TheBill 접속 ---")
    driver.get(config.THEBILL_MAIN_URL)
    time.sleep(2)
    log("메인 페이지 도착")

    # 프로필 세션이 살아있으면 이미 로그인된 상태일 수 있음
    if _is_logged_in(driver):
        log("이미 로그인된 세션입니다 (2FA 생략).")
        return

    # 아이디/비밀번호 입력 후 로그인 버튼
    try:
        id_box = WebDriverWait(driver, config.TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "loginid")))
        id_box.clear()
        id_box.send_keys(config.THEBILL_ID)
        pw_box = driver.find_element(By.ID, "loginpw")
        pw_box.clear()
        pw_box.send_keys(config.THEBILL_PW)
        driver.find_element(By.ID, "btnLogin").click()
        log("아이디/비밀번호 입력 후 로그인 클릭")
    except Exception as e:
        log(f"로그인 폼 입력 생략/실패({e}) — 수동 로그인 대기로 진행")

    log("=" * 56)
    log(" 크롬 창에서 2단계 인증(카카오/이메일/휴대폰)을 완료하세요.")
    log(f" 로그인 완료까지 최대 {config.LOGIN_WAIT}초 기다립니다...")
    log("=" * 56)

    # 로그인(2FA) 완료까지 대기 — 페이지 제목이 '더빌 [가맹점ID]' 로 바뀜
    deadline = time.time() + config.LOGIN_WAIT
    while time.time() < deadline:
        if _is_logged_in(driver):
            log("로그인 완료 감지!")
            return
        time.sleep(2)
    raise TimeoutError("로그인이 제한시간 내에 완료되지 않았습니다(2FA 미완료?).")


def _is_logged_in(driver) -> bool:
    """로그인 여부: 제목이 '더빌 [가맹점ID]' 형태인지로 판단."""
    try:
        title = driver.title or ""
        return "더빌 [" in title and config.MERCHANT_ID in title
    except Exception:
        return False


# 입금내역조회 화면을 SPA로 불러오는 경로 (분석으로 확인됨)
VACCT_TOP_URL = "https://www.thebill.co.kr/vacct/not/vaNotMasUpdateTop.tb?menucd=VAS1010"
DEPOSIT_CONTENT = "/vacct/rcp/vaRcpMasList.tb?menucd=VAS4010"


def go_to_deposit_inquiry(driver: webdriver.Chrome) -> None:
    """가상계좌 섹션 로드 → 입금내역조회(VAS4010) 컨텐츠 로드."""
    log("--- Step 2: 입금내역조회 화면 이동 ---")
    wait = WebDriverWait(driver, config.TIMEOUT)

    # 가상계좌 섹션 셸 로드 ($.loadContent 사용 가능 상태 만들기)
    driver.get(VACCT_TOP_URL)
    wait.until(lambda d: d.execute_script(
        "return (typeof jQuery!=='undefined') && (typeof $.loadContent==='function')"))
    log("가상계좌 섹션 로드 완료")

    # 입금내역조회 컨텐츠를 AJAX로 로드 (메뉴 클릭과 동일한 동작)
    driver.execute_script("$.loadContent(arguments[0]);", DEPOSIT_CONTENT)

    # 조회 화면의 시작일 칸이 뜨면 로드 완료
    wait.until(EC.presence_of_element_located((By.ID, "startDate")))
    log("입금내역조회(VAS4010) 화면 로드 완료")


def search_and_download(driver: webdriver.Chrome) -> str:
    """조회기간 설정 → 조회 → 엑셀다운로드. 다운로드된 파일 경로를 반환."""
    log("--- Step 3: 기간 설정 → 조회 → 엑셀다운로드 ---")
    wait = WebDriverWait(driver, config.TIMEOUT)
    start_date = (datetime.now() - timedelta(days=config.DAYS_AGO)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    # 시작일/종료일 입력 (datepicker 칸이라 값 주입 + change 이벤트 발생)
    driver.execute_script(
        "var s=document.getElementById('startDate'); s.value=arguments[0];"
        "var e=document.getElementById('endDate'); e.value=arguments[1];", start_date, end_date)
    log(f"조회기간: {start_date} ~ {end_date}")

    # 조회 실행 (조회 버튼 onclick=$.retrieve())
    driver.execute_script("$.retrieve();")
    log("조회 실행")
    time.sleep(config.RESULT_WAIT)  # 결과 로딩 대기

    # 엑셀다운로드 (버튼 onclick=xlsDownload())
    before = set(glob.glob(os.path.join(config.DOWNLOAD_DIR, "*")))
    driver.execute_script("xlsDownload();")
    log("엑셀다운로드 실행")
    return wait_for_download(before)


def wait_for_download(before: set[str]) -> str:
    """다운로드 폴더에 엑셀 파일이 '완성'될 때까지 대기 후 경로 반환.

    크롬은 받는 중엔 .crdownload/.tmp 로 저장했다가 끝나면 .xls 로 이름을 바꾼다.
    그래서 임시 확장자는 무시하고, 크기가 안정된 .xls/.xlsx 만 인정한다.
    """
    skip = (".crdownload", ".tmp")
    deadline = time.time() + config.DOWNLOAD_WAIT
    while time.time() < deadline:
        now = set(glob.glob(os.path.join(config.DOWNLOAD_DIR, "*")))
        new = [f for f in (now - before) if not f.endswith(skip)]
        finished = [f for f in new if f.lower().endswith((".xls", ".xlsx"))]
        if finished:
            path = max(finished, key=os.path.getctime)
            size1 = os.path.getsize(path)
            time.sleep(0.8)  # 크기 안정화 확인
            if os.path.exists(path) and os.path.getsize(path) == size1:
                log(f"다운로드 완료: {path}")
                return path
        time.sleep(0.5)
    raise TimeoutError("다운로드가 제한시간 내에 완료되지 않았습니다.")


# ════════════════════════════════════════════════════════════════
#  6) 엑셀 파싱  (완성본 — 실제 파일만 있으면 동작)
# ════════════════════════════════════════════════════════════════
# 더빌 엑셀의 컬럼명 후보 → 표준 필드 매핑 (앞쪽일수록 우선)
COLUMN_HINTS = {
    "paid_at":       ["입금일시", "거래일시", "입금일자", "거래일자"],
    "billing_month": ["청구월"],
    "settle_date":   ["정산일"],
    "customer":      ["고객명", "고객"],
    "depositor":     ["출금계좌성명", "입금자명", "보내는분", "송금인", "성명"],
    "amount":        ["입금금액", "입금액", "거래금액", "금액"],
    "bank":          ["가상계좌은행", "은행명", "은행", "거래은행"],
    "vacct":         ["가상계좌번호", "계좌번호"],
    "deposit_type":  ["입금구분"],
}


def _pick(colnames: list[str], hints: list[str]) -> str | None:
    """후보 단어가 포함된 컬럼명을 찾는다."""
    for c in colnames:
        cs = str(c).replace(" ", "")
        for h in hints:
            if h in cs:
                return c
    return None


def _clean(val) -> str:
    """빈 값/nan 을 깔끔한 빈 문자열로."""
    s = str(val).strip()
    return "" if s.lower() in ("nan", "none", "nat") else s


def _to_int(val) -> int:
    s = str(val).replace(",", "").replace("원", "").strip()
    try:
        return int(float(s))
    except ValueError:
        return 0


# 합계/소계 등 집계행을 거르기 위한 키워드 (고객명 오탐 방지를 위해 단독 '계'는 제외)
_SUMMARY_WORDS = ("합계", "소계", "총계", "합 계")


def parse_deposits(path: str) -> list[Deposit]:
    """다운로드한 엑셀(.xls)을 파싱한다.

    더빌 같은 국내 시스템은 .xls 확장자지만 실제론 HTML 표인 경우가 흔해서,
    두 방식을 모두 시도한다.
    """
    import pandas as pd

    log(f"엑셀 파싱: {path}")
    df = None
    # (1) 확장자에 맞는 엔진 자동 선택 (.xls=xlrd, .xlsx=openpyxl)
    try:
        df = pd.read_excel(path)
    except Exception:
        pass
    # (2) .xls 강제 시도
    if df is None or df.empty:
        try:
            df = pd.read_excel(path, engine="xlrd")
        except Exception:
            pass
    # (3) HTML 표로 위장된 .xls 시도 (국내 시스템에서 흔함)
    if df is None or df.empty:
        try:
            tables = pd.read_html(path)
            if tables:
                df = max(tables, key=len)  # 가장 행 많은 표 선택
        except Exception:
            pass
    if df is None or df.empty:
        raise ValueError(f"엑셀을 읽지 못했습니다: {path} (구조를 알려주시면 맞춰 드립니다)")

    cols = list(df.columns)
    log(f"감지된 컬럼: {cols}")
    m = {k: _pick(cols, h) for k, h in COLUMN_HINTS.items()}

    def g(row, key):
        return _clean(row[m[key]]) if m.get(key) else ""

    deposits: list[Deposit] = []
    for _, row in df.iterrows():
        amount = _to_int(row[m["amount"]]) if m.get("amount") else 0
        if amount <= 0:  # 금액 없는 빈행 거르기
            continue
        paid_at = g(row, "paid_at")
        customer = g(row, "customer")
        depositor = g(row, "depositor")
        # 합계/소계 등 집계행 거르기
        joined = f"{paid_at} {customer} {depositor}"
        if any(w in joined for w in _SUMMARY_WORDS):
            continue
        deposits.append(Deposit(
            paid_at=paid_at,
            billing_month=g(row, "billing_month"),
            settle_date=g(row, "settle_date"),
            customer=customer,
            depositor=depositor,
            amount=amount,
            bank=g(row, "bank"),
            vacct=g(row, "vacct"),
            deposit_type=g(row, "deposit_type"),
        ))
    log(f"파싱 결과: 입금 {len(deposits)}건")
    return deposits


# ════════════════════════════════════════════════════════════════
#  7) 저장 / 전송
# ════════════════════════════════════════════════════════════════
CSV_FIELDS = ["paid_at", "billing_month", "settle_date", "customer", "depositor",
              "amount", "bank", "vacct", "deposit_type"]


def save_csv(deposits: list[Deposit], path: str) -> None:
    import csv
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for d in deposits:
            w.writerow(asdict(d))
    log(f"CSV 저장: {path} ({len(deposits)}건)")


def sync_api(deposits: list[Deposit]) -> None:
    import requests
    payload = [asdict(d) for d in deposits]
    log(f"API 전송: {len(payload)}건 → {config.API_SYNC_URL}")
    resp = requests.post(config.API_SYNC_URL, json=payload, timeout=30)
    log(f"API 응답: {resp.status_code}")
    resp.raise_for_status()


# ════════════════════════════════════════════════════════════════
#  메인
# ════════════════════════════════════════════════════════════════
def deliver(deposits: list[Deposit]) -> None:
    """파싱 결과를 CSV·(선택)API·(선택)구글시트로 내보낸다."""
    save_csv(deposits, config.OUTPUT_CSV)
    if getattr(config, "ENABLE_API_SYNC", False):
        sync_api(deposits)
    if getattr(config, "ENABLE_SHEETS_SYNC", False):
        try:
            from sheets_sync import push_deposits
            push_deposits(deposits)
        except Exception as e:
            log(f"[경고] 구글 시트(더빌_입금내역) 전송 건너뜀: {e}")
    if getattr(config, "ENABLE_OPS_SYNC", False):
        try:
            from ops_sync import push_deposits as ops_push
            ops_push(deposits)
        except Exception as e:
            log(f"[경고] OPS 탭 전송 건너뜀: {e}")


def run_full() -> None:
    driver = build_driver()
    try:
        login(driver)
        go_to_deposit_inquiry(driver)
        xls_path = search_and_download(driver)
        deposits = parse_deposits(xls_path)
        deliver(deposits)
    finally:
        driver.quit()


def main() -> None:
    ap = argparse.ArgumentParser(description="더빌 입금내역 크롤러")
    ap.add_argument("--parse-only", metavar="XLS", help="다운로드 없이 기존 엑셀 파일만 파싱")
    args = ap.parse_args()

    if args.parse_only:
        deposits = parse_deposits(args.parse_only)
        deliver(deposits)
        for d in deposits[:10]:
            print("  ", d)
    else:
        run_full()


if __name__ == "__main__":
    main()
