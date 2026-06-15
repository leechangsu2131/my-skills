import gspread
import sys
from collections import defaultdict
from datetime import datetime
import re

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())

# === 1. Read 매매일지 - get all 2026 positions ===
ws_journal = ss.worksheet('📒 매매일지')
journal = ws_journal.get_all_values()

def parse_date(s):
    s = s.strip()
    if not s: return None
    try:
        clean = re.sub(r'[^\d.]', '', s)
        parts = [p for p in clean.split('.') if p]
        if len(parts) >= 3:
            yy = int(parts[0])
            if yy < 100: yy += 2000
            return datetime(yy, int(parts[1]), int(parts[2]))
    except: pass
    return None

# Group by semantic position ID
pos_data = defaultdict(lambda: {'dates': [], 'buys': 0, 'sells': 0, 'names': set(), 'tickers': set(), 'reasons': [], 'amounts': []})

for row in journal[3:]:
    if len(row) < 7: continue
    date_str = row[0].strip()
    sem_id = row[1].strip()
    ticker = row[2].strip()
    name = row[3].strip()
    buy_sell = row[4].strip()
    qty = row[5].strip()
    amount = row[6].strip()
    reason = row[7].strip() if len(row) > 7 else ''
    
    if not sem_id: continue
    dt = parse_date(date_str)
    if not dt: continue
    
    pos_data[sem_id]['dates'].append(dt)
    pos_data[sem_id]['names'].add(name)
    pos_data[sem_id]['tickers'].add(ticker)
    if buy_sell == '매수': pos_data[sem_id]['buys'] += 1
    elif buy_sell == '매도': pos_data[sem_id]['sells'] += 1
    if reason: pos_data[sem_id]['reasons'].append(reason)
    if amount and amount != '-': pos_data[sem_id]['amounts'].append(amount)

# === 2. Read 전략·전망 - get existing position IDs ===
ws_strat = ss.worksheet('🧠 전략·전망')
strat = ws_strat.get_all_values()

existing_ids = set()
for row in strat[41:]:  # After header row 41
    if row and row[0].strip():
        existing_ids.add(row[0].strip())

print(f"Existing position IDs in 전략·전망: {len(existing_ids)}")

# === 3. Find 2026 positions missing from 전략·전망 ===
missing = []
for sem_id, data in sorted(pos_data.items()):
    data['dates'].sort()
    first_date = data['dates'][0]
    last_date = data['dates'][-1]
    
    # Only 2026
    if first_date.year < 2026: continue
    
    if sem_id not in existing_ids:
        # Determine status
        has_sells = data['sells'] > 0
        has_buys = data['buys'] > 0
        
        # Check if in 👋 청산종목 later
        name = list(data['names'])[0]
        ticker = list(data['tickers'])[0] if data['tickers'] else ''
        
        missing.append({
            'sem_id': sem_id,
            'name': name,
            'ticker': ticker,
            'first_date': first_date,
            'last_date': last_date,
            'buys': data['buys'],
            'sells': data['sells'],
            'reasons': data['reasons']
        })

print(f"\nMissing 2026 positions: {len(missing)}")
for m in missing:
    reasons_str = ' / '.join(m['reasons'][:3]) if m['reasons'] else '(매매근거 없음)'
    print(f"  {m['sem_id']}: {m['name']} ({m['ticker']}) | {m['first_date'].strftime('%Y-%m-%d')} ~ {m['last_date'].strftime('%Y-%m-%d')} | 매수{m['buys']}건 매도{m['sells']}건 | {reasons_str}")
