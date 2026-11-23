import urllib.request
import json
import time
import base64
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    js = """
    (() => {
        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        var node;
        while(node = walker.nextNode()) {
            if (node.nodeValue === '기본신상관리') {
                var p = node.parentElement;
                var rect = p.getBoundingClientRect();
                if (rect.y > 800) {
                    p.click();
                    return {clicked: true, rect: {x: rect.x, y: rect.y}};
                }
            }
        }
        return {clicked: false};
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Click tab result:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(2)
    
    # Screenshot
    ws.send(json.dumps({'id': 2, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
    res = json.loads(ws.recv())
    img_b64 = res.get('result', {}).get('data')
    if img_b64:
        img_path = r"C:\Users\user\.gemini\antigravity\brain\fde9f22d-fe7a-43bc-9514-58c8a0680c48\neis_clicked_bm00.png"
        with open(img_path, 'wb') as f:
            f.write(base64.b64decode(img_b64))
        print("Saved screenshot to:", img_path)
        
    ws.close()

if __name__ == '__main__':
    main()
