import gspread
import os
import sys

BASE_DIR = r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade"
sys.path.append(BASE_DIR)
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
sid = get_sheet_id()
ss = gc.open_by_key(sid)

# 1. 환율 가져오기
ws_rt = ss.worksheet("📈 실시간현황")
exchange_rate_str = ws_rt.acell('B2').value
print(f"환율: {exchange_rate_str}")
try:
    exchange_rate = float(exchange_rate_str.replace(',', ''))
except:
    exchange_rate = 1360.0
    print("환율 파싱 실패, 1360으로 폴백")

# 2. 마지막 4개 거래 삭제
ws_log = ss.worksheet("📒 매매일지")
all_records = ws_log.get_all_values()
num_rows = len(all_records)
# 삭제할 행은 마지막 4행
print(f"매매일지 총 행 수: {num_rows}, 마지막 4행 삭제 예정")
ws_log.delete_rows(num_rows - 3, num_rows)

# 3. 새로운 거래 추가
trades = [
    {"date": "2026-05-21", "ticker": "UNH", "name": "유나이티드헬스 그룹", "type": "매수", "qty": 21, "price": int(381.37 * exchange_rate), "amount": int(21 * 381.37 * exchange_rate), "memo": f"환율 {exchange_rate:,.2f}원 적용 (단가 $381.37)"},
    {"date": "2026-05-21", "ticker": "META", "name": "메타 플랫폼스", "type": "매수", "qty": 5, "price": int(603.00 * exchange_rate), "amount": int(5 * 603.00 * exchange_rate), "memo": f"환율 {exchange_rate:,.2f}원 적용 (단가 $603.00)"},
    {"date": "2026-05-21", "ticker": "BRKb", "name": "버크셔 해서웨이 B", "type": "매수", "qty": 4, "price": int(481.00 * exchange_rate), "amount": int(4 * 481.00 * exchange_rate), "memo": f"환율 {exchange_rate:,.2f}원 적용 (단가 $481.00)"},
    {"date": "2026-05-21", "ticker": "AAPL", "name": "애플", "type": "매수", "qty": 4, "price": int(301.25 * exchange_rate), "amount": int(4 * 301.25 * exchange_rate), "memo": f"환율 {exchange_rate:,.2f}원 적용 (단가 $301.25)"}
]

import datetime
def parse_trade(raw: dict) -> list:
    today = datetime.date.today().isoformat()
    return [
        raw.get("date", today),
        raw.get("ticker", ""),
        raw.get("name", ""),
        raw.get("type", ""),
        raw.get("qty", ""),
        raw.get("price", ""),
        raw.get("amount", ""),
        raw.get("reason", ""),
        raw.get("timing", ""),
        raw.get("score", ""),
        raw.get("analysis", ""),
        raw.get("condition", ""),
        raw.get("bias", ""),
        raw.get("fix", ""),
        raw.get("memo", ""),
    ]

for t in trades:
    row = parse_trade(t)
    ws_log.append_row(row, value_input_option="USER_ENTERED")
    print(f"Added corrected trade: {t['name']}")

print("완료")
