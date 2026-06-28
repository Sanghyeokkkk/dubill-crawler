"""구글 시트 자동 입력 모듈 (gspread + 서비스 계정).

입금내역(Deposit 리스트 또는 deposits.csv)을 구글 시트에 추가한다.
이미 들어있는 행은 (입금일시+입금자명+금액) 기준으로 건너뛴다(중복 방지).

준비물: 구글 서비스 계정 키(JSON) + 대상 시트를 서비스계정 이메일과 공유.
        자세한 설정은 'GOOGLE_SHEETS_설정가이드.md' 참고.

단독 실행(테스트):
    python sheets_sync.py            # deposits.csv 를 시트에 올림
"""
from __future__ import annotations

import csv
import os

import gspread
from google.oauth2.service_account import Credentials

import config

# '더빌_입금내역' 탭 헤더 (더빌 엑셀 컬럼 기준, 등록구분은 가상계좌번호와 중복이라 제외)
HEADER = ["입금일시", "청구월", "정산일", "고객명", "출금계좌성명",
          "입금금액", "가상계좌은행", "가상계좌번호", "입금구분"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _client() -> gspread.Client:
    if not os.path.exists(config.SERVICE_ACCOUNT_JSON):
        raise FileNotFoundError(
            f"서비스 계정 키가 없습니다: {config.SERVICE_ACCOUNT_JSON}\n"
            "      GOOGLE_SHEETS_설정가이드.md 를 보고 JSON 키를 내려받아 두세요."
        )
    creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_JSON, scopes=SCOPES)
    return gspread.authorize(creds)


def _open_worksheet(gc: gspread.Client):
    if not config.SPREADSHEET_URL or "여기에" in config.SPREADSHEET_URL:
        raise ValueError("config.py 의 SPREADSHEET_URL 에 구글 시트 주소를 넣어주세요.")
    sh = gc.open_by_url(config.SPREADSHEET_URL)
    try:
        ws = sh.worksheet(config.WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=config.WORKSHEET_NAME, rows=2000, cols=len(HEADER) + 2)
    # 헤더 보장 (A1:H1)
    last_col = chr(ord("A") + len(HEADER) - 1)  # H
    rng = f"A1:{last_col}1"
    if ws.get_values(rng) != [HEADER]:
        ws.update(values=[HEADER], range_name=rng)
    return ws


def _key(row: list) -> str:
    """중복 판정 키: 입금일시|고객명|출금계좌성명|입금금액|가상계좌번호."""
    def at(i):
        return row[i] if i < len(row) else ""
    return "|".join(str(at(i)) for i in (0, 3, 4, 5, 7))


def push_rows(rows: list[list]) -> int:
    """HEADER 순서의 행들을 시트에 추가. 신규 건수 반환."""
    gc = _client()
    ws = _open_worksheet(gc)

    existing = ws.get_all_values()[1:]  # 헤더 제외
    seen = {_key(r) for r in existing if len(r) >= 5}

    new_rows = [r for r in rows if _key(r) not in seen]
    if new_rows:
        ws.append_rows(new_rows, value_input_option="USER_ENTERED")
    print(f"[구글시트] 전체 {len(rows)}건 중 신규 {len(new_rows)}건 추가 (기존 {len(seen)}건).")
    return len(new_rows)


def _row_from_deposit(d) -> list:
    # HEADER 순서: 입금일시,청구월,정산일,고객명,출금계좌성명,입금금액,가상계좌은행,가상계좌번호,입금구분
    return [d.paid_at, d.billing_month, d.settle_date, d.customer, d.depositor,
            d.amount, d.bank, d.vacct, d.deposit_type]


def push_deposits(deposits) -> int:
    """Deposit 데이터클래스 리스트를 시트에 추가."""
    return push_rows([_row_from_deposit(d) for d in deposits])


def push_csv(path: str) -> int:
    """deposits.csv 를 읽어 시트에 추가."""
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append([r.get("paid_at", ""), r.get("billing_month", ""), r.get("settle_date", ""),
                         r.get("customer", ""), r.get("depositor", ""), r.get("amount", ""),
                         r.get("bank", ""), r.get("vacct", ""), r.get("deposit_type", "")])
    return push_rows(rows)


if __name__ == "__main__":
    path = config.OUTPUT_CSV
    print(f"CSV 읽기: {path}")
    push_csv(path)
