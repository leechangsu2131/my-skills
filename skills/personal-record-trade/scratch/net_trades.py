import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('📒 매매일지')

records = ws.get_all_values()
updates = []

for i, row in enumerate(records[-16:]):
    row_idx = len(records) - 16 + i + 1  # 1-indexed
    
    if len(row) > 3:
        # Find SK하이닉스 Net Trade on 06/12
        if '2026. 6. 12' in row[0] and 'SK하이닉스' in row[3]:
            # Update to Net Sell 1
            updates.append({'range': f'E{row_idx}:H{row_idx}', 'values': [['매도', '1', '-', '[위탁+토스] 총 매수 2, 매도 3 -> 순매도 1 (일부단가 미표기)']]})
            
        # Find HD한국조선해양 Net Trade on 06/12
        elif '2026. 6. 12' in row[0] and 'HD한국조선해양' in row[3]:
            # Update to Net 0
            updates.append({'range': f'E{row_idx}:H{row_idx}', 'values': [['단타', '0', '-', '[위탁종합] 매수 10, 매도 10 -> 데이트레이딩 (포지션변동 0)']]})

if updates:
    ws.batch_update(updates, value_input_option='USER_ENTERED')
    print("Successfully netted SK Hynix and HD KSOE trades.")
else:
    print("Could not find the target rows to update.")
