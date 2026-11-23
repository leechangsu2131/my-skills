import urllib.request
import json
import time
import base64
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    # 1. Close popup
    js_close = """
    (() => {
        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        var node;
        while(node = walker.nextNode()) {
            if (node.nodeValue === '닫기') {
                var p = node.parentElement;
                p.click();
                return {closed: true};
            }
        }
        return {closed: false};
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js_close, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Closed popup:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(1)
    
    # 2. Click 학생부조회및출력 tab at the bottom
    js_tab = """
    (() => {
        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        var node;
        while(node = walker.nextNode()) {
            if (node.nodeValue === '학생부조회및출력') {
                var p = node.parentElement;
                var rect = p.getBoundingClientRect();
                if (rect.y > 800) {
                    p.click();
                    return {clickedTab: true, rect: {x: rect.x, y: rect.y}};
                }
            }
        }
        return {clickedTab: false};
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_tab, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Switch tab:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(2)
    
    # 3. Screenshot
    ws.send(json.dumps({'id': 3, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
    res = json.loads(ws.recv())
    img_b64 = res.get('result', {}).get('data')
    if img_b64:
        img_path = r"C:\Users\user\.gemini\antigravity\brain\fde9f22d-fe7a-43bc-9514-58c8a0680c48\neis_slrcm00_screen.png"
        with open(img_path, 'wb') as f:
            f.write(base64.b64decode(img_b64))
        print("Saved screenshot to:", img_path)
        
    ws.close()

if __name__ == '__main__':
    main()
