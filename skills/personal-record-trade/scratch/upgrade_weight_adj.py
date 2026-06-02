import gspread
import sys

sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\personal-record-trade")
from gsheet_auth import get_client, get_sheet_id

gc = get_client()
ss = gc.open_by_key(get_sheet_id())

ws = ss.worksheet('🎯 비중조절신호')

# 1. Write the Top-Down Dashboard in AA1:AD6
dashboard = [
    ['📊 버킷별 리스크 할당 및 한도 모니터링', '', '', ''],
    ['버킷', '타겟예산', '현재비중', '상태'],
    ['성장', 0.45, '=IFERROR(SUMIFS(\'📊 포트폴리오\'!Q:Q, \'📊 포트폴리오\'!G:G, "성장"), 0)', '=IFS(AB3-AC3 > 0.05, "🔥확대요망", AC3-AB3 > 0.05, "🔥축소요망", TRUE, "✅안정")'],
    ['코어', 0.35, '=IFERROR(SUMIFS(\'📊 포트폴리오\'!Q:Q, \'📊 포트폴리오\'!G:G, "코어"), 0)', '=IFS(AB4-AC4 > 0.05, "🔥확대요망", AC4-AB4 > 0.05, "🔥축소요망", TRUE, "✅안정")'],
    ['인컴', 0.20, '=IFERROR(SUMIFS(\'📊 포트폴리오\'!Q:Q, \'📊 포트폴리오\'!G:G, "인컴"), 0)', '=IFS(AB5-AC5 > 0.05, "🔥확대요망", AC5-AB5 > 0.05, "🔥축소요망", TRUE, "✅안정")'],
    ['최대감내손실(Risk Limit)', -0.15, '=IFERROR(-SUM(S5:S100), 0)', '=IF(AC6<AB6, "⚠️위험초과", "✅안전")']
]
ws.update("AA1:AD6", dashboard, value_input_option='USER_ENTERED')
print("Dashboard added to AA1:AD6")

# Find max row
records = ws.get_all_values()
max_r = len(records)
if max_r < 5:
    max_r = 100

# 2. Update O열(모델비중) & R열(매매신호) for rows 5 to max_r
updates = []
for r in range(5, max_r + 1):
    # O열 (Model Weight): Fractional Kelly (f=0.2)
    # p = D (확신도), q = 1-D
    # a = Downside % = (E - I) / E
    # b = Upside % = (H - E) / E
    # formula = 0.2 * ( (D / a) - ((1-D) / b) )
    o_formula = f'=IF(A{r}="","", MAX(0, MIN(0.2 * ( (D{r} / MAX((E{r}-I{r})/E{r}, 0.001)) - ((1-D{r}) / MAX((H{r}-E{r})/E{r}, 0.001)) ), 0.15)))'
    
    # R열 (Trade Signal)
    r_formula = f'=IF(A{r}="","", IFS(Q{r} > 0.03, "🔴비중축소", Q{r} < -0.03, "🟢비중확대", TRUE, "⚪유지"))'
    
    updates.append({'range': f'O{r}', 'values': [[o_formula]]})
    updates.append({'range': f'R{r}', 'values': [[r_formula]]})

if updates:
    ws.batch_update(updates, value_input_option='USER_ENTERED')
    print(f"Updated O and R columns for rows 5 to {max_r}")

print("Upgrade complete.")
