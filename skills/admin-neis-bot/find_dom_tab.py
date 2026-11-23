import urllib.request
import json
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=10)
    
    js = """
    (() => {
        var iframes = Array.from(document.querySelectorAll('iframe')).map(f => ({
            id: f.id,
            name: f.name,
            src: f.src
        }));
        
        var matches = [];
        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        var node;
        while(node = walker.nextNode()) {
            if (node.nodeValue && node.nodeValue.includes('기본신상관리')) {
                var p = node.parentElement;
                var rect = p.getBoundingClientRect();
                matches.push({
                    text: node.nodeValue,
                    tag: p.tagName,
                    class: p.className,
                    rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height}
                });
            }
        }
        return {
            iframes: iframes,
            textMatches: matches
        };
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print(json.dumps(res.get('result', {}).get('result', {}).get('value'), ensure_ascii=False, indent=2))
    ws.close()

if __name__ == '__main__':
    main()
