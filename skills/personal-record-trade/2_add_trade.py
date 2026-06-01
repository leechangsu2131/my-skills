"""
2_add_trade.py
──────────────
Claude가 스크린샷을 파싱한 결과를 받아 Google Sheets 매매일지에 추가합니다.

사용법 (Claude Desktop에서):
  python 2_add_trade.py --json '{"date":"2025-05-02","ticker":"NVDA","name":"NVIDIA","type":"매수","qty":10,"price":294130,"amount":2941300,"reason":"AI수혜"}'

또는 파이프:
  echo '{...}' | python 2_add_trade.py

Claude Desktop 프롬프트 예시:
  "이 체결 스크린샷을 파싱해서 2_add_trade.py를 실행해줘"
"""

import gspread
import json, sys, os, datetime, argparse

from gsheet_auth import get_client, get_sheet_id  # .env 기반 인증 (service_account.json 폴백)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 거래 데이터 구조 ──────────────────────────────────────────
# Claude가 스크린샷에서 파싱해서 이 형식으로 전달
TRADE_SCHEMA = {
    "date":    "매매일 (YYYY-MM-DD)",
    "ticker":  "티커 코드 (NVDA, 005930 등)",
    "name":    "종목명",
    "type":    "매수 / 매도 / 매수·매도",
    "qty":     "수량 (주)",
    "price":   "단가 (원)",
    "amount":  "거래금액 (원)",
    "reason":  "매매 이유 (선택)",
    "timing":  "타이밍 이유 (선택)",
    "score":   "만족도 -10~10 (선택)",
    "memo":    "비고 (선택)",
}

def parse_trade(raw: dict) -> list:
    """dict → Sheets 행 리스트 변환"""
    today = datetime.date.today().isoformat()
    return [
        raw.get("date", today),
        raw.get("position_id", ""),  # 새롭게 추가된 컬럼 (B)
        raw.get("ticker", ""),
        raw.get("name", ""),
        raw.get("type", ""),
        raw.get("qty", ""),
        raw.get("amount", ""),       # 단가(price)가 시트에서 빠졌으므로 바로 금액
        raw.get("reason", ""),
        raw.get("score", ""),
        raw.get("condition", ""),
        raw.get("analysis", ""),
        raw.get("bias", ""),
        raw.get("fix", ""),
    ]

def add_trade(trade_data: dict):
    """매매일지 시트에 행 추가"""
    gc = get_client()
    sheet_id = get_sheet_id()

    ss = gc.open_by_key(sheet_id)
    ws = ss.worksheet("📒 매매일지")

    row = parse_trade(trade_data)
    ws.append_row(row, value_input_option="USER_ENTERED")

    print(f"✅ 매매일지 추가 완료:")
    print(f"   {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}주 | {row[5]:,}원")
    return row

def update_portfolio_price(ticker: str, current_price: float):
    """포트폴리오 시트 현재가 업데이트"""
    gc = get_client()
    sheet_id = get_sheet_id()
    ss = gc.open_by_key(sheet_id)
    ws = ss.worksheet("📊 포트폴리오")

    data = ws.get_all_values()
    headers = data[0]
    ticker_col = headers.index("코드") + 1      # 1-indexed
    price_col  = headers.index("현재가(원)") + 1

    for i, row in enumerate(data[1:], start=2):
        if len(row) > ticker_col - 1 and row[ticker_col - 1] == ticker:
            ws.update_cell(i, price_col, current_price)
            print(f"✅ {ticker} 현재가 업데이트: {current_price:,}원 (행 {i})")
            return
    print(f"⚠️ {ticker} 를 포트폴리오에서 찾을 수 없음")

def batch_update_prices(price_dict: dict):
    """여러 종목 현재가 일괄 업데이트 {ticker: price}"""
    gc = get_client()
    sheet_id = get_sheet_id()
    ss = gc.open_by_key(sheet_id)
    ws = ss.worksheet("📊 포트폴리오")

    data = ws.get_all_values()
    headers = data[0]
    ticker_col = headers.index("코드")
    price_col  = headers.index("현재가(원)")

    updates = []
    for i, row in enumerate(data[1:], start=2):
        if len(row) > ticker_col:
            t = row[ticker_col]
            if t in price_dict:
                cell = gspread.utils.rowcol_to_a1(i, price_col + 1)
                updates.append({"range": f"📊 포트폴리오!{cell}",
                                 "values": [[price_dict[t]]]})

    if updates:
        ss.values_batch_update({"valueInputOption": "USER_ENTERED",
                                 "data": updates})
        print(f"✅ {len(updates)}개 종목 현재가 업데이트 완료")

def add_snapshot(snapshot_date: str, holdings: list):
    """특정일잔고 시트에 스냅샷 추가"""
    gc = get_client()
    sheet_id = get_sheet_id()
    ss = gc.open_by_key(sheet_id)
    ws = ss.worksheet("📅 특정일잔고")

    rows = [[snapshot_date] + list(h) for h in holdings]
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    print(f"✅ {snapshot_date} 스냅샷 {len(rows)}건 추가")

# ── CLI 인터페이스 ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="매매일지 추가 도구")
    parser.add_argument("--json", type=str, help="거래 데이터 JSON 문자열")
    parser.add_argument("--file", type=str, help="거래 데이터 JSON 파일 경로")
    parser.add_argument("--price", nargs=2, metavar=("TICKER","PRICE"),
                        help="현재가 업데이트: --price NVDA 294130")
    parser.add_argument("--prices", type=str,
                        help='일괄 현재가 업데이트 JSON: \'{"NVDA":294130,"GOOG":562910}\'')
    args = parser.parse_args()

    if args.price:
        ticker, price = args.price
        update_portfolio_price(ticker, float(price))
    elif args.prices:
        batch_update_prices(json.loads(args.prices))
    elif args.json:
        add_trade(json.loads(args.json))
    elif args.file:
        with open(args.file) as f:
            add_trade(json.load(f))
    elif not sys.stdin.isatty():
        # 파이프 입력
        add_trade(json.load(sys.stdin))
    else:
        print("📋 거래 데이터 스키마:")
        for k, v in TRADE_SCHEMA.items():
            print(f"  {k:10s}: {v}")
        print("\n사용 예시:")
        print("""  python 2_add_trade.py --json '{"date":"2025-05-02","ticker":"NVDA","name":"NVIDIA","type":"매수","qty":10,"price":294130,"amount":2941300}'""")
        print("""  python 2_add_trade.py --price NVDA 305000""")
        print("""  python 2_add_trade.py --prices '{"NVDA":305000,"GOOG":570000,"META":920000}'""")

if __name__ == "__main__":
    main()
