import urllib.request
import json
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    portal_tab = next((t for t in resp if 'eduptl' in t.get('url', '')), None)
    if not portal_tab:
        print("Portal tab not found!")
        return
        
    ws = websocket.create_connection(portal_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=10)
    js = """
    (() => {
        var links = Array.from(document.querySelectorAll('a.qTodoBtn')).map(a => ({
            id: a.id,
            text: a.innerText.trim()
        }));
        return links.filter(l => l.text.includes('학생C') || l.text.includes('학생B') || l.text.includes('학생A') || l.text.includes('학생D') || l.text.includes('학생E'));
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print(json.dumps(res.get('result', {}).get('result', {}).get('value'), ensure_ascii=False, indent=2))
    ws.close()

if __name__ == '__main__':
    main()
