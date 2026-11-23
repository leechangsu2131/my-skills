import urllib.request
import json
import time
import os
import websocket

def main():
    download_dir = r"C:\Users\user\Downloads"
    files_before = set(os.listdir(download_dir))
    
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if t.get('id') == '95ECC5D4F751F9C6BFFEAC8B8DDF0490'), None)
    if not neis_tab:
        print("NEIS tab not found!")
        return
        
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    # 1. Allow download in CDP
    ws.send(json.dumps({
        'id': 1,
        'method': 'Page.setDownloadBehavior',
        'params': {
            'behavior': 'allow',
            'downloadPath': download_dir
        }
    }))
    print("setDownloadBehavior:", ws.recv())
    
    # 2. Fill reason in privateCmtPop and click btnConfirm
    js_submit = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var pop = instances.find(ai => ai.app && ai.app.id.includes("privateCmtPop"));
        if (!pop) return {error: "privateCmtPop not found"};
        
        var cmb = pop.lookup("cmbReason");
        if (cmb) {
            cmb.value = "업무수행";
            try { cmb.dispatchEvent(new cpr.events.CUIEvent("selection-dispose")); } catch(e){}
            try { cmb.dispatchEvent(new cpr.events.CUIEvent("value-change")); } catch(e){}
        }
        
        var txa = pop.lookup("txaReason");
        if (txa) {
            txa.value = "2027 학습지원 신청";
            try { txa.dispatchEvent(new cpr.events.CUIEvent("value-change")); } catch(e){}
        }
        
        var btn = pop.lookup("btnConfirm");
        if (btn) {
            btn.click();
            return {
                success: true,
                cmbVal: cmb ? cmb.value : null,
                txaVal: txa ? txa.value : null
            };
        }
        return {error: "btnConfirm not found"};
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_submit, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Submit result:", res.get('result', {}).get('result', {}).get('value'))
    
    # Wait for download
    print("Waiting 10 seconds for download to complete...")
    for i in range(10):
        time.sleep(1)
        files_after = set(os.listdir(download_dir))
        new_files = files_after - files_before
        if new_files:
            print(f"[{i+1}s] Detected new files:", new_files)
            
    files_after = set(os.listdir(download_dir))
    new_files = files_after - files_before
    print("Final downloaded files:", new_files)
    
    ws.close()

if __name__ == '__main__':
    main()
