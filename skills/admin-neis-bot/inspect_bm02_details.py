import urllib.request
import json
import base64
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    # 1. Inspect grd1 columns and dmSearch
    js = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_srgbm02_m00"));
        if (!app) return {error: "app not found"};
        
        var grd1 = app.lookup("grd1");
        var cols = [];
        if (grd1 && grd1.header) {
            for (var c = 0; c < grd1.columnCount; c++) {
                cols.push({
                    colIndex: c,
                    text: grd1.header.getColumn(c) ? grd1.header.getColumn(c).getText() : ''
                });
            }
        }
        
        var dmSearch = app.lookup("dmSearch");
        var dmData = dmSearch ? dmSearch.getDatas() : null;
        
        var dsList = app.lookup("dsListItmInq");
        var dsCols = dsList ? dsList.getColumnNames() : [];
        var rowCount = dsList ? dsList.getRowCount() : 0;
        
        return {
            cols: cols,
            dmSearch: dmData,
            dsCols: dsCols,
            rowCount: rowCount
        };
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Screen details:", json.dumps(res.get('result', {}).get('result', {}).get('value'), ensure_ascii=False, indent=2))
    
    # Capture screenshot to see the screen visually
    ws.send(json.dumps({'id': 2, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
    res = json.loads(ws.recv())
    img_b64 = res.get('result', {}).get('data')
    if img_b64:
        img_path = r"C:\Users\user\.gemini\antigravity\brain\fde9f22d-fe7a-43bc-9514-58c8a0680c48\neis_bm02_screen.png"
        with open(img_path, 'wb') as f:
            f.write(base64.b64decode(img_b64))
        print("Saved screenshot to:", img_path)
        
    ws.close()

if __name__ == '__main__':
    main()
