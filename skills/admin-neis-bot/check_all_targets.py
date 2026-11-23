import json
import urllib.request

tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=3).read())
for i, t in enumerate(tabs):
    print(f"[{i}] type={t.get('type')} | title={t.get('title')} | url={t.get('url')[:80]}")
