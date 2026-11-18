import os
import requests
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(next(p / "_shared" for p in _pl.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import load_env

load_env()

db_id = os.environ.get('NOTION_DATABASE_ID')
api_key = os.environ.get('NOTION_API_KEY')

url = f"https://api.notion.com/v1/databases/{db_id}/query"
headers = {
    'Authorization': f'Bearer {api_key}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

r = requests.post(url, json={'page_size': 1}, headers=headers, verify=False)
if r.ok:
    data = r.json()
    if data['results']:
        props = data['results'][0]['properties']
        sql = 'CREATE TABLE "class-manage" (\n  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,'
        for k, v in props.items():
            t = v.get('type')
            pg_type = 'TEXT' # default
            if t == 'number': pg_type = 'NUMERIC'
            elif t == 'checkbox': pg_type = 'BOOLEAN'
            elif t == 'date': pg_type = 'DATE'
            elif t == 'multi_select': pg_type = 'TEXT[]'
            
            sql += f'\n  "{k}" {pg_type},'
        sql += '\n  created_at TIMESTAMPTZ DEFAULT now()\n);'
        
        with open('output_sql.txt', 'w', encoding='utf-8') as f:
            f.write(sql)
        print("SQL saved to output_sql.txt")
