import json

with open(r'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\admin-neis-bot\training_screen_dump.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for item in data:
    app_id = item.get('appId', '')
    if 'hrd' in app_id:
        print('=== ' + app_id + ' ===')
        for c in item.get('controls', []):
            cid = c.get('id', '')
            val = str(c.get('value', ''))
            ctype = c.get('type', '')
            if any(k in cid.lower() or k in val for k in ['연수', '등록', '신청', 'title', 'lbl', 'btn', 'grid', 'grd']):
                print(f'  {cid} ({ctype}): {val}')
