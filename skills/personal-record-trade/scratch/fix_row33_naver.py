import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())

# 1. Update NAVER quantity to exactly 34
ws_portfolio = ss.worksheet('📊 포트폴리오')
port_records = ws_portfolio.get_all_values()

naver_row_idx = None
for i, row in enumerate(port_records):
    if len(row) > 2 and row[2] == '035420': # NAVER
        naver_row_idx = i + 1
        ws_portfolio.update(f"H{naver_row_idx}", [["34"]], value_input_option='USER_ENTERED')
        print(f"Updated NAVER (Row {naver_row_idx}) quantity to 34.")
        break

# 2. Fix Row 33 (TIME ETF)
insert_r = 33

# Use apostrophe for the ticker to force string type, preventing scientific notation parsing
time_ticker = "'0113D0"

# D33 needs a formula. Actually we can just use the exact ticker without apostrophe in formulas.
formula_ticker = "C33"

time_port = [
    '-', '원', time_ticker,
    f'=GOOGLEFINANCE({formula_ticker}, "name")',
    f'=IFS({formula_ticker}="","",B33="BTC","CURRENCY:BTCUSD",REGEXMATCH(TO_TEXT({formula_ticker}),"^[A-Za-z]"),{formula_ticker},TRUE,"KRX:"&{formula_ticker})',
    '코어·지수', '코어', '490',
    f'=GOOGLEFINANCE({formula_ticker})',
    f'=GOOGLEFINANCE({formula_ticker}, "price") * IF(AND(OR(B33="달러", B33="BTC"), REGEXMATCH(TO_TEXT({formula_ticker}), "^[A-Za-z]")), GOOGLEFINANCE("CURRENCY:USDKRW"), 1)',
    '12910',
    '=H33*J33',
    '=H33*K33',
    '=IFERROR(L33-M33,"")',
    '=IFERROR((L33-M33)/M33,"")'
]

ws_portfolio.update(f"A33:O33", [time_port], value_input_option='USER_ENTERED')
print(f"Fixed Row 33 with TIME ETF.")
