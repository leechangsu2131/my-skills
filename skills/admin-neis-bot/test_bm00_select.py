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
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_srgbm00_m00"));
        var grd = app.lookup("grdBmList");
        grd.selectRows([0]);
        return {selected: 0};
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Selected row 0 in bm00:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(2)
    
    # Check all datasets in bm00
    js_dss = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_srgbm00_m00"));
        return app.getAllDataControls().filter(d => d instanceof cpr.data.DataSet && d.getRowCount() > 0).map(d => ({
            id: d.id,
            count: d.getRowCount(),
            sample: d.getRowData(0)
        }));
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_dss, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    data = res.get('result', {}).get('result', {}).get('value')
    for d in data:
        print(f"Dataset {d['id']} ({d['count']} rows):")
        print(" ", list(d['sample'].keys()))
        
    ws.close()

if __name__ == '__main__':
    main()
