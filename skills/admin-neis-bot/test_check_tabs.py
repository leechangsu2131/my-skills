import json
import urllib.request

try:
    tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=3).read())
    for t in tabs:
        if t.get('type') == 'page':
            print(f"[{t.get('id')[:10]}] {t.get('title')} | {t.get('url')}")
except Exception as e:
    print("CDP Error:", e)
