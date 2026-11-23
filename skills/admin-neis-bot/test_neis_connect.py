import urllib.request
import json
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    if not neis_tab:
        print("No NEIS tab found!")
        return
    
    print("Found NEIS tab:", neis_tab['title'], neis_tab['url'], neis_tab['id'])
    ws_url = neis_tab['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=10)
    
    # 1. Get title and url
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': 'document.title + " | " + window.location.href'}}))
    res = json.loads(ws.recv())
    print("Page info:", res.get('result', {}).get('result', {}).get('value'))
    
    # 2. Check if cpr is loaded
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': 'typeof cpr !== "undefined"'}}))
    res = json.loads(ws.recv())
    has_cpr = res.get('result', {}).get('result', {}).get('value')
    print("Has CPR:", has_cpr)
    
    if has_cpr:
        # Check running apps
        js = """
        (() => {
            if (typeof cpr === 'undefined') return 'no cpr';
            var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
            return apps.map(a => a.app ? a.app.id : 'no-id');
        })()
        """
        ws.send(json.dumps({'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
        res = json.loads(ws.recv())
        print("Running apps:", res.get('result', {}).get('result', {}).get('value'))
    
    ws.close()

if __name__ == '__main__':
    main()
