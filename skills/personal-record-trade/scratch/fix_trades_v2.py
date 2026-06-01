import gspread
import sys
import datetime

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws_log = ss.worksheet("📒 매매일지")

# Delete rows with 1360 exchange rate assumption
all_records = ws_log.get_all_values()
rows_to_delete = []
for i, row in enumerate(all_records):
    # row is 0-indexed, Google sheets is 1-indexed
    # memo is the 15th column (index 14) usually, but let's just check the whole row string
    if "1360원" in str(row):
        rows_to_delete.append(i + 1)

# Delete in reverse order to not mess up indices
for r in reversed(rows_to_delete):
    print(f"Deleting row {r}")
    ws_log.delete_rows(r)

exchange_rate = 1515.79
trades = [
    {"date": "2026-05-21", "ticker": "UNH", "name": "유나이티드헬스 그룹", "type": "매수", "qty": 21, "price": int(381.37 * exchange_rate), "amount": int(21 * 381.37 * exchange_rate), "memo": f"환율 {exchange_rate:,.2f}원 적용 (단가 $381.37)"},
    {"date": "2026-05-21", "ticker": "META", "name": "메타 플랫폼스", "type": "매수", "qty": 5, "price": int(603.00 * exchange_rate), "amount": int(5 * 603.00 * exchange_rate), "memo": f"환율 {exchange_rate:,.2f}원 적용 (단가 $603.00)"},
    {"date": "2026-05-21", "ticker": "BRKb", "name": "버크셔 해서웨이 B", "type": "매수", "qty": 4, "price": int(481.00 * exchange_rate), "amount": int(4 * 481.00 * exchange_rate), "memo": f"환율 {exchange_rate:,.2f}원 적용 (단가 $481.00)"},
    {"date": "2026-05-21", "ticker": "AAPL", "name": "애플", "type": "매수", "qty": 4, "price": int(301.25 * exchange_rate), "amount": int(4 * 301.25 * exchange_rate), "memo": f"환율 {exchange_rate:,.2f}원 적용 (단가 $301.25)"}
]

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

print("Fix completed successfully!")
