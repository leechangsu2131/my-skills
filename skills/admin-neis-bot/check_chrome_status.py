import io, sys, json, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    with urllib.request.urlopen('http://127.0.0.1:9222/json') as response:
        tabs = json.loads(response.read().decode())
        print(f"Total tabs: {len(tabs)}")
        for t in tabs:
            print(f"- {t.get('title')} ({t.get('url')})")
except Exception as e:
    print("Error connecting to Chrome 9222:", e)
