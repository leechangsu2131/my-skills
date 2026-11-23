import urllib.request
import json
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if t.get('id') == '95ECC5D4F751F9C6BFFEAC8B8DDF0490'), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=10)
    
    js = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var pop = instances.find(ai => ai.app && ai.app.id.includes("privateCmtPop"));
        if (!pop) return {error: "privateCmtPop not found"};
        
        var all = pop.getContainer().getAllRecursiveChildren();
        return {
            appId: pop.app.id,
            controls: all.map(c => ({
                id: c.id,
                type: c.type,
                text: c.text,
                value: c.value
            })),
            datasets: pop.getAllDataControls().map(d => ({
                id: d.id,
                type: d.type,
                cols: d instanceof cpr.data.DataSet ? d.getColumnNames() : null,
                rows: d instanceof cpr.data.DataSet ? d.getRowDataRanged() : null
            }))
        };
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print(json.dumps(res.get('result', {}).get('result', {}).get('value'), ensure_ascii=False, indent=2))
    ws.close()

if __name__ == '__main__':
    main()
