import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws_port = ss.worksheet('📊 포트폴리오')
records = ws_port.get_all_values()

# Target classifications
targets = {
    'NVDA': '코어',  # Changing NVDA to Core based on user request
    'PLTR': '성장',
    'APP': '성장',
    'RDDT': '성장',
    'HOOD': '성장',
    '267260': '성장', # 현대일렉트릭
    
    'GOOG': '코어',
    'META': '코어',
    'NFLX': '코어',
    'ADBE': '코어',
    'ORCL': '코어',
    '035420': '코어', # 네이버
    'UNH': '코어',
    '000660': '코어', # SK하이닉스
    '461020': '코어', # 아이스크림미디어
    
    '001450': '인컴', # 현대해상
    '브라질채권': '인컴'
}

updates = []
print("--- Check and Update ---")
for i, r in enumerate(records):
    ticker = r[4] or r[2]
    current_bucket = r[6]
    row_idx = i + 1
    
    for t_key, t_bucket in targets.items():
        if t_key in ticker or t_key in str(r):
            if current_bucket != t_bucket:
                updates.append({'range': f'G{row_idx}', 'values': [[t_bucket]]})
                print(f"Row {row_idx}: {r[3] or r[2]} - '{current_bucket}' -> '{t_bucket}' 로 수정 예약")

if updates:
    ws_port.batch_update(updates, value_input_option='USER_ENTERED')
    print("일괄 업데이트 완료!")
else:
    print("모든 종목이 올바르게 분류되어 있습니다.")
