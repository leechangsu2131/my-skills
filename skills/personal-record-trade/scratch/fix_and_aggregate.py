import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('📒 매매일지')

# We added 20 rows previously. Let's delete the last 20 rows.
records = ws.get_all_values()
total_rows = len(records)
print(f"Total rows before delete: {total_rows}")

# Delete from bottom up
for i in range(total_rows, total_rows - 20, -1):
    ws.delete_rows(i)

# Construct the aggregated 16 rows correctly aligned to headers:
# [매매일(0), 포지션ID(1), 티커(2), 종목명(3), 구분(4), 수량(5), 금액(6), 매매근거(7)]
aggregated_trades = [
    ['2026. 6. 8', '', '', '한미반도체', '매수', '10', '2,705,000', '[토스증권]'],
    ['2026. 6. 8', '', '', 'HD현대일렉트릭', '매수', '1', '868,000', '[토스증권]'],
    
    ['2026. 6. 10', '', '000660', 'SK하이닉스', '매수', '3', '5,822,000', '[위탁종합] 2건 합산 (2주+1주)'],
    
    ['2026. 6. 11', '', '000660', 'SK하이닉스', '매수', '1', '1,943,000', '[토스증권]'],
    
    ['2026. 6. 12', '', '000660', 'SK하이닉스', '교체/단타', '매수 2 / 매도 3', '매수 4,034,000 / 매도 4,574,000', '[위탁종합] 매수 2, 매도 1(단가미상) / [토스증권] 매도 2'],
    ['2026. 6. 12', '', '', 'HD한국조선해양', '단타', '매수 10 / 매도 10', '매수 3,825,000 / 매도 미표기', '[위탁종합] 데이트레이딩 (매도단가 미표기)'],
    ['2026. 6. 12', '', '', '동성화인텍', '매수', '221', '3,995,680', '[위탁종합]'],
    ['2026. 6. 12', '', '', 'TIGER 조선TOP10', '매수', '137', '3,648,995', '[위탁종합]'],
    ['2026. 6. 12', '', '', 'RISE 200TR', '매도', '400', '-', '[위탁종합] 단가 미표기'],
    ['2026. 6. 12', '', '', '현대해상', '매도', '142', '-', '[위탁종합] 단가 미표기'],
    ['2026. 6. 12', '', '', '한미반도체', '매도', '11', '3,410,000', '[토스증권]'],
    ['2026. 6. 12', '', '', 'HD현대일렉트릭', '매도', '1', '1,105,000', '[토스증권]'],
    ['2026. 6. 12', '', '', 'TIGER 인도니프티50', '매수', '249', '3,091,335', '[어머님ISA]'],
    ['2026. 6. 12', '', '', 'NAVER', '매수', '3', '711,000', '[어머님ISA]'],
    ['2026. 6. 12', '', '', 'ACE 중국과창판STAR50', '매도', '206', '2,999,360', '[어머님ISA]'],
    ['2026. 6. 12', '', '', 'TIGER 토탈월드스탁액티브', '매도', '93', '1,262,010', '[어머님ISA] 총 467주 주문 중 93주만 체결']
]

ws.append_rows(aggregated_trades, value_input_option='USER_ENTERED')
print("Successfully deleted previous misaligned 20 rows and appended the 16 correctly aggregated and aligned rows.")
