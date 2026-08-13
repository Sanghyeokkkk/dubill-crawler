"""CMS_RAW 탭(PMS pro 시트) 자동 기재 — ⑦탭과 동일 구조로 더빌 입금내역 적재.

컬럼(⑦ 구조):
 A 중복데이터개 | B 지점명 | C 호수 | D 현입주자 | E 입금일 | F 금액
 | G 입금출처 | H 특이사항(계좌상입금표기) | I 귀속월 | J 상세내용
채우는 열: B~I  (A 중복데이터·J 상세내용은 비움)
현입주자(D): PMS pro의 'data' 탭에서 (지점명,호실)→고객명, 없으면 출금계좌성명.
중복판정: 지점|호수|입금일|금액.

★ 안전장치(지난 덮어쓰기 사고 반영):
  - 마지막 데이터 행을 B~H 어느 칸이든 값 있으면 데이터로 간주(끝까지 스캔)
  - 쓰기 직전 대상 구간이 비었는지 재확인, 아니면 중단

실행:
    python cms_raw_sync.py            # 미리보기(실제 안 씀)
    python cms_raw_sync.py --apply    # 실제 기재
"""
from __future__ import annotations

import argparse
import re

import gspread
from google.oauth2.service_account import Credentials

import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HEADER = ["중복데이터  개", "지점명", "호수", "현 입주자", "입실료/보증금 입금일",
          "금액", "입금출처", "특이사항(계좌상 입금표기)", "귀속 월", "상세내용"]


def _open():
    creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_JSON, scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(config.CMS_RAW_KEY)


def _norm(v) -> str:
    return str(v).replace(",", "").replace("원", "").strip()


def _num_amt(v):
    try:
        return int(float(_norm(v)))
    except (ValueError, TypeError):
        return v


def _split(customer: str):
    c = (customer or "").strip()
    if "점" in c:
        i = c.rfind("점")
        return c[: i + 1], c[i + 1:].strip()
    return c, ""


def _base(branch, date, amount) -> str:
    return f"{str(branch).strip()}|{str(date).strip()}|{_norm(amount)}"


def _billing_label(bm: str) -> str:
    s = str(bm or "").strip()
    m = re.match(r"(\d{4})-(\d{1,2})", s)
    if m:
        return f"{m.group(1)[2:]}년 {int(m.group(2))}월"
    return s


def _names(sh) -> dict:
    """PMS pro 'data' 탭: (지점명,호실) → 고객명."""
    try:
        ws = sh.get_worksheet_by_id(config.CMS_RAW_DATA_GID)
        vals = ws.get_all_values()
    except Exception:
        return {}
    BRANCH, ROOM, NAME = 1, 2, 4   # B 지점명, C 호실, E 고객명
    d = {}
    for r in vals[1:]:             # 2행부터
        if len(r) > NAME and r[BRANCH].strip():
            nm = r[NAME].strip()
            if nm:
                d[(r[BRANCH].strip(), str(r[ROOM]).strip())] = nm
    return d


def push(deposits, apply=False) -> int:
    """deposits: [(paid_at, billing_month, customer, depositor, amount), ...]."""
    sh = _open()
    ws = sh.get_worksheet_by_id(config.CMS_RAW_GID)
    names = _names(sh)
    vals = ws.get_all_values()

    # 헤더 보장 (⑦ 구조). CMS_RAW는 원래 raw 헤더라 다르면 교체.
    if not vals or [c.strip() for c in vals[0][:len(HEADER)]] != HEADER:
        ws.update(range_name="A1:J1", values=[HEADER], value_input_option="RAW")
        print("[CMS_RAW] 헤더를 ⑦ 구조로 설정함.")
        vals = ws.get_all_values()

    # 중복판정: 지점(B)|입금일(E)|금액(F)|호수(C)
    seen = set()
    for r in vals[1:]:
        if len(r) > 5 and r[1].strip():
            seen.add(_base(r[1], r[4], r[5]) + "|" + str(r[2]).strip())

    # 마지막 데이터 행: B~H 어느 칸이든 값 있으면 데이터로 간주(끝까지 스캔)
    last = 1
    for i, r in enumerate(vals, start=1):
        if i == 1:
            continue
        if any(str(c).strip() for c in r[1:8]):
            last = i

    new_rows, preview = [], []
    for paid_at, billing_month, customer, depositor, amount in deposits:
        b, room = _split(customer)
        key = _base(b, paid_at, amount) + "|" + room.strip()
        if key in seen:
            continue
        seen.add(key)
        tenant = names.get((b.strip(), room.strip())) or depositor
        # B~I: 지점,호수,현입주자,입금일,금액,입금출처,특이사항,귀속월
        new_rows.append([b, room, tenant, paid_at, _num_amt(amount), "CMS",
                         depositor, _billing_label(billing_month)])
        preview.append((b, room, tenant, paid_at, amount))

    print(f"[CMS_RAW] 신규 {len(new_rows)}건 (총입력 {len(deposits)}건, 기존행 {len(seen) - len(new_rows)})")
    for p in preview[:20]:
        print("   +", p)

    if apply and new_rows:
        start = last + 1
        end = start + len(new_rows) - 1
        target = ws.get_values(f"A{start}:J{end}")
        if any(any(str(c).strip() for c in row) for row in target):
            raise RuntimeError(f"[중단] CMS_RAW {start}~{end} 행에 데이터가 있어 덮어쓰기를 막음.")
        ws.update(range_name=f"B{start}:I{end}", values=new_rows,
                  value_input_option="USER_ENTERED")
        print(f"✅ CMS_RAW B{start}:I{end} 에 {len(new_rows)}건 기재 완료.")
    elif not apply:
        print("※ 미리보기만 했습니다. 실제 기재: python cms_raw_sync.py --apply")
    return len(new_rows)


def push_deposits(deposits, apply=True) -> int:
    data = [(d.paid_at, d.billing_month, d.customer, d.depositor, d.amount) for d in deposits]
    return push(data, apply=apply)


def _load_from_dubill():
    """테스트용: OPS 시트의 더빌_입금내역 탭에서 입금 읽어오기."""
    creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_JSON, scopes=SCOPES)
    sh = gspread.authorize(creds).open_by_url(config.SPREADSHEET_URL)
    v = sh.worksheet(config.WORKSHEET_NAME).get_all_values()
    h = v[0]
    def ci(n):
        for i, x in enumerate(h):
            if x.strip() == n:
                return i
        return -1
    ic, ibm, idt, idep, ia = ci("고객명"), ci("청구월"), ci("입금일시"), ci("출금계좌성명"), ci("입금금액")
    out = []
    for r in v[1:]:
        if len(r) > max(ic, idt, ia) and r[ic].strip():
            out.append((r[idt], r[ibm], r[ic], r[idep], r[ia]))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    push(_load_from_dubill(), apply=args.apply)
