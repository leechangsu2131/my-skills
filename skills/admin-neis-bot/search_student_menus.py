import urllib.request
import json
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    if not neis_tab:
        print("No NEIS tab found!")
        return
        
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=10)
    
    # Search all datasets in Index app
    js = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var idx = instances.find(ai => ai.app && ai.app.id.includes("Index"));
        if (!idx) return {error: "Index app not found"};
        
        var results = [];
        var dss = idx.getAllDataControls();
        for (var i = 0; i < dss.length; i++) {
            var ds = dss[i];
            if (ds instanceof cpr.data.DataSet) {
                var rowCount = ds.getRowCount();
                for (var r = 0; r < rowCount; r++) {
                    var rowData = ds.getRowData(r);
                    var str = JSON.stringify(rowData);
                    // Match student, record, info, etc.
                    if (str.includes("학생") || str.includes("학적") || str.includes("신상") || str.includes("명부") || str.includes("담임")) {
                        results.push({
                            dsId: ds.id,
                            menuId: rowData.menuId || rowData.MENU_ID || rowData.pgmId || rowData.PGM_ID,
                            menuNm: rowData.menuNm || rowData.MENU_NM || rowData.pgmNm || rowData.PGM_NM,
                            callUrl: rowData.callUrl || rowData.CALL_URL,
                            raw: rowData
                        });
                    }
                }
            }
        }
        return {count: results.length, items: results.slice(0, 50)};
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    data = res.get('result', {}).get('result', {}).get('value')
    print("Found menu items count:", data.get('count') if isinstance(data, dict) else data)
    if isinstance(data, dict) and 'items' in data:
        for item in data['items']:
            print(f"[{item.get('dsId')}] menuId: {item.get('menuId')} | menuNm: {item.get('menuNm')} | url: {item.get('callUrl')}")
            
    ws.close()

if __name__ == '__main__':
    main()
