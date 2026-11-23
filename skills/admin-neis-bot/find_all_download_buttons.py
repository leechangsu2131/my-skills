import urllib.request
import json
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=10)
    
    js = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var eduApps = instances.filter(a => a.app && a.app.id.startsWith('edu/'));
        var res = [];
        for (var i = 0; i < eduApps.length; i++) {
            var a = eduApps[i];
            var cont = a.getContainer();
            var all = cont ? cont.getAllRecursiveChildren() : [];
            var btns = [];
            var grids = [];
            for (var j = 0; j < all.length; j++) {
                var c = all[j];
                if (c.type === 'button') {
                    btns.push({id: c.id, text: c.text});
                } else if (c.type === 'grid') {
                    var cols = [];
                    if (c.header) {
                        for (var k = 0; k < c.columnCount; k++) {
                            cols.push(c.header.getColumn(k) ? c.header.getColumn(k).getText() : '');
                        }
                    }
                    grids.push({id: c.id, cols: cols.map(x => x.replace(/\\r?\\n/g, ' '))});
                }
            }
            res.push({
                appId: a.app.id,
                buttons: btns,
                grids: grids
            });
        }
        return res;
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    data = res.get('result', {}).get('result', {}).get('value', [])
    for app in data:
        print(f"\n=== App: {app['appId']} ===")
        print("  Buttons:", [f"{b['id']}: {b['text']}" for b in app['buttons']])
        for g in app['grids']:
            print(f"  Grid {g['id']}:", [col for col in g['cols'] if col])

    ws.close()

if __name__ == '__main__':
    main()
