"""CMS_RAW 탭(PMS pro 시트) 자동 기재 — 더빌 원본(raw) 형식으로 입금내역 적재.

CMS_RAW 헤더(raw):
 A 입금일시 | B 청구월 | C 정산일 | D 고객명 | E 출금계좌성명 | F 입금금액
 | G 가상계좌은행 | H 가상계좌번호 | I 입금구분
→ 우리 '더빌_입금내역' 탭과 동일 구조. 크롤링한 더빌 데이터를 그대로 적재.

중복판정: 입금일시|고객명|출금계좌성명|입금금액|가상계좌번호 (콤마 무시).

★ 안전장치: 마지막 데이터 행을 A~I 어느 칸이든 값 있으면 데이터로 간주(끝까지 스캔),
  쓰기 직전 대상 구간이 비었는지 재확인 후 아니면 중단(덮어쓰기 차단).

실행:
    python cms_raw_sync.py            # 미리보기
    python cms_raw_sync.py --apply    # 실제 기재
    python cms_raw_sync.py --reset    # (주의) 데이터 비우고 더빌_입금내역 전체로 재적재
"""
from __future__ import annotations

import argparse

import gspread
from google.oauth2.service_account import Credentials

import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HEADER = ["입금일시", "청구월", "정산일", "고객명", "출금계좌성명",
          "입금금액", "가상계좌은행", "가상계좌번호", "입금구분"]


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


def _key(row) -> str:
    """중복키: 입금일시|고객명|출금계좌성명|입금금액|가상계좌번호 (콤마 무시)."""
    def at(i):
        return _norm(row[i]) if i < len(row) else ""
    return "|".join(at(i) for i in (0, 3, 4, 5, 7))


def _ws(sh):
    return sh.get_worksheet_by_id(config.CMS_RAW_GID)


def push(deposits, apply=False) -> int:
    """deposits: [(입금일시,청구월,정산일,고객명,출금계좌성명,입금금액,가상계좌은행,가상계좌번호,입금구분), ...]."""
    sh = _open()
    ws = _ws(sh)
    vals = ws.get_all_values()

    # 헤더 보장(raw). 다르면 맞춤.
    if not vals or [c.strip() for c in vals[0][:len(HEADER)]] != HEADER:
        ws.update(range_name="A1:I1", values=[HEADER], value_input_option="RAW")
        vals = ws.get_all_values()

    seen = set()
    for r in vals[1:]:
        if len(r) >= 5 and r[0].strip():
            seen.add(_key(r))

    # 마지막 데이터 행: A~I 어느 칸이든 값 있으면 데이터로 간주(끝까지 스캔)
    last = 1
    for i, r in enumerate(vals, start=1):
        if i == 1:
            continue
        if any(str(c).strip() for c in r[0:9]):
            last = i

    new_rows = []
    for d in deposits:
        row = [d[0], d[1], d[2], d[3], d[4], _num_amt(d[5]), d[6], d[7], d[8]]
        k = _key(row)
        if k in seen:
            continue
        seen.add(k)
        new_rows.append(row)

    print(f"[CMS_RAW] 신규 {len(new_rows)}건 (총입력 {len(deposits)}건, 기존행 {len(seen) - len(new_rows)})")
    for r in new_rows[:15]:
        print("   +", [r[0], r[3], r[4], r[5], r[8]])

    if apply and new_rows:
        start = last + 1
        end = start + len(new_rows) - 1
        target = ws.get_values(f"A{start}:I{end}")
        if any(any(str(c).strip() for c in row) for row in target):
            raise RuntimeError(f"[중단] CMS_RAW {start}~{end} 행에 데이터가 있어 덮어쓰기를 막음.")
        ws.update(range_name=f"A{start}:I{end}", values=new_rows,
                  value_input_option="USER_ENTERED")
        print(f"✅ CMS_RAW A{start}:I{end} 에 {len(new_rows)}건 기재 완료.")
    elif not apply:
        print("※ 미리보기만 했습니다. 실제 기재: python cms_raw_sync.py --apply")
    return len(new_rows)


def push_deposits(deposits, apply=True) -> int:
    data = [(d.paid_at, d.billing_month, d.settle_date, d.customer, d.depositor,
             d.amount, d.bank, d.vacct, d.deposit_type) for d in deposits]
    return push(data, apply=apply)


def _load_from_dubill():
    """더빌_입금내역 탭 전체를 raw 형식 튜플로 읽기."""
    creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_JSON, scopes=SCOPES)
    sh = gspread.authorize(creds).open_by_url(config.SPREADSHEET_URL)
    v = sh.worksheet(config.WORKSHEET_NAME).get_all_values()
    h = v[0]
    idx = {name: i for i, name in enumerate(c.strip() for c in h)}
    cols = ["입금일시", "청구월", "정산일", "고객명", "출금계좌성명",
            "입금금액", "가상계좌은행", "가상계좌번호", "입금구분"]
    out = []
    for r in v[1:]:
        if not (r[idx["고객명"]].strip() if idx.get("고객명", -1) >= 0 else ""):
            continue
        out.append(tuple(r[idx[c]] if idx.get(c, -1) >= 0 and idx[c] < len(r) else "" for c in cols))
    return out


def reset_and_backfill():
    """(주의) CMS_RAW 데이터를 비우고 더빌_입금내역 전체로 다시 채움."""
    sh = _open()
    ws = _ws(sh)
    vals = ws.get_all_values()
    # A~I 어느 칸이든 값 있으면 데이터로 보고 그 끝까지 비움(어긋난 ⑦ 데이터도 포함)
    last = 1
    for i, r in enumerate(vals, start=1):
        if i == 1:
            continue
        if any(str(c).strip() for c in r[0:9]):
            last = i
    if last >= 2:
        ws.batch_clear([f"A2:I{last}"])
        print(f"[CMS_RAW] 기존 데이터 A2:I{last} 비움.")
    ws.update(range_name="A1:I1", values=[HEADER], value_input_option="RAW")
    return push(_load_from_dubill(), apply=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--reset", action="store_true", help="데이터 비우고 더빌_입금내역 전체로 재적재")
    args = ap.parse_args()
    if args.reset:
        reset_and_backfill()
    else:
        push(_load_from_dubill(), apply=args.apply)
