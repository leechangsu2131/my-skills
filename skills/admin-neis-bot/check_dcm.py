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
        var idx = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes("Index"));
        return idx.callAppMethod("doOpenMenuToMdi", ["AMDCM30001"]);
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Call AMDCM30001:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(3)
    
    # Check apps
    js_apps = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("dcm_schdp01_m01"));
        if (!app) return {error: "not found"};
        return {
            appId: app.app.id,
            buttons: app.getContainer().getAllRecursiveChildren().filter(c => c.type === 'button').map(b => ({id: b.id, text: b.text})),
            grids: app.getContainer().getAllRecursiveChildren().filter(c => c.type === 'grid').map(g => {
                var cols = [];
                if (g.header) {
                    for (var i = 0; i < g.columnCount; i++) {
                        cols.push(g.header.getColumn(i) ? g.header.getColumn(i).getText() : '');
                    }
                }
                return {id: g.id, cols: cols};
            }),
            datasets: app.getAllDataControls().map(d => ({
                id: d.id,
                cols: d instanceof cpr.data.DataSet ? d.getColumnNames() : []
            }))
        };
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_apps, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("App details:", json.dumps(res.get('result', {}).get('result', {}).get('value'), ensure_ascii=False, indent=2))
    ws.close()

if __name__ == '__main__':
    main()
