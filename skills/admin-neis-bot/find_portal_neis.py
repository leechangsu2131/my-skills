import json
import urllib.request
import websocket

tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=3).read())
portal_tab = next((t for t in tabs if 'eduptl' in t.get('url', '')), None)
if not portal_tab:
    print("Portal tab not found")
    exit()

ws_url = portal_tab['webSocketDebuggerUrl']
ws = websocket.create_connection(ws_url, timeout=5, suppress_origin=True)

js = """
(function(){
    var elements = Array.from(document.querySelectorAll('a, button, div, span, img')).filter(el => {
        var t = el.innerText || el.getAttribute('title') || el.getAttribute('alt') || '';
        var h = el.getAttribute('href') || '';
        var o = el.getAttribute('onclick') || '';
        var id = el.id || '';
        return (t.includes('나이스') || t.includes('NEIS') || h.includes('neis') || o.includes('neis') || id.includes('neis'));
    }).map(el => ({
        tag: el.tagName,
        id: el.id,
        className: el.className,
        text: (el.innerText || '').trim(),
        onclick: el.getAttribute('onclick') || '',
        href: el.getAttribute('href') || ''
    }));
    return elements;
})()
"""

msg = {
    "id": 1,
    "method": "Runtime.evaluate",
    "params": {
        "expression": js,
        "returnByValue": True
    }
}
ws.send(json.dumps(msg))
res = json.loads(ws.recv())
elements = res.get('result', {}).get('result', {}).get('value', [])
print("Found NEIS elements in portal:")
print(json.dumps(elements, ensure_ascii=False, indent=2))
ws.close()
