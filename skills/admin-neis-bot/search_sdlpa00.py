import urllib.request
import json
import time
import base64
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    # 1. Inspect els_sdlpa00_m00
    js = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_sdlpa00_m00"));
        if (!app) return {error: "app not found"};
        
        var all = app.getContainer().getAllRecursiveChildren();
        var buttons = all.filter(c => c.type === 'button').map(b => ({id: b.id, text: b.text}));
        var grids = all.filter(c => c.type === 'grid').map(g => {
            var cols = [];
            if (g.header) {
                for (var j = 0; j < g.columnCount; j++) {
                    cols.push(g.header.getColumn(j) ? g.header.getColumn(j).getText() : '');
                }
            }
            return {id: g.id, cols: cols};
        });
        var dss = app.getAllDataControls().map(d => ({
            id: d.id,
            cols: d instanceof cpr.data.DataSet ? d.getColumnNames() : []
        }));
        
        // Click search if available
        var btnSearch = app.lookup("btnSearch");
        var clicked = false;
        if (btnSearch) {
            btnSearch.click();
            clicked = true;
        }
        
        return {
            buttons: buttons,
            grids: grids,
            datasets: dss,
            clickedSearch: clicked
        };
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print(json.dumps(res.get('result', {}).get('result', {}).get('value'), ensure_ascii=False, indent=2))
    
    time.sleep(3)
    
    # Check data after search
    js_after = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_sdlpa00_m00"));
        if (!app) return {error: "app not found"};
        
        return app.getAllDataControls().filter(d => d instanceof cpr.data.DataSet).map(d => ({
            id: d.id,
            count: d.getRowCount(),
            sample: d.getRowCount() > 0 ? d.getRowData(0) : null
        }));
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_after, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("\nData after search:", json.dumps(res.get('result', {}).get('result', {}).get('value'), ensure_ascii=False, indent=2))
    
    # Screenshot
    ws.send(json.dumps({'id': 3, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
    res = json.loads(ws.recv())
    img_b64 = res.get('result', {}).get('data')
    if img_b64:
        img_path = r"C:\Users\user\.gemini\antigravity\brain\fde9f22d-fe7a-43bc-9514-58c8a0680c48\neis_sdlpa00_searched.png"
        with open(img_path, 'wb') as f:
            f.write(base64.b64decode(img_b64))
        print("Saved screenshot to:", img_path)
        
    ws.close()

if __name__ == '__main__':
    main()
