import urllib.request
import json

try:
    resp = urllib.request.urlopen('http://127.0.0.1:9222/json')
    data = json.loads(resp.read().decode('utf-8'))
    print(f'Found {len(data)} targets:')
    for t in data:
        print(f"- {t.get('type')}: {t.get('title')} ({t.get('url')})")
except Exception as e:
    print('Error:', e)
