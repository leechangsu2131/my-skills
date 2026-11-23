import urllib.request
import json
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    js = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_srgbm00_m00"));
        if (!app) return {error: "els_srgbm00_m00 not found"};
        
        // Find all buttons, controls, combos, grids
        var ctrls = [];
        var allCtrls = app.getContainer().getAllRecursiveChildren();
        for (var i = 0; i < allCtrls.length; i++) {
            var c = allCtrls[i];
            var type = c.type;
            var id = c.id;
            var val = '';
            var text = '';
            try { if (c.value !== undefined) val = String(c.value); } catch(e){}
            try { if (c.text !== undefined) text = String(c.text); } catch(e){}
            
            if (type === 'button' || type === 'grid' || type === 'combobox' || (text && (text.includes('다운') || text.includes('조회') || text.includes('엑셀')))) {
                ctrls.push({
                    id: id,
                    type: type,
                    text: text,
                    value: val,
                    visible: c.visible,
                    enabled: c.enabled
                });
            }
        }
        
        // Check datasets
        var dss = app.getAllDataControls().map(d => ({
            id: d.id,
            type: d.type,
            rowCount: d instanceof cpr.data.DataSet ? d.getRowCount() : null,
            cols: d instanceof cpr.data.DataSet ? d.getColumnNames() : null
        }));
        
        return {
            ctrls: ctrls,
            datasets: dss
        };
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    data = res.get('result', {}).get('result', {}).get('value')
    print("Controls:")
    for c in data.get('ctrls', []):
        print(f"  [{c['type']}] id='{c['id']}' text='{c['text']}' val='{c['value']}' enabled={c['enabled']}")
        
    print("\nDatasets:")
    for d in data.get('datasets', []):
        print(f"  [{d['type']}] id='{d['id']}' rowCount={d['rowCount']} cols={d['cols']}")
        
    ws.close()

if __name__ == '__main__':
    main()
