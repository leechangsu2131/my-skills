import urllib.request
import json
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    js = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_srgbm02_m00"));
        if (!app) return {error: "app not found"};
        
        var btn1 = app.lookup("btn1");
        var btnSearch = app.lookup("btnSearch");
        var btn6 = app.lookup("btn6");
        
        // Let's inspect listeners
        return {
            btn1: btn1 ? {id: btn1.id, text: btn1.text} : null,
            btn6: btn6 ? {id: btn6.id, text: btn6.text} : null
        };
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print(res.get('result', {}).get('result', {}).get('value'))
    ws.close()

if __name__ == '__main__':
    main()
