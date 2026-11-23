import urllib.request
import json
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=10)
    
    js = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var out = [];
        for (var i = 0; i < instances.length; i++) {
            var ai = instances[i];
            var all = ai.getContainer().getAllRecursiveChildren();
            for (var j = 0; j < all.length; j++) {
                var c = all[j];
                var t = c.text || '';
                if (t.includes('기본신상관리') || t.includes('명렬표출력')) {
                    out.push({
                        appId: ai.app ? ai.app.id : 'no-id',
                        ctrlId: c.id,
                        type: c.type,
                        text: t
                    });
                }
            }
        }
        return out;
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print(json.dumps(res.get('result', {}).get('result', {}).get('value'), ensure_ascii=False, indent=2))
    ws.close()

if __name__ == '__main__':
    main()
