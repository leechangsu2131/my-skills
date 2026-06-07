import sys
from gsheet_auth import get_client, get_sheet_id
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = get_client()
doc = client.open_by_key(get_sheet_id())
ws = doc.worksheet("🔬 기업분석")

today = datetime.now().strftime("%Y-%m-%d")

new_row = [
    "", # F_PER
    "033500", # 티커
    "동성화인텍", # 종목명
    "분석중", # 상태
    18930, # 현재가
    5677, # 시총(억)
    8.87, # PER
    "", # EV/FCF
    2.15, # PBR
    "", # Implied성장률%
    "", # 섹터PER대비%
    "", # PER변화1Y
    "-1.9%", # 매출성장률% (26.1Q)
    "11.7%", # 영업마진% (26.1Q)
    "", # ROIC%
    "", # FCF성장률%
    "", # 성장괴리%p
    "LNG 보냉재 고가 수주분 반영 본격화. 이익률(11.7%) 대폭 개선. 하반기 대형 프로젝트 모멘텀 대기 중.", # 한줄판단
    "이익 턴어라운드 가시화", # 기대현실적
    "", # 비중판단
    "LNG선 수주 사이클 꺾이거나 MDI(원자재) 가격 폭등 시", # 매도트리거
    today, # 업데이트일
    "", # 시장내포_CAP(년)
    "", # 시장내포_수익률%
    "", # 미래성장_의존도%
    36500 # 애널목표가
]

# Get all values to find empty row or update if exists
data = ws.get_all_values()
tickers = [row[1] if len(row) > 1 else "" for row in data]

if "033500" in tickers:
    row_idx = tickers.index("033500") + 1
    # Update only specific columns to not overwrite user's formulas if any
    ws.update(f'A{row_idx}:Z{row_idx}', [new_row], value_input_option='USER_ENTERED')
    print(f"Updated Dongsung Finetec at row {row_idx}")
else:
    ws.append_row(new_row, value_input_option='USER_ENTERED')
    print("Appended Dongsung Finetec to new row")
