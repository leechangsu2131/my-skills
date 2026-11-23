import urllib.request
import json
import csv
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if t.get('id') == '95ECC5D4F751F9C6BFFEAC8B8DDF0490'), None)
    if not neis_tab:
        print("Tab not found!")
        return
        
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    ws.send(json.dumps({
        'id': 1,
        'method': 'Runtime.evaluate',
        'params': {'expression': 'window.__parent_data', 'returnByValue': True}
    }))
    res = json.loads(ws.recv())
    data = res.get('result', {}).get('result', {}).get('value', [])
    ws.close()
    
    print(f"Extracted data for {len(data)} students.")
    
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
                
    print(f"CSV 저장 완료: {csv_path}")
    
    # Summary count
    with_parent = sum(1 for s in data if s.get('parents'))
    print(f"보호자 등록 확인: {with_parent}명 / 전체 {len(data)}명")

if __name__ == '__main__':
    main()
