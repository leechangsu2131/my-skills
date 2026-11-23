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
        if (!app) return {error: "app not found"};
        
        var btnSearch = app.lookup("btnSearch");
        if (btnSearch) {
            btnSearch.click();
            return {clicked: true};
        }
        return {clicked: false};
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Click search on bm00:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(3)
    
    # Check datasets in bm00
    js_ds = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_srgbm00_m00"));
        if (!app) return {error: "app not found"};
        
        var dss = app.getAllDataControls();
        var res = [];
        for (var i = 0; i < dss.length; i++) {
            var d = dss[i];
            if (d instanceof cpr.data.DataSet && d.getRowCount() > 0) {
                res.push({
                    id: d.id,
                    rowCount: d.getRowCount(),
                    cols: d.getColumnNames(),
                    firstRow: d.getRowData(0)
                });
            }
        }
        return res;
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_ds, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    data = res.get('result', {}).get('result', {}).get('value', [])
    for d in data:
        print(f"Dataset {d['id']} (rows: {d['rowCount']}): cols={d['cols']}")
        print(f"  Sample keys: {list(d['firstRow'].keys())}")
        
    # Screenshot
    ws.send(json.dumps({'id': 3, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
    res = json.loads(ws.recv())
    img_b64 = res.get('result', {}).get('data')
    if img_b64:
        img_path = r"C:\Users\user\.gemini\antigravity\brain\fde9f22d-fe7a-43bc-9514-58c8a0680c48\neis_bm00_searched.png"
        with open(img_path, 'wb') as f:
            f.write(base64.b64decode(img_b64))
        print("Saved screenshot to:", img_path)
        
    ws.close()

if __name__ == '__main__':
    main()
