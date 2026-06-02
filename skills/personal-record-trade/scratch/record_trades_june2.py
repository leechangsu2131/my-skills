import gspread
import sys
import re

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())

# 1. Update 🔬 기업분석
ws_analysis = ss.worksheet('🔬 기업분석')
analysis_records = ws_analysis.get_all_values()
max_p_id = 0
naver_p_id = "P035" # Just in case, we will find it

for i, row in enumerate(analysis_records):
    p_id_str = row[0]
    if p_id_str.startswith('P') and p_id_str[1:].isdigit():
        max_p_id = max(max_p_id, int(p_id_str[1:]))
    if len(row) > 1 and row[1] == '035420':
        naver_p_id = row[0]

time_p_id = f"P{max_p_id + 1:03d}"
tiger_p_id = f"P{max_p_id + 2:03d}"

# Append new ETFs to 🔬 기업분석
ws_analysis.append_rows([
    [time_p_id, "0113D0", "TIME 글로벌탑픽액티브", "보유"],
    [tiger_p_id, "0060H0", "TIGER 토탈월드스탁액티브", "보유"]
], value_input_option='USER_ENTERED')
print(f"Added ETFs to 🔬 기업분석 with IDs {time_p_id} and {tiger_p_id}")

# 2. Append to 📒 매매일지
ws_journal = ss.worksheet('📒 매매일지')
trades = [
    ["2026-06-02", naver_p_id, "035420", "NAVER", "매도", "23", "5911000", "젠슨황 방문 단기 급등에 의한 분할 매도", "", "", "", "", ""],
    ["2026-06-02", time_p_id, "0113D0", "TIME 글로벌탑픽액티브", "매수", "490", "6325900", "글로벌 탑픽 ETF 신규 편입", "", "", "", "", ""],
    ["2026-06-02", tiger_p_id, "0060H0", "TIGER 토탈월드스탁액티브", "매수", "460", "6329600", "월드스탁 ETF 신규 편입", "", "", "", "", ""],
    ["2026-06-02", naver_p_id, "035420", "NAVER", "매도", "18", "4743000", "젠슨황 방문 단기 급등에 의한 분할 매도", "", "", "", "", ""]
]
journal_records = ws_journal.get_all_values()
last_valid_j = 0
for i, r in enumerate(journal_records):
    if r[0].strip() != '':
        last_valid_j = i + 1
# Just use append_rows, it's safer if there are no blank lines
ws_journal.append_rows(trades, value_input_option='USER_ENTERED')
print(f"Appended 4 trades to 📒 매매일지")

# 3. Update 📊 포트폴리오
ws_portfolio = ss.worksheet('📊 포트폴리오')
port_records = ws_portfolio.get_all_values()
cash_row_idx = None
naver_row_idx = None

for i, row in enumerate(port_records):
    if len(row) > 2 and row[2] == '원화':
        cash_row_idx = i + 1
        current_cash = int(row[7].replace(',', ''))
        new_cash = current_cash - 2001500 # Net cash change
        ws_portfolio.update(f"H{cash_row_idx}", [[f"{new_cash:,}"]], value_input_option='USER_ENTERED')
    if len(row) > 2 and row[2] == '035420': # NAVER
        naver_row_idx = i + 1
        current_naver_qty = int(row[7].replace(',', ''))
        new_naver_qty = current_naver_qty - 41
        ws_portfolio.update(f"H{naver_row_idx}", [[new_naver_qty]], value_input_option='USER_ENTERED')

# Append 2 new rows for ETFs in Portfolio
insert_r = len(port_records) + 1
for i, row in enumerate(port_records):
    if i > 5 and (len(row) < 2 or row[1].strip() == ''):
        insert_r = i + 1
        break

def build_portfolio_row(r, ticker, name, qty, buy_price, sector, bucket):
    return [
        '-', '원', ticker,
        f'=GOOGLEFINANCE(C{r}, "name")',
        f'=IFS(C{r}="","",B{r}="BTC","CURRENCY:BTCUSD",REGEXMATCH(TO_TEXT(C{r}),"^[A-Za-z]"),C{r},TRUE,"KRX:"&C{r})',
        sector, bucket, str(qty),
        f'=GOOGLEFINANCE(C{r})',
        f'=GOOGLEFINANCE(C{r}, "price") * IF(AND(OR(B{r}="달러", B{r}="BTC"), REGEXMATCH(TO_TEXT(C{r}), "^[A-Za-z]")), GOOGLEFINANCE("CURRENCY:USDKRW"), 1)',
        str(buy_price),
        f'=H{r}*J{r}',
        f'=H{r}*K{r}',
        f'=IFERROR(L{r}-M{r},"")',
        f'=IFERROR((L{r}-M{r})/M{r},"")'
    ]

# We need to insert them one by one due to formulas needing exact row index
time_port = build_portfolio_row(insert_r, "0113D0", "TIME 글로벌탑픽액티브", 490, 12910, "코어·지수", "코어")
tiger_port = build_portfolio_row(insert_r+1, "0060H0", "TIGER 토탈월드스탁액티브", 460, 13760, "코어·지수", "코어")
ws_portfolio.update(f"A{insert_r}:O{insert_r+1}", [time_port, tiger_port], value_input_option='USER_ENTERED')
print("Added 2 ETFs to 📊 포트폴리오 and updated NAVER/Cash.")

# 4. Update 🎯 비중조절신호
ws_weight = ss.worksheet('🎯 비중조절신호')
weight_records = ws_weight.get_all_values(value_render_option='FORMULA')

insert_w = len(weight_records) + 1
for i, row in enumerate(weight_records):
    if i > 3 and (len(row) == 0 or str(row[0]).strip() == ''):
        insert_w = i + 1
        break

template_row = weight_records[4] # row 5 GOOG

def build_weight_row(r, ticker, target_price, downside):
    new_row = []
    for cell in template_row:
        cell_str = str(cell)
        for col in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            cell_str = re.sub(rf"(?<!\$)\b{col}5\b", f"{col}{r}", cell_str)
            cell_str = re.sub(rf"\${col}5\b", f"${col}{r}", cell_str)
        new_row.append(cell_str)
    
    new_row[0] = ticker
    new_row[3] = 0.5 # Conviction
    new_row[5] = "직접입력"
    new_row[6] = target_price
    new_row[8] = downside
    new_row[10] = 0.10 # return target
    new_row[14] = 0.05 # model weight
    new_row[17] = "대기"
    return new_row

time_weight = build_weight_row(insert_w, "0113D0", 15000, 10000)
tiger_weight = build_weight_row(insert_w+1, "0060H0", 15000, 10000)

ws_weight.update(f"A{insert_w}:Y{insert_w+1}", [time_weight, tiger_weight], value_input_option='USER_ENTERED')
print("Added 2 ETFs to 🎯 비중조절신호")
