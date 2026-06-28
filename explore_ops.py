"""OPS 메인 시트 구조 탐색 (읽기 전용)."""
import gspread
from google.oauth2.service_account import Credentials
import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_JSON, scopes=SCOPES)
gc = gspread.authorize(creds)
sh = gc.open_by_url(config.SPREADSHEET_URL)

print("스프레드시트 제목:", sh.title)
print("\n=== 전체 탭 목록 ===")
for ws in sh.worksheets():
    print(f"  - {ws.title!r}  (gid={ws.id}, {ws.row_count}행 x {ws.col_count}열)")

# URL의 gid=938279850 탭 찾기
target = None
for ws in sh.worksheets():
    if ws.id == 938279850:
        target = ws
        break
if target is None:
    target = sh.sheet1

print(f"\n=== 대상 탭: {target.title!r} 상단 행 ===")
rows = target.get_values("A1:N6")
for i, r in enumerate(rows, start=1):
    print(f"[{i}행] {r}")
