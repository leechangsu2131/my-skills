import sys
from gsheet_auth import get_client, get_sheet_id

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

client = get_client()
doc = client.open_by_key(get_sheet_id())

# Fix 📊 포트폴리오
ws_portfolio = doc.worksheet("📊 포트폴리오")
portfolio_data = ws_portfolio.get_all_values()
for i, row in enumerate(portfolio_data):
    if len(row) > 2:
        if row[2] == "453850":
            ws_portfolio.update_cell(i + 1, 3, "416090")
            print(f"Fixed portfolio ticker 453850 -> 416090 at row {i+1}")
        elif row[2] == "486290":
            ws_portfolio.update_cell(i + 1, 3, "453950")
            print(f"Fixed portfolio ticker 486290 -> 453950 at row {i+1}")

# Fix 📒 매매일지
ws_journal = doc.worksheet("📒 매매일지")
journal_data = ws_journal.get_all_values()
for i, row in enumerate(journal_data):
    if len(row) > 1:
        if row[1] == "453850":
            ws_journal.update_cell(i + 1, 2, "416090")
            print(f"Fixed journal ticker 453850 -> 416090 at row {i+1}")
        elif row[1] == "486290":
            ws_journal.update_cell(i + 1, 2, "453950")
            print(f"Fixed journal ticker 486290 -> 453950 at row {i+1}")

