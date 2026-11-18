import os
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(next(p / "_shared" for p in _pl.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import load_env
load_env()

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
table = os.environ.get('SUPABASE_TABLE_NAME')

headers = {
    'apikey': key,
    'Authorization': f'Bearer {key}'
}

print('🗑️ 기존 데이터 전체 삭제 중...')
res = requests.delete(f'{url}/rest/v1/{table}?id=not.is.null', headers=headers, verify=False)
print('Delete Result:', res.status_code, res.text)
