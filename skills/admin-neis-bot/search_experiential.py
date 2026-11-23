import urllib.request
import json
import time
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if t.get('id') == '95ECC5D4F751F9C6BFFEAC8B8DDF0490'), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    js_data = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("eds_eaaae01_m01"));
        if (!app) return {error: "app not found"};
        
        var dss = app.getAllDataControls().filter(d => d instanceof cpr.data.DataSet);
        var out = [];
        for (var i = 0; i < dss.length; i++) {
            var d = dss[i];
            out.push({
                id: d.id,
                count: d.getRowCount(),
                cols: d.getColumnNames(),
                rows: d.getRowDataRanged()
            });
        }
        return out;
    })()
    """
    ws.send(json.dumps({'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': js_data, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    data = res.get('result', {}).get('result', {}).get('value')
    if isinstance(data, list):
        for ds in data:
            print(f"DataSet {ds['id']} ({ds['count']} rows)")
            for r in ds.get('rows', []):
                for name in ['백다온', '오지윤', '이서우', '이예나', '천선율']:
                    if name in str(r):
                        print(f"  FOUND {name} in {ds['id']}:", {k: v for k, v in r.items() if v and not k.startswith('_')})
    else:
        print("Result:", data)

    ws.close()

if __name__ == '__main__':
    main()
