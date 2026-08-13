"""⑦[운영팀] 입실자_입실료 보증금 확인 탭 자동 기재 (수동 입력 대체).

크롤러가 받은 더빌 입금을 이 탭에 새 행으로 추가한다.
채우는 열: B 지점명 · C 호수 · D 현입주자 · E 입금일 · F 금액 · G 입금출처 · H 특이사항
비우는 열: A(중복데이터), I(귀속월=수기), J~N(운영/버튼/참조) → 건드리지 않음

중복 판정: 지점|호수|입금일|금액 (이미 있는 입금은 추가 안 함)

실행:
    python tab7_sync.py            # 미리보기(실제 안 씀)
    python tab7_sync.py --apply    # 실제 기재
"""
from __future__ import annotations

import argparse
import re

import gspread
from google.oauth2.service_account import Credentials

import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _open():
    creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_JSON, scopes=SCOPES)
    return gspread.authorize(creds).open_by_url(config.SPREADSHEET_URL)


def _ws(sh, gid, name):
    if gid is not None:
        try:
            return sh.get_worksheet_by_id(gid)
        except Exception:
            pass
    return sh.worksheet(name)


def _crm_names(sh) -> dict:
    """① CRM(PMS_입주)에서 (지점,호수) → 이름(N열) 조회표. 헤더 3행, 데이터 4행부터."""
    try:
        ws = _ws(sh, getattr(config, "CRM_GID", None), getattr(config, "CRM_NAME", ""))
        vals = ws.get_all_values()
    except Exception:
        return {}
    BRANCH, ROOM, NAME = 0, 1, 13   # A 지점명, B 호수, N 이름
    d = {}
    for r in vals[3:]:               # 4행부터 데이터
        if len(r) > NAME and r[BRANCH].strip():
            name = r[NAME].strip()
            if name:
                d[(r[BRANCH].strip(), str(r[ROOM]).strip())] = name
    return d


def _norm(v) -> str:
    return str(v).replace(",", "").replace("원", "").strip()


def _split(customer: str) -> tuple[str, str]:
    c = (customer or "").strip()
    if "점" in c:
        i = c.rfind("점")
        return c[: i + 1], c[i + 1:].strip()
    return c, ""


def _base(branch, date, amount) -> str:
    """중복 판정 기준(공통): 지점|입금일|금액."""
    return f"{str(branch).strip()}|{str(date).strip()}|{_norm(amount)}"


def _num_amt(v):
    try:
        return int(float(_norm(v)))
    except (ValueError, TypeError):
        return v


def _load_deposits_from_csv(path):
    import csv
    out = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out.append((r.get("paid_at", ""), r.get("customer", ""),
                        r.get("depositor", ""), r.get("amount", "")))
    return out


def push(deposits, apply=False) -> int:
    """deposits: [(paid_at, customer, depositor, amount), ...] 형태. 신규 추가 건수 반환."""
    sh = _open()
    ws = _ws(sh, getattr(config, "TAB7_GID", None), getattr(config, "TAB7_NAME", ""))
    crm = _crm_names(sh)   # (지점,호수) → 이름
    vals = ws.get_all_values()

    # 중복판정: (지점|입금일|금액)이 같고 '호수' 또는 '입금자표기'가 같으면 중복.
    #  → 더빌 등록 호수와 실제 방 호수가 달라도(예: 강준구 309→304) 입금자표기로 잡음.
    # 중복판정: (지점|호수|입금일|금액). 같은 법인이 여러 방에 같은 금액을 내도
    #   (예: 롯데건설 207/306/410) 호수가 달라 각각 유지된다.
    seen_room = set()
    for r in vals[1:]:
        if len(r) > 5 and r[1].strip():
            seen_room.add(_base(r[1], r[4], r[5]) + "|" + str(r[2]).strip())

    # 마지막 데이터 행: B~H 어느 칸이든 값이 있으면 데이터 행으로 본다(끝까지 스캔).
    #   ★ 지점명이 빈 '방배정 전 보증금' 행도 반드시 포함 → 그 위에 절대 덮어쓰지 않음.
    last = 2
    for i, r in enumerate(vals, start=1):
        if i <= 2:
            continue
        if any(str(c).strip() for c in r[1:8]):   # B~H
            last = i

    new_rows, preview = [], []
    for paid_at, customer, depositor, amount in deposits:
        b, room = _split(customer)
        key = _base(b, paid_at, amount) + "|" + room.strip()
        if key in seen_room:
            continue
        seen_room.add(key)
        # 현입주자(D): CRM(지점,호수) 이름 우선, 없으면 출금계좌성명으로 폴백
        tenant = crm.get((b.strip(), room.strip())) or depositor
        # B~H (7열): 지점,호수,현입주자,입금일,금액,입금출처,특이사항
        new_rows.append([b, room, tenant, paid_at, _num_amt(amount), "CMS", depositor])
        preview.append((b, room, tenant, paid_at, amount, "CRM" if crm.get((b.strip(), room.strip())) else "폴백"))

    print(f"[⑦탭] 신규 대상 {len(new_rows)}건 (총입력 {len(deposits)}건 중, 기존행 {len(seen_room)})")
    for p in preview[:20]:
        print("   +", p)

    if apply and new_rows:
        start = last + 1
        end = start + len(new_rows) - 1
        # ★ 안전장치: 쓰기 직전 대상 구간(A~L)이 비었는지 재확인. 비어있지 않으면 덮어쓰지 않고 중단.
        target = ws.get_values(f"A{start}:L{end}")
        if any(any(str(c).strip() for c in row) for row in target):
            raise RuntimeError(
                f"[중단] ⑦탭 {start}~{end} 행에 이미 데이터가 있어 덮어쓰기를 막았습니다. "
                f"동시 편집/누락행 가능성 — 수동 확인 필요."
            )
        ws.update(range_name=f"B{start}:H{end}", values=new_rows,
                  value_input_option="USER_ENTERED")
        print(f"✅ ⑦탭 B{start}:H{end} 에 {len(new_rows)}건 기재 완료 (귀속월 I열은 수기).")
    elif not apply:
        print("※ 미리보기만 했습니다. 실제 기재: python tab7_sync.py --apply")
    return len(new_rows)


def push_deposits(deposits, apply=True) -> int:
    """크롤러에서 Deposit 객체 리스트로 호출."""
    data = [(d.paid_at, d.customer, d.depositor, d.amount) for d in deposits]
    return push(data, apply=apply)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    push(_load_deposits_from_csv(config.OUTPUT_CSV), apply=args.apply)
