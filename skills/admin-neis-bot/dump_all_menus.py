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
            rows.push({
                id: r.menuId,
                name: r.menuNm,
                depth: r.menuNmDepth,
                up: r.upMenuId,
                page: r.CALL_PAGE,
                desc: r.MENU_DESC
            });
        }
        return rows;
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    rows = res.get('result', {}).get('result', {}).get('value', [])
    
    dump_path = r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\admin-neis-bot\all_neis_menus.json"
    with open(dump_path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"Dumped {len(rows)} menus to {dump_path}")

    ws.close()

if __name__ == '__main__':
    main()
