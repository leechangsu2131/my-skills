import urllib.request
import json
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    portal_tab = next((t for t in resp if 'eduptl' in t.get('url', '')), None)
    if not portal_tab:
        print("No portal tab found!")
        return
    
    print("Found portal tab:", portal_tab['title'], portal_tab['url'], portal_tab['id'])
    ws_url = portal_tab['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=5)
    
    js = """
    (() => {
        var links = Array.from(document.querySelectorAll('a')).map(a => ({
            id: a.id,
            className: a.className,
            text: a.innerText.trim(),
            href: a.href,
            onclick: a.getAttribute('onclick')
        }));
        return links.filter(l => l.id.includes('neis') || l.text.includes('나이스') || (l.href && l.href.includes('neis')) || (l.onclick && l.onclick.includes('neis')));
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Portal NEIS links:", json.dumps(res.get('result', {}).get('result', {}).get('value'), ensure_ascii=False, indent=2))
    ws.close()

if __name__ == '__main__':
    main()
