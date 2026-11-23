import json

with open(r'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\admin-neis-bot\all_neis_menus.json', encoding='utf-8') as f:
    menus = json.load(f)

print("Matching menus:")
for m in menus:
    name = m.get('name', '')
    desc = m.get('desc', '')
    if any(k in name or k in desc for k in ['학부모', '보호자', '명부', '명렬', '신상', '가족', '연락', '주소', '인적', '신고', '등록']):
        print(f"[{m['id']}] {m['depth']} ({m['name']}) -> {m['page']}")
