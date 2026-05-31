from gsheet_auth import get_client, get_sheet_id

client = get_client()
doc = client.open_by_key(get_sheet_id())

for sheet in doc.worksheets():
    if sheet.id == 1127641143:  # GID_ANALYSIS
        print(f"Current columns: {sheet.col_count}")
        target_cols = 37
        if sheet.col_count < target_cols:
            sheet.add_cols(target_cols - sheet.col_count)
            print(f"Added columns up to {target_cols}")
        break
