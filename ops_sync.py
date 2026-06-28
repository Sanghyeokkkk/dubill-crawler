"""OPS 메인 시트('더빌 입금 자동화(서브 테스트)' 탭) 자동 기입 모듈.

더빌 입금내역을 OPS 시트의 컬럼 구조에 맞춰 새 행으로 추가한다.
 - 고객명(예: '세종대점305') → 지점명/호수로 분리
 - 출금계좌성명 → 현 입주자(D) + 계좌상 입금표기(J)
 - 청구월(2026-06) → 귀속 월(26년 6월)
중복은 (지점+호수+입금일+금액+입금자) 기준으로 자동 제거.

탭 구조 (2행 헤더, 데이터는 3행부터):
 A 중복데이터개 | B 지점명 | C 호수 | D 현입주자 | E 실월세 | F 귀속월
 | G 입금일 | H 실입금액 | I 입금출처 | J 특이사항(계좌상입금표기) | K 입금상태 | L 상세내용

단독 실행(테스트):
    python ops_sync.py            # deposits.csv 전체 적재
    python ops_sync.py --limit 3  # 앞 3건만 적재(소량 테스트)
"""
from __future__ import annotations

import argparse
import csv
import re

import gspread
from google.oauth2.service_account import Credentials

import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HEADER_ROWS = 2          # 1행=병합제목, 2행=헤더
LAST_COL = "L"           # A~L 까지만 기록 (M,N 운영열은 손대지 않음)


def _ws():
    creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_JSON, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(config.SPREADSHEET_URL)
    # 1순위: gid(고유 ID)로 찾기 → 탭 이름이 바뀌어도 안전
    gid = getattr(config, "OPS_WORKSHEET_GID", None)
    if gid is not None:
        try:
            return sh.get_worksheet_by_id(gid)
        except Exception:
            pass  # gid 로 못 찾으면 이름으로 폴백
    return sh.worksheet(config.OPS_WORKSHEET_NAME)


# ── 변환 헬퍼 ────────────────────────────────────────────
def split_customer(customer: str) -> tuple[str, str]:
    """'세종대점305' → ('세종대점','305'). '점'이 없으면 전체를 지점명으로."""
    c = (customer or "").strip()
    if "점" in c:
        i = c.rfind("점")
        return c[: i + 1], c[i + 1:].strip()
    return c, ""


def billing_label(bm: str) -> str:
    """'2026-06' → '26년 6월'."""
    s = str(bm or "").strip()
    m = re.match(r"(\d{4})-(\d{1,2})", s)
    if m:
        return f"{m.group(1)[2:]}년 {int(m.group(2))}월"
    return s


def _norm_amt(v) -> str:
    return str(v).replace(",", "").replace("원", "").strip()


def _fmt_amt(v) -> str:
    try:
        return f"{int(float(_norm_amt(v))):,}"
    except (ValueError, TypeError):
        return str(v)


def _build_row(paid_at, billing_month, customer, depositor, amount) -> list:
    branch, room = split_customer(customer)
    return [
        paid_at,                     # A 입금일시(더빌 엑셀은 날짜만 제공)
        branch,                      # B 지점명
        room,                        # C 호수
        depositor,                   # D 현 입주자(출금계좌성명)
        "",                          # E 실월세(더빌 없음)
        billing_label(billing_month),  # F 귀속 월
        paid_at,                     # G 입실료/보증금 입금일
        _fmt_amt(amount),            # H 실입금액
        "CMS",                       # I 입금출처
        depositor,                   # J 특이사항(계좌상 입금표기)
        "",                          # K 입금상태
        "",                          # L 상세내용
    ]


# ── 중복 판정 키: 지점|호수|입금일|금액|입금자 ─────────────
def _key(row: list) -> str:
    def at(i):
        return row[i] if i < len(row) else ""
    return "|".join([at(1), at(2), at(6), _norm_amt(at(7)), at(9)])


def push_rows(rows: list[list]) -> int:
    ws = _ws()
    # 실제 데이터 끝은 '지점명'(B열) 기준으로 판정 (A열 등 멀리 떨어진 값/수식 영향 배제)
    branch_col = ws.col_values(2)
    last = len(branch_col)                       # 마지막 데이터 행(1-based)
    existing = ws.get_values(f"A3:{LAST_COL}{last}") if last >= 3 else []
    seen = {_key(r) for r in existing if len(r) > 1 and r[1]}

    new_rows = [r for r in rows if _key(r) not in seen]
    if new_rows:
        start = last + 1                         # 마지막 데이터 바로 아래
        rng = f"A{start}:{LAST_COL}{start + len(new_rows) - 1}"
        ws.update(range_name=rng, values=new_rows, value_input_option="RAW")
    print(f"[OPS탭] 전체 {len(rows)}건 중 신규 {len(new_rows)}건 추가 (기존 {len(seen)}건).")
    return len(new_rows)


def push_deposits(deposits) -> int:
    rows = [_build_row(d.paid_at, d.billing_month, d.customer, d.depositor, d.amount)
            for d in deposits]
    return push_rows(rows)


def push_csv(path: str, limit: int | None = None) -> int:
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(_build_row(r.get("paid_at", ""), r.get("billing_month", ""),
                                   r.get("customer", ""), r.get("depositor", ""),
                                   r.get("amount", "")))
    if limit:
        rows = rows[:limit]
    return push_rows(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="앞 N건만 적재(테스트용)")
    args = ap.parse_args()
    print(f"CSV 읽기: {config.OUTPUT_CSV}")
    push_csv(config.OUTPUT_CSV, limit=args.limit)
