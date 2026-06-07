import sys
from gsheet_auth import get_client, get_sheet_id
from gspread.utils import rowcol_to_a1

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = get_client()
doc = client.open_by_key(get_sheet_id())
ws = doc.worksheet("📊 포트폴리오")

trades = [
    {
        "ticker": "453850",
        "name": "ACE 중국과창판STAR50(합성)",
        "qty": 497,
        "price": 14477,
        "amount": 497 * 14477,
        "currency": "원"
    },
    {
        "ticker": "486290",
        "name": "TIGER TSMC파운드리밸류체인",
        "qty": 257,
        "price": 38780,
        "amount": 257 * 38780,
        "currency": "원"
    },
    {
        "ticker": "000660",
        "name": "SK하이닉스",
        "qty": 2,
        "price": 2142000,
        "amount": 2 * 2142000,
        "currency": "원"
    },
    {
        "ticker": "042700",
        "name": "한미반도체",
        "qty": 10,
        "price": 294000,
        "amount": 10 * 294000,
        "currency": "원"
    }
]

data = ws.get_all_values()
tickers_in_sheet = [row[2] if len(row) > 2 else "" for row in data]

new_rows = []

for t in trades:
    if t["ticker"] in tickers_in_sheet:
        # Update existing
        row_idx = tickers_in_sheet.index(t["ticker"]) + 1
        row = data[row_idx - 1]
        
        try:
            curr_qty = float(row[7].replace(',', '')) if len(row) > 7 and row[7] else 0
        except ValueError:
            curr_qty = 0
            
        try:
            curr_price = float(row[10].replace(',', '')) if len(row) > 10 and row[10] else 0
        except ValueError:
            curr_price = 0
            
        new_qty = curr_qty + t["qty"]
        if new_qty > 0:
            new_avg_price = ((curr_qty * curr_price) + t["amount"]) / new_qty
        else:
            new_avg_price = curr_price
            
        ws.update_cell(row_idx, 8, new_qty)
        ws.update_cell(row_idx, 11, new_avg_price)
        print(f"Updated {t['name']}: Qty {curr_qty}->{new_qty}, Avg Price {curr_price}->{new_avg_price}")
        
    else:
        # Prepare to append new row
        next_row_num = len(data) + len(new_rows) + 1
        r = str(next_row_num)
        
        new_row = [
            "B", # 등급
            t["currency"], # 통화
            t["ticker"], # 종목코드
            f'=GOOGLEFINANCE(C{r}, "name")', # 종목명
            f'=IFS(C{r}="", "", B{r}="BTC", "CURRENCY:BTCUSD", REGEXMATCH(TO_TEXT(C{r}), "^[A-Za-z]"), C{r}, TRUE, "KRX:" & C{r})', # GF티커
            "미분류", # 섹터
            "기타", # 버킷
            t["qty"], # 수량
            f'=IF(C{r}="","",IFERROR(GOOGLEFINANCE(E{r},"price"),""))', # 현지가
            f'=GOOGLEFINANCE(C{r}, "price") * IF(AND(OR(B{r}="달러", B{r}="BTC"), REGEXMATCH(TO_TEXT(C{r}), "^[A-Za-z]")), GOOGLEFINANCE("CURRENCY:USDKRW"), 1)', # 현재가(원)
            t["price"], # 평균매입가
            f'=H{r}*J{r}', # 평가금액
            f'=H{r}*K{r}', # 매입금액
            f'=IFERROR(L{r}-M{r},"")', # 평가손익
            f'=IFERROR((L{r}-M{r})/M{r},"")' # 수익률
        ]
        new_rows.append(new_row)
        print(f"Prepared new row for {t['name']}.")

if new_rows:
    ws.append_rows(new_rows, value_input_option='USER_ENTERED')
    print(f"Appended {len(new_rows)} new rows to 📊 포트폴리오.")

