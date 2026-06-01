import gspread
import sys
import datetime

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws_portfolio = ss.worksheet('📊 포트폴리오')
ws_closed = ss.worksheet('👋 청산종목')

port_records = ws_portfolio.get_all_values()

# Target ticker
target_ticker = '461900'
row_idx = None
target_row = None

for i, row in enumerate(port_records):
    if len(row) > 3 and row[2] == target_ticker:
        row_idx = i + 1
        target_row = row
        break

if row_idx is None:
    print(f"Ticker {target_ticker} not found in portfolio.")
    sys.exit(1)

# Extract data for 👋 청산종목
# ['종목명', '진입가설(요약)', '진입근거', '매수가', '목표가', '하방', '매도완료일', '보유기간(일)', '실현손익', '수익률', '사후평가\n(1~10)', '인지오류', '해결전략', '재매매의향']
# target_row: ['A-', '달러', '461900', 'PLUS TOP 10 US Tech Company', 'KRX:461900', 'AI 인프라', '코어', '0', '25,500.0', '25,500', '18,971', '29,733,000', '22,120,186', '7,612,814', '34.42%']

name = target_row[3]
buy_price = target_row[10]
realized_profit = target_row[13]
return_rate = target_row[14]
sell_date = "2026-06-01"

new_closed_row = [
    name,
    "", # 진입가설
    "", # 진입근거
    buy_price, # 매수가
    "", # 목표가
    "", # 하방
    sell_date, # 매도완료일
    "", # 보유기간
    realized_profit, # 실현손익
    return_rate, # 수익률
    "", # 사후평가
    "", # 인지오류
    "", # 해결전략
    ""  # 재매매의향
]

# 1. Add to closed positions
ws_closed.append_row(new_closed_row, value_input_option="USER_ENTERED")
print(f"Added {name} to 👋 청산종목")

# 2. Delete from portfolio
ws_portfolio.delete_rows(row_idx)
print(f"Deleted {name} (Row {row_idx}) from 📊 포트폴리오")
