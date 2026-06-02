import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())

ws = ss.worksheet('📊 포트폴리오')

# 1. Delete row 33
ws.delete_rows(33)
print("Deleted row 33.")

# 2. Append TIME ETF
time_ticker = "'0113D0" # Use string to avoid scientific notation
formula_ticker = "C34" # Since TIGER is now at 33, new row will be 34
r = 34

time_port = [
    '-', '원', time_ticker,
    f'=GOOGLEFINANCE({formula_ticker}, "name")',
    f'=IFS({formula_ticker}="","",B{r}="BTC","CURRENCY:BTCUSD",REGEXMATCH(TO_TEXT({formula_ticker}),"^[A-Za-z]"),{formula_ticker},TRUE,"KRX:"&{formula_ticker})',
    '코어·지수', '코어', '490',
    f'=GOOGLEFINANCE({formula_ticker})',
    f'=GOOGLEFINANCE({formula_ticker}, "price") * IF(AND(OR(B{r}="달러", B{r}="BTC"), REGEXMATCH(TO_TEXT({formula_ticker}), "^[A-Za-z]")), GOOGLEFINANCE("CURRENCY:USDKRW"), 1)',
    '12910',
    f'=H{r}*J{r}',
    f'=H{r}*K{r}',
    f'=IFERROR(L{r}-M{r},"")',
    f'=IFERROR((L{r}-M{r})/M{r},"")'
]

ws.append_row(time_port, value_input_option='USER_ENTERED')
print("Appended TIME ETF to the end.")
