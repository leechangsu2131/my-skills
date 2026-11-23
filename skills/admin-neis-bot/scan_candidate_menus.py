import urllib.request
import json
import time
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    candidates = [
        ("학부모서비스승인관리", "AMELS40004"),
        ("학생주소연계", "AMELS40046"),
        ("학생부조회및출력", "AMELS40218"),
        ("반편성결과조회", "AMELS40186"),
    ]
    
    for title, mid in candidates:
        js = f"""
        (() => {{
            var idx = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes("Index"));
            return idx.callAppMethod("doOpenMenuToMdi", ["{mid}"]);
        }})()
        """
        ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
        ws.recv()
        time.sleep(3)
        
        js_inspect = """
        (() => {
            var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
            var last = instances[instances.length - 1];
            if (!last || !last.app) return {error: "no app"};
            
            var all = last.getContainer().getAllRecursiveChildren();
            var buttons = [];
            var grids = [];
            for (var i = 0; i < all.length; i++) {
                var c = all[i];
                if (c.type === 'button') {
                    buttons.push({id: c.id, text: c.text});
                } else if (c.type === 'grid') {
                    var cols = [];
                    if (c.header) {
                        for (var j = 0; j < c.columnCount; j++) {
                            cols.push(c.header.getColumn(j) ? c.header.getColumn(j).getText() : '');
                        }
                    }
                    grids.push({id: c.id, cols: cols});
                }
            }
            return {
                appId: last.app.id,
                buttons: buttons,
                grids: grids,
                datasets: last.getAllDataControls().map(d => ({
                    id: d.id,
                    cols: d instanceof cpr.data.DataSet ? d.getColumnNames() : []
                }))
            };
        })()
        """
        ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_inspect, 'returnByValue': True}}))
        res = json.loads(ws.recv())
        data = res.get('result', {}).get('result', {}).get('value')
        print(f"=== {title} ({mid}) -> {data.get('appId')} ===")
        print("Buttons:", [b['text'] for b in data.get('buttons', [])])
        for g in data.get('grids', []):
            print("Grid cols:", [col.replace('\r\n', ' ') for col in g['cols'] if col])
        for d in data.get('datasets', []):
            if any('guard' in col.lower() or 'prnt' in col.lower() or '보호' in col or '학부모' in col for col in d['cols']):
                print(f"Dataset {d['id']} with guardian cols:", d['cols'])
        print()

    ws.close()

if __name__ == '__main__':
    main()
