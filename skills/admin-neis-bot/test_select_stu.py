import urllib.request
import json
import time
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    js = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_sdlpa00_m00"));
        var grd = app.lookup("grdMain");
        grd.selectRows([0]);
        return {selected: 0};
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Selected row 0:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(2)
    
    # Check dsSchpaAprv
    js_check = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_sdlpa00_m00"));
        var ds = app.lookup("dsSchpaAprv");
        return {
            count: ds ? ds.getRowCount() : 0,
            rows: ds ? ds.getRowDataRanged() : []
        };
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_check, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("dsSchpaAprv:", json.dumps(res.get('result', {}).get('result', {}).get('value'), ensure_ascii=False, indent=2))
    ws.close()

if __name__ == '__main__':
    main()
