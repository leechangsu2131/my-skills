import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())

ws = ss.worksheet('📊 포트폴리오')

# Write static values first
static_values = ['-', '원', "'0113D0", "", "", "코어·지수", "코어", 490, "", "", 12910, "", "", "", ""]
ws.update(f"A33:O33", [static_values], value_input_option='USER_ENTERED')

# Now write formulas
formulas = [
    {'range': 'D33', 'values': [['=GOOGLEFINANCE(C33, "name")']]},
    {'range': 'E33', 'values': [['=IFS(C33="","",B33="BTC","CURRENCY:BTCUSD",REGEXMATCH(TO_TEXT(C33),"^[A-Za-z]"),C33,TRUE,"KRX:"&C33)']]},
    {'range': 'I33', 'values': [['=GOOGLEFINANCE(C33)']]},
    {'range': 'J33', 'values': [['=GOOGLEFINANCE(C33, "price") * IF(AND(OR(B33="달러", B33="BTC"), REGEXMATCH(TO_TEXT(C33), "^[A-Za-z]")), GOOGLEFINANCE("CURRENCY:USDKRW"), 1)']]},
    {'range': 'L33', 'values': [['=H33*K33']]}, # Wait, L33 is H33*J33 (qty * current price)
    {'range': 'M33', 'values': [['=H33*K33']]},
    {'range': 'N33', 'values': [['=IFERROR(L33-M33,"")']]},
    {'range': 'O33', 'values': [['=IFERROR((L33-M33)/M33,"")']]}
]
formulas[4]['values'] = [['=H33*J33']]

for f in formulas:
    try:
        ws.update(f['range'], f['values'], value_input_option='USER_ENTERED')
        print(f"Success updating {f['range']}")
    except Exception as e:
        print(f"Failed updating {f['range']}: {e}")

print("Done fixing row 33")
