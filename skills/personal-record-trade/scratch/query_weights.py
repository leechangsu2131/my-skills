import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())
ws = ss.worksheet('📊 포트폴리오')

records = ws.get_all_values()
total_assets = 0
stocks = []

for i, r in enumerate(records):
    if i > 3 and len(r) > 11 and r[11].strip() != '' and r[11] != '평가금액':
        try:
            val = float(r[11].replace(',', ''))
            # Exclude non-stock items if necessary, but here we include all to see weight
            stocks.append({
                'name': r[3] or r[2],
                'bucket': r[6],
                'val': val,
                'ticker': r[4] or r[2]
            })
            total_assets += val
        except ValueError:
            pass

stocks.sort(key=lambda x: x['val'], reverse=True)

print(f"Total Portfolio Assets (from evaluating column L): {total_assets:,.0f}")
print("-" * 50)
for s in stocks:
    weight = (s['val'] / total_assets) * 100 if total_assets > 0 else 0
    print(f"{s['name'][:20]:<20} | {s['bucket']:<5} | {s['val']:>12,.0f} | {weight:>5.1f}%")
