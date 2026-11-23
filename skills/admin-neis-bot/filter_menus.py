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
        var out = [];
        for (var i = 0; i < ds.getRowCount(); i++) {
            var r = ds.getRowData(i);
            var nm = r.menuNm || '';
            if (r.CALL_PAGE && (nm.includes('학부모') || nm.includes('학생부') || nm.includes('인적') || nm.includes('신상') || nm.includes('주소') || nm.includes('가족') || nm.includes('연계'))) {
                out.push({id: r.menuId, nm: r.menuNm, page: r.CALL_PAGE, depth: r.menuNmDepth});
            }
        }
        return out;
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    rows = res.get('result', {}).get('result', {}).get('value', [])
    for r in rows:
        print(f"[{r['id']}] {r['depth']} ({r['nm']}) -> {r['page']}")

    ws.close()

if __name__ == '__main__':
    main()
