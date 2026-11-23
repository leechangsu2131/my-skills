import urllib.request
import json
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=10)
    
    js = """
    (() => {
        var idx = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes("Index"));
        var ds = idx.lookup("dsAllMenu");
        var rows = [];
        for (var i = 0; i < ds.getRowCount(); i++) {
            var r = ds.getRowData(i);
            if (r.shlDptWrkCd === '002001') {
                rows.push({
                    id: r.menuId,
                    name: r.menuNm,
                    depth: r.menuNmDepth,
                    page: r.CALL_PAGE,
                    pgm: r.PGM_ID
                });
            }
        }
        return rows;
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    rows = res.get('result', {}).get('result', {}).get('value', [])
    print(f"Total 학급담임 menus: {len(rows)}")
    for r in rows:
        print(f"[{r['id']}] {r['depth']} ({r['name']}) -> {r['page']}")

    ws.close()

if __name__ == '__main__':
    main()
