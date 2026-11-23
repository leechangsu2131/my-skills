import urllib.request
import json
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=10)
    
    js = """
    (() => {
        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        var node;
        var found = [];
        while(node = walker.nextNode()) {
            if (node.nodeValue && (node.nodeValue.includes('개인정보') || node.nodeValue.includes('사유') || node.nodeValue.includes('제출'))) {
                var p = node.parentElement;
                var rect = p.getBoundingClientRect();
                found.push({
                    text: node.nodeValue.trim(),
                    tag: p.tagName,
                    class: p.className,
                    rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height}
                });
            }
        }
        return found;
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print(json.dumps(res.get('result', {}).get('result', {}).get('value'), ensure_ascii=False, indent=2))
    ws.close()

if __name__ == '__main__':
    main()
