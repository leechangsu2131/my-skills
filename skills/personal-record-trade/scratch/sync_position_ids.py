import gspread
import sys
from collections import defaultdict
from datetime import datetime, timedelta
import re

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())

# === 1. Build index from 매매일지: group trades by semantic ID ===
ws_journal = ss.worksheet('📒 매매일지')
journal = ws_journal.get_all_values()

# semantic_id -> list of {date, name, ticker}
id_info = defaultdict(list)
for row in journal[3:]:
    if len(row) < 5: continue
    date_str = row[0].strip()
    sem_id = row[1].strip()
    name = row[3].strip()
    if not sem_id or not date_str: continue
    try:
        clean = re.sub(r'[^\d.]', '', date_str)
        parts = [p for p in clean.split('.') if p]
        if len(parts) >= 3:
            yy = int(parts[0]); 
            if yy < 100: yy += 2000
            dt = datetime(yy, int(parts[1]), int(parts[2]))
            id_info[sem_id].append({'date': dt, 'name': name})
    except: continue

# For each semantic ID, compute earliest date and stock name
sem_id_meta = {}
for sid, trades in id_info.items():
    trades.sort(key=lambda x: x['date'])
    sem_id_meta[sid] = {
        'first_date': trades[0]['date'],
        'last_date': trades[-1]['date'],
        'name': trades[0]['name']
    }

# === 2. Read 전략·전망 positions ===
ws_strat = ss.worksheet('🧠 전략·전망')
strat = ws_strat.get_all_values()

# Position review rows start at row 42 (index 41), header at row 41 (index 40)
# ['포지션ID', '티커', '종목명', '개설일', '종료일', '상태', '포지션 테제', '실제결과', '잘한점 / 실수', '인지오류']

def parse_date(s):
    s = s.strip()
    if not s: return None
    try:
        return datetime.strptime(s, '%Y-%m-%d')
    except:
        try:
            clean = re.sub(r'[^\d.]', '', s)
            parts = [p for p in clean.split('.') if p]
            if len(parts) >= 3:
                yy = int(parts[0])
                if yy < 100: yy += 2000
                return datetime(yy, int(parts[1]), int(parts[2]))
        except: pass
    return None

def get_season(month):
    if month in [3,4,5]: return '봄'
    if month in [6,7,8]: return '여름'
    if month in [9,10,11]: return '가을'
    return '겨울'

# Name normalization map for matching
name_aliases = {
    'nvidia': ['NVIDIA', '엔비디아'],
    '팔란티어': ['팔란티어', 'PLTR', 'Palantir'],
    'alphabet': ['구글', 'GOOG', 'Alphabet', '구글'],
    'mags etf': ['MAGS'],
    '파가야': ['파가야', 'PGY'],
    '테슬라': ['테슬라', 'TSLA', 'Tesla'],
    '중국주식': ['중국주식', 'CN'],
    'unitedhealth': ['UNH', 'UnitedHealth'],
    '한국전력': ['한국전력'],
    '현대차3우b': ['현대차3우B'],
    '삼성전자': ['삼성전자'],
    'kg스틸': ['KG스틸'],
    'ark etf': ['ARKK', 'ARKF', 'ARK'],
    '현대해상': ['현대해상'],
    'meta': ['Meta', '메타', 'META'],
    '앱로빈': ['앱로빈', 'APP'],
    'adobe': ['어도비', 'Adobe', 'ADBE'],
    'synopsys': ['시놉시스', 'Synopsys', 'SNPS'],
    '삼성바이오': ['삼성바이오로직스', '삼성바이오'],
    '현대일렉트릭': ['현대일렉트릭'],
    '넷플릭스': ['넷플릭스', 'NFLX'],
    '아이스크림미디어': ['아이스크림미디어'],
    '현대해상2차': ['현대해상'],
}

def find_best_match(stock_name, ticker, open_date, close_date):
    """Find the best matching semantic ID from 매매일지"""
    if not open_date:
        return None
    
    candidates = []
    for sid, meta in sem_id_meta.items():
        # Check if dates overlap: the position's open_date should be near the cluster's date range
        cluster_start = meta['first_date']
        cluster_end = meta['last_date']
        
        # The open_date should be within [cluster_start - 30d, cluster_end + 30d]
        if open_date >= cluster_start - timedelta(days=30) and open_date <= cluster_end + timedelta(days=30):
            # Check name similarity
            sid_name = meta['name'].lower()
            s_lower = stock_name.lower() if stock_name else ''
            t_lower = ticker.lower() if ticker else ''
            
            name_match = False
            if s_lower and s_lower in sid_name: name_match = True
            if sid_name and sid_name in s_lower: name_match = True
            if t_lower and t_lower in sid_name: name_match = True
            if sid_name and sid_name in t_lower: name_match = True
            # Check the semantic ID itself
            sid_lower = sid.lower()
            if s_lower and s_lower in sid_lower: name_match = True
            if t_lower and t_lower in sid_lower: name_match = True
            
            # Also check aliases
            for key, aliases in name_aliases.items():
                key_match = any(a.lower() in s_lower or a.lower() in t_lower or s_lower in a.lower() for a in aliases if s_lower)
                sid_match = any(a.lower() in sid_lower for a in aliases)
                if key_match and sid_match:
                    name_match = True
                    break
            
            if name_match:
                # Score by date proximity
                dist = abs((open_date - cluster_start).days)
                candidates.append((sid, dist))
    
    if candidates:
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]
    
    # Fallback: compute from name and date directly
    yy = open_date.strftime('%y')
    season = get_season(open_date.month)
    # Try stock name first
    fallback = f"{stock_name}-{yy}년{season}"
    return fallback

updates = []
print("=== Mapping Old -> New Position IDs ===")
for i in range(41, len(strat)):  # rows 42+ (0-indexed: 41+)
    row = strat[i]
    if len(row) < 6: continue
    old_id = row[0].strip()
    ticker = row[1].strip()
    name = row[2].strip()
    open_date_str = row[3].strip()
    close_date_str = row[4].strip()
    
    if not old_id or not old_id.startswith('P'): continue
    
    open_date = parse_date(open_date_str)
    close_date = parse_date(close_date_str)
    
    new_id = find_best_match(name, ticker, open_date, close_date)
    
    row_num = i + 1  # 1-indexed
    print(f"  Row {row_num}: {old_id} ({name}) -> {new_id}")
    
    if new_id:
        updates.append({'range': f'A{row_num}', 'values': [[new_id]]})

# === 3. Also update the 전략별 성공률 section (rows 4-9) ===
# These reference position IDs in their text descriptions, but they use stock names directly, no P-codes to change.

if updates:
    ws_strat.batch_update(updates, value_input_option='USER_ENTERED')
    print(f"\nSuccessfully updated {len(updates)} position IDs in 🧠 전략·전망")
else:
    print("\nNo updates needed")
