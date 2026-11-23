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
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_srgbm02_m00"));
        if (!app) return {error: "app not found"};
        
        var btnSearch = app.lookup("btnSearch");
        if (btnSearch) {
            btnSearch.click();
            return {clickedSearch: true};
        }
        return {clickedSearch: false};
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Click search:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(3)
    
    # Check row count
    js_data = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_srgbm02_m00"));
        if (!app) return {error: "app not found"};
        
        var ds = app.lookup("dsListItmInq");
        var count = ds ? ds.getRowCount() : 0;
        var sample = count > 0 ? ds.getRowData(0) : null;
        return {rowCount: count, cols: ds ? ds.getColumnNames() : [], sampleKeys: sample ? Object.keys(sample) : []};
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_data, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Data after search:", json.dumps(res.get('result', {}).get('result', {}).get('value'), ensure_ascii=False, indent=2))
    
    # Screenshot
    ws.send(json.dumps({'id': 3, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
    res = json.loads(ws.recv())
    img_b64 = res.get('result', {}).get('data')
    if img_b64:
        img_path = r"C:\Users\user\.gemini\antigravity\brain\fde9f22d-fe7a-43bc-9514-58c8a0680c48\neis_bm02_searched.png"
        with open(img_path, 'wb') as f:
            f.write(base64.b64decode(img_b64))
        print("Saved screenshot to:", img_path)
        
    ws.close()

if __name__ == '__main__':
    main()
