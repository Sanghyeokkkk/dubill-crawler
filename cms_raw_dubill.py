"""더빌(가상계좌) 입금 → 'PMS pro' 문서의 CMS_RAW 탭 적재.

로카 보증금(cms_raw_sync.py)과 같은 CMS_RAW 탭을 공유한다. 이 탭엔
 - 더빌 가상계좌 행 (입금구분='가상계좌')  ← 이 모듈이 담당
 - 로카 보증금 행 (입금구분='로카 계좌')  ← cms_raw_sync.py 가 담당
가 함께 쌓인다.

★ 열 위치를 하드코딩하지 않고 매번 헤더를 이름으로 찾는다.
  (정산일·가상계좌은행 열이 삭제되어도 안 깨지도록)
★ 마지막 데이터 행은 '어느 칸이든 값 있으면' 기준으로 찾는다 → 고객명·청구월이
  빈 보증금 행 위에 절대 덮어쓰지 않는다.
★ 쓰기 직전 대상 구간이 비었는지 재확인, 아니면 중단.

실행:
    python cms_raw_dubill.py            # 미리보기 (더빌_입금내역 소스)
    python cms_raw_dubill.py --apply    # 실제 기재
"""
from __future__ import annotations

import argparse

import gspread
from google.oauth2.service_account import Credentials

import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# 더빌 필드 → CMS_RAW 헤더 이름 (헤더에 없는 이름은 자동으로 건너뜀)
FIELD_TO_HEADER = [
    ("paid_at", "입금일시"),
    ("billing_month", "청구월"),
    ("customer", "고객명"),
    ("depositor", "출금계좌성명"),
    ("amount", "입금금액"),
    ("vacct", "가상계좌번호"),
    ("deposit_type", "입금구분"),
]
# 중복 판정에 쓰는 헤더들 (존재하는 것만 사용)
KEY_HEADERS = ["입금일시", "고객명", "출금계좌성명", "입금금액", "가상계좌번호"]


def _norm(v) -> str:
    return str(v).replace(",", "").replace("원", "").strip()


def _num_amt(v):
    try:
        return int(float(_norm(v)))
    except (ValueError, TypeError):
        return v


def _col_letter(n):
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(ord("A") + r) + s
    return s


def _open_ws():
    creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_JSON, scopes=SCOPES)
    gc = gspread.authorize(creds)
    url = getattr(config, "CMS_SPREADSHEET_URL", "")
    sh = gc.open_by_url(url) if url else gc.open_by_key(config.CMS_RAW_KEY)
    return sh.get_worksheet_by_id(config.CMS_RAW_GID)


def _positions(header):
    return {h.strip(): i for i, h in enumerate(header)}


def _key(row, pos):
    parts = []
    for name in KEY_HEADERS:
        i = pos.get(name)
        parts.append(_norm(row[i]) if (i is not None and i < len(row)) else "")
    return "|".join(parts)


def push(deposits, apply=False) -> int:
    """deposits: dict 또는 (paid_at,billing_month,customer,depositor,amount,vacct,deposit_type) 접근 가능한 객체 리스트."""
    ws = _open_ws()
    vals = ws.get_all_values()
    if not vals:
        raise RuntimeError("CMS_RAW 헤더를 읽지 못했습니다.")
    header = vals[0]
    pos = _positions(header)
    width = len(header)

    # 필수 헤더 확인
    for _, name in FIELD_TO_HEADER:
        if name in ("정산일", "가상계좌은행"):
            continue
    if "입금일시" not in pos or "입금구분" not in pos:
        raise RuntimeError(f"CMS_RAW 헤더가 예상과 다릅니다: {header}")

    # 기존 키 수집(모든 행). 보증금 행은 고객명/가상계좌번호가 비어 키가 달라 충돌 안 함.
    seen = set()
    for r in vals[1:]:
        if any(str(c).strip() for c in r[:width]):
            seen.add(_key(r, pos))

    # 마지막 데이터 행: 어느 칸이든 값 있으면 데이터로 간주(보증금 행 포함)
    last = 1
    for i, r in enumerate(vals, start=1):
        if i == 1:
            continue
        if any(str(c).strip() for c in r[:width]):
            last = i

    def getf(d, f):
        return d[f] if isinstance(d, dict) else getattr(d, f)

    new_rows, preview = [], []
    for d in deposits:
        row = [""] * width
        for f, name in FIELD_TO_HEADER:
            if name not in pos:
                continue
            val = getf(d, f)
            if name == "입금금액":
                val = _num_amt(val)
            if name == "입금구분" and not str(val).strip():
                val = "가상계좌"
            row[pos[name]] = val
        k = _key(row, pos)
        if k in seen:
            continue
        seen.add(k)
        new_rows.append(row)
        preview.append((getf(d, "paid_at"), getf(d, "customer"), getf(d, "depositor"),
                        getf(d, "amount")))

    print(f"[CMS_RAW·더빌] 신규 {len(new_rows)}건 (총입력 {len(deposits)}건)")
    for p in preview[:15]:
        print("   +", p)

    if apply and new_rows:
        start, end = last + 1, last + len(new_rows)
        rng = f"A{start}:{_col_letter(width - 1)}{end}"
        target = ws.get_values(rng)
        if any(any(str(c).strip() for c in row) for row in target):
            raise RuntimeError(f"[중단] CMS_RAW {start}~{end} 행에 데이터가 있어 덮어쓰기를 막음.")
        ws.update(range_name=rng, values=new_rows, value_input_option="USER_ENTERED")
        print(f"✅ CMS_RAW {rng} 에 {len(new_rows)}건 기재 완료 (보증금 행은 안 건드림).")
    elif not apply:
        print("※ 미리보기입니다. 실제 기재: python cms_raw_dubill.py --apply")
    return len(new_rows)


def push_deposits(deposits, apply=True) -> int:
    """크롤러에서 Deposit 객체 리스트로 호출."""
    return push(deposits, apply=apply)


def _load_from_dubill():
    """테스트/백필용: 더빌_입금내역 탭에서 읽어 dict 리스트로."""
    creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_JSON, scopes=SCOPES)
    sh = gspread.authorize(creds).open_by_url(config.SPREADSHEET_URL)
    v = sh.worksheet(config.WORKSHEET_NAME).get_all_values()
    idx = {h.strip(): i for i, h in enumerate(v[0])}
    out = []
    for r in v[1:]:
        if not r[idx.get("고객명", 0)].strip():
            continue
        out.append({
            "paid_at": r[idx.get("입금일시", -1)] if idx.get("입금일시", -1) >= 0 else "",
            "billing_month": r[idx.get("청구월", -1)] if idx.get("청구월", -1) >= 0 else "",
            "customer": r[idx.get("고객명", -1)] if idx.get("고객명", -1) >= 0 else "",
            "depositor": r[idx.get("출금계좌성명", -1)] if idx.get("출금계좌성명", -1) >= 0 else "",
            "amount": r[idx.get("입금금액", -1)] if idx.get("입금금액", -1) >= 0 else "",
            "vacct": r[idx.get("가상계좌번호", -1)] if idx.get("가상계좌번호", -1) >= 0 else "",
            "deposit_type": r[idx.get("입금구분", -1)] if idx.get("입금구분", -1) >= 0 else "",
        })
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    push(_load_from_dubill(), apply=args.apply)
