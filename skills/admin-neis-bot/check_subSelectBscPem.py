import urllib.request
import json
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=10)
    
    js = """
    (() => {
        try {
            var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
            var app = instances.find(ai => ai.app && ai.app.id.includes("els_srgbm00_m00"));
            if (!app) return {error: "app not found"};
            
            var sub = app.lookup("subSelectBscPem");
            return {
                action: sub ? sub.action : null,
                mediaType: sub ? sub.mediaType : null
            };
        } catch(e) {
            return {error: e.toString()};
        }
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print(json.dumps(res.get('result', {}).get('result', {}).get('value'), ensure_ascii=False, indent=2))
    ws.close()

if __name__ == '__main__':
    main()
