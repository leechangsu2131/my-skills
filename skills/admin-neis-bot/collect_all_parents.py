import urllib.request
import json
import time
import csv
import os
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if t.get('id') == '95ECC5D4F751F9C6BFFEAC8B8DDF0490'), None)
    if not neis_tab:
        print("Tab not found!")
        return
        
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=10)
    
    # 1. Start async collection in browser
    js_start = """
    (() => {
        window.__parent_done = false;
        window.__parent_data = [];
        window.__parent_progress = 0;
        
        (async () => {
            try {
                var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
                var app = instances.find(ai => ai.app && ai.app.id.includes("els_sdlpa00_m00"));
                if (!app) {
                    window.__parent_error = "els_sdlpa00_m00 not found";
                    window.__parent_done = true;
                    return;
                }
                
                var grd = app.lookup("grdMain");
                var dsStu = app.lookup("dsStu");
                var dsSchpaAprv = app.lookup("dsSchpaAprv");
                var count = dsStu.getRowCount();
                
                var results = [];
                for (var i = 0; i < count; i++) {
                    window.__parent_progress = i + 1;
                    var s = dsStu.getRowData(i);
                    grd.selectRows([i]);
                    
                    // Wait for dsSchpaAprv to load or timeout 800ms
                    for (var w = 0; w < 8; w++) {
                        await new Promise(r => setTimeout(r, 100));
                        if (dsSchpaAprv.getRowCount() > 0) {
                            var pRow = dsSchpaAprv.getRowData(0);
                            if (pRow.stuDtcNo === s.stuDtcNo) break;
                        }
                    }
                    
                    var parents = [];
                    for (var p = 0; p < dsSchpaAprv.getRowCount(); p++) {
                        var pData = dsSchpaAprv.getRowData(p);
                        if (pData.stuDtcNo === s.stuDtcNo) {
                            parents.push({
                                parentName: pData.userNm,
                                telNo: pData.mblTelno,
                                status: pData.aprvStsCdNm
                            });
                        }
                    }
                    
                    results.push({
                        no: s.clsNo,
                        name: s.stuFlnm,
                        brdt: s.stuBrdt,
                        parents: parents
                    });
                }
                
                window.__parent_data = results;
                window.__parent_done = true;
            } catch(e) {
                window.__parent_error = e.toString();
                window.__parent_done = true;
            }
        })();
        
        return {started: true};
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js_start, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Started background task in browser:", res.get('result', {}).get('result', {}).get('value'))
    
    # 2. Poll until done
    for attempt in range(40):
        time.sleep(1)
        ws.send(json.dumps({
            'id': 100 + attempt,
            'method': 'Runtime.evaluate',
            'params': {'expression': '({done: window.__parent_done, progress: window.__parent_progress, err: window.__parent_error})', 'returnByValue': True}
        }))
        res = json.loads(ws.recv())
        status = res.get('result', {}).get('result', {}).get('value', {})
        print(f"[{attempt+1}s] Progress: {status.get('progress')}/19, Done: {status.get('done')}")
        if status.get('done'):
            break
            
    # 3. Retrieve data
    ws.send(json.dumps({
        'id': 200,
        'method': 'Runtime.evaluate',
        'params': {'expression': 'window.__parent_data', 'returnByValue': True}
    }))
    res = json.loads(ws.recv())
    data = res.get('result', {}).get('result', {}).get('value', [])
    ws.close()
    
    print(f"\n[추출 완료] 총 {len(data)}명 데이터 수집 성공!")
    
    # Save to CSV in Downloads
    csv_path = r"C:\Users\user\Downloads\3학년2반_학생_생년월일_보호자명단.csv"
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["번호", "학생성명", "생년월일", "보호자성명", "보호자연락처", "학부모서비스상태"])
        for s in data:
            parents = s.get('parents', [])
            if parents:
                for p in parents:
                    writer.writerow([s['no'], s['name'], s['brdt'], p['parentName'], p['telNo'], p['status']])
            else:
                writer.writerow([s['no'], s['name'], s['brdt'], "미등록", "", ""])
                
    print(f"CSV 파일 저장 완료: {csv_path}")

if __name__ == '__main__':
    main()
