import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())

# 1. Update 🔬 기업분석
ws_analysis = ss.worksheet('🔬 기업분석')
analysis_records = ws_analysis.get_all_values()
max_p_id = 0
hanmi_analysis_row = None

for i, row in enumerate(analysis_records):
    p_id_str = row[0]
    if p_id_str.startswith('P') and p_id_str[1:].isdigit():
        max_p_id = max(max_p_id, int(p_id_str[1:]))
    
    if len(row) > 1 and row[1] == '042700':
        hanmi_analysis_row = i + 1

new_p_id = f"P{max_p_id + 1:03d}"

if hanmi_analysis_row:
    # Update existing row
    ws_analysis.update(f"A{hanmi_analysis_row}", [[new_p_id]])
    ws_analysis.update(f"D{hanmi_analysis_row}", [["보유"]])
    print(f"Updated 🔬 기업분석: row {hanmi_analysis_row} to {new_p_id} and '보유'")
else:
    print("Could not find Hanmi in 🔬 기업분석!")
    # Just in case, append it
    ws_analysis.append_row([new_p_id, "042700", "한미반도체", "보유"], value_input_option='USER_ENTERED')

# 2. Append to 📒 매매일지
ws_journal = ss.worksheet('📒 매매일지')
# We must use the exact exact columns. A:매매일, B:포지션ID, C:티커, D:종목명, E:구분, F:수량, G:금액(원), H:매매근거
trade_row = [
    "2026-06-01",
    new_p_id,
    "042700",
    "한미반도체",
    "매수",
    "15",
    "4425000", # 15 * 295000
    "신규 매수",
    "", "", "", "", ""
]
# Append safely by finding first empty row
journal_records = ws_journal.get_all_values()
last_valid_j = 0
for i, r in enumerate(journal_records):
    if r[0].strip() != '':
        last_valid_j = i + 1
ws_journal.update(f"A{last_valid_j + 1}:M{last_valid_j + 1}", [trade_row[:13]], value_input_option='USER_ENTERED')
print(f"Appended trade to 📒 매매일지 at row {last_valid_j + 1}")

# 3. Update 📊 포트폴리오
ws_portfolio = ss.worksheet('📊 포트폴리오')
port_records = ws_portfolio.get_all_values()

# Deduct KRW Cash
cash_row = None
for i, row in enumerate(port_records):
    if len(row) > 2 and row[2] == '원화':
        cash_row = i + 1
        current_cash = int(row[7].replace(',', ''))
        new_cash = current_cash - 4425000
        ws_portfolio.update(f"H{cash_row}", [[f"{new_cash:,}"]], value_input_option='USER_ENTERED')
        print(f"Updated KRW Cash in 📊 포트폴리오 (Row {cash_row}): {current_cash:,} -> {new_cash:,}")
        break

# Append Hanmi
# Find the first row where column B (index 1) is empty
insert_row = len(port_records) + 1
for i, row in enumerate(port_records):
    if len(row) < 2 or row[1].strip() == '':
        if i > 5: # Skip headers
            insert_row = i + 1
            break

# The formulas must use insert_row
r = insert_row
portfolio_row = [
    '-', # A: 등급
    '원', # B: 통화
    '042700', # C: 종목코드
    f'=GOOGLEFINANCE(C{r}, "name")', # D: 종목명
    f'=IFS(C{r}="","",B{r}="BTC","CURRENCY:BTCUSD",REGEXMATCH(TO_TEXT(C{r}),"^[A-Za-z]"),C{r},TRUE,"KRX:"&C{r})', # E: GF티커
    'AI 인프라', # F: 섹터
    '성장', # G: 버킷
    '15', # H: 수량
    f'=GOOGLEFINANCE(C{r})', # I: 현지가
    f'=GOOGLEFINANCE(C{r}, "price") * IF(AND(OR(B{r}="달러", B{r}="BTC"), REGEXMATCH(TO_TEXT(C{r}), "^[A-Za-z]")), GOOGLEFINANCE("CURRENCY:USDKRW"), 1)', # J: 현재가(원)
    '295000', # K: 평균매입가
    f'=H{r}*J{r}', # L: 평가금액
    f'=H{r}*K{r}', # M: 매입금액
    f'=IFERROR(L{r}-M{r},"")', # N: 평가손익
    f'=IFERROR((L{r}-M{r})/M{r},"")' # O: 수익률
]

ws_portfolio.update(f"A{r}:O{r}", [portfolio_row], value_input_option='USER_ENTERED')
print(f"Appended Hanmi Semiconductor to 📊 포트폴리오 at row {r}")
