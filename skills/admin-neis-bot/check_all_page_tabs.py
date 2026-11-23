import urllib.request
import json

resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
for t in resp:
    if t.get('type') == 'page':
        print(f"[{t.get('id')}] {t.get('title')} | {t.get('url')}")
