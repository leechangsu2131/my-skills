"""
3학년 2반 학생 생년월일 및 보호자명 자동 추출 봇
=====================================================
admin-neis-bot 및 ISSUES.md 표준 준수:
- Chrome 9222 포트 연결
- eXBuilder6 CPR 프레임워크 기반 데이터셋(dsStdnt, dsFamily 등) 직접 탐색
- 개인정보 보호: 추출 데이터는 채팅창 노출 대신 선생님 로컬 PC Downloads 폴더에 CSV로 저장
"""

import os
import sys
import json
import csv
import urllib.request
import websocket
from datetime import datetime

CDP_HTTP = "http://127.0.0.1:9222"
DOWNLOADS_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
OUTPUT_CSV = os.path.join(DOWNLOADS_DIR, f"3학년2반_학생_보호자명단_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

def get_browser_ws_url():
    try:
        ver = json.loads(urllib.request.urlopen(f"{CDP_HTTP}/json/version", timeout=3).read())
        return ver.get("webSocketDebuggerUrl")
    except Exception as e:
        print(f"[오류] Chrome 9222 디버깅 포트 연결 실패: {e}")
        return None

def find_neis_tab():
    try:
        tabs = json.loads(urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=3).read())
        for t in tabs:
            if t.get("type") == "page" and "neis.go.kr" in t.get("url", ""):
                return t
    except Exception as e:
        print(f"[오류] 탭 목록 조회 실패: {e}")
    return None

def cdp_send(ws, msg_id, method, params=None, session_id=None):
    cmd = {"id": msg_id, "method": method}
    if params:
        cmd["params"] = params
    if session_id:
        cmd["sessionId"] = session_id
    ws.send(json.dumps(cmd))
    while True:
        raw = ws.recv()
        res = json.loads(raw)
        if res.get("id") == msg_id:
            return res

def extract_students():
    print("=" * 60)
    print("  나이스 3학년 2반 학생 생년월일 및 보호자명 추출 시작")
    print("=" * 60)

    neis_tab = find_neis_tab()
    if not neis_tab:
        print("\n[안내] 현재 Chrome(9222)에 나이스(neis.go.kr) 탭이 열려있지 않습니다.")
        print("▶ 조치 방법:")
        print("  1. 열려있는 업무포털(gbe.eduptl.kr) 화면에서 [나이스] 아이콘을 클릭하여 접속해주세요.")
        print("  2. 나이스에서 [학급담임]-[학적]-[기본신상관리] 또는 [학생명부] 화면으로 이동해주세요.")
        print("  3. 이동 후 본 스크립트를 다시 실행해주세요.\n")
        return False

    print(f"[확인] 나이스 탭 발견: {neis_tab.get('title')} ({neis_tab.get('id')[:10]}...)")

    browser_ws = get_browser_ws_url()
    if not browser_ws:
        return False

    ws = websocket.create_connection(browser_ws, timeout=10, suppress_origin=True)

    # Attach to NEIS tab with flatten=True
    msg_id = 1
    attach_res = cdp_send(ws, msg_id, "Target.attachToTarget", {
        "targetId": neis_tab["id"],
        "flatten": True
    })
    session_id = attach_res.get("result", {}).get("sessionId")
    if not session_id:
        print("[오류] 나이스 세션 연결 실패")
        ws.close()
        return False

    print(f"[연결] 세션 ID: {session_id}")

    # eXBuilder6 CPR 인스턴스 전체 탐색 스크립트
    js_extract = """
    (function(){
        if (typeof cpr === 'undefined' || !cpr.core || !cpr.core.Platform) {
            return { success: false, error: 'cpr_not_found' };
        }

        var platform = cpr.core.Platform.INSTANCE;
        var apps = platform.getAllRunningAppInstances();
        var result = {
            success: true,
            runningApps: apps.map(a => a.app ? a.app.id : 'unknown'),
            studentData: [],
            detectedDatasets: []
        };

        // 모든 실행 중인 앱 인스턴스에서 데이터셋 순회
        apps.forEach(function(inst) {
            if (!inst || typeof inst.getAllDataControls !== 'function') return;
            var controls = inst.getAllDataControls();
            controls.forEach(function(ds) {
                if (typeof ds.getRowCount !== 'function') return;
                var rowCount = ds.getRowCount();
                if (rowCount === 0) return;

                result.detectedDatasets.push({
                    appId: inst.app ? inst.app.id : '',
                    dsId: ds.id,
                    rowCount: rowCount
                });

                // 학생 정보가 포함된 데이터셋 탐색 (dsStdnt, dsMain, dsStudent 등)
                for (var r = 0; r < rowCount; r++) {
                    var rowData = ds.getRowData(r);
                    var keys = Object.keys(rowData);
                    
                    // 학생 이름, 생년월일, 보호자 관련 필드가 있는지 확인
                    var hasName = keys.some(k => k.toLowerCase().includes('nm') || k.toLowerCase().includes('name') || k === 'stdntNm' || k === 'stuFlnm');
                    var hasBrdt = keys.some(k => k.toLowerCase().includes('brdt') || k.toLowerCase().includes('birth') || k.toLowerCase().includes('rrno') || k.toLowerCase().includes('bth'));

                    if (hasName && hasBrdt) {
                        result.studentData.push({
                            appId: inst.app ? inst.app.id : '',
                            dsId: ds.id,
                            row: r,
                            data: rowData
                        });
                    }
                }
            });
        });

        return result;
    })()
    """

    msg_id += 1
    eval_res = cdp_send(ws, msg_id, "Runtime.evaluate", {
        "expression": js_extract,
        "returnByValue": True,
        "awaitPromise": True
    }, session_id=session_id)

    res_val = eval_res.get("result", {}).get("result", {}).get("value", {})
    ws.close()

    if not res_val or not res_val.get("success"):
        print(f"[경고] 나이스 CPR 엔진 탐색 실패: {res_val.get('error', 'unknown')}")
        return False

    running_apps = res_val.get("runningApps", [])
    detected_ds = res_val.get("detectedDatasets", [])
    student_data = res_val.get("studentData", [])

    print(f"\n[실행 중인 앱 목록] {len(running_apps)}개:")
    for app in running_apps[:10]:
        print(f"  - {app}")

    print(f"\n[감지된 데이터셋] {len(detected_ds)}개:")
    for ds in detected_ds:
        print(f"  - {ds['appId']} / {ds['dsId']} ({ds['rowCount']}행)")

    if not student_data:
        print("\n[안내] 학생 목록 데이터셋이 아직 조회되지 않았습니다.")
        print("▶ 나이스 화면에서 [학급담임]-[학적]-[기본신상관리] 또는 [학생명부]로 들어가서 [조회] 버튼을 1회 눌러주세요.")
        return False

    print(f"\n[추출 성공] 학생 관련 데이터 {len(student_data)}건 발견!")

    # 데이터 정제 및 CSV 저장
    # 필드 매핑 표준화
    extracted_rows = []
    for item in student_data:
        d = item["data"]
        # 번호
        num = d.get("stdntNo") or d.get("stuNo") or d.get("no") or d.get("num") or ""
        # 성명
        name = d.get("stdntNm") or d.get("stuFlnm") or d.get("korNm") or d.get("name") or ""
        # 생년월일
        brdt = d.get("brdt") or d.get("bthday") or d.get("birthDte") or d.get("rrno") or d.get("rrno1") or ""
        # 보호자 성명
        guardian = d.get("prntNm") or d.get("guardNm") or d.get("parntNm") or d.get("reprPrntNm") or ""
        # 보호자 관계
        relation = d.get("relNm") or d.get("guardRelNm") or d.get("prntRelNm") or ""
        # 비고/연락처
        contact = d.get("telNo") or d.get("mphonNo") or d.get("prntMphonNo") or ""

        extracted_rows.append({
            "번호": num,
            "성명": name,
            "생년월일": brdt,
            "보호자명": guardian,
            "관계": relation,
            "연락처": contact,
            "원천_데이터셋": item["dsId"]
        })

    # 중복 제거 (성명 + 번호 기준)
    unique_rows = []
    seen = set()
    for r in extracted_rows:
        key = (r["번호"], r["성명"])
        if key not in seen and r["성명"]:
            seen.add(key)
            unique_rows.append(r)

    # 번호순 정렬
    try:
        unique_rows.sort(key=lambda x: int(x["번호"]) if str(x["번호"]).isdigit() else 999)
    except Exception:
        pass

    # CSV 파일 저장 (UTF-8 with BOM for Excel compatibility)
    with open(OUTPUT_CSV, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["번호", "성명", "생년월일", "보호자명", "관계", "연락처", "원천_데이터셋"])
        writer.writeheader()
        writer.writerows(unique_rows)

    print("\n" + "=" * 60)
    print(f"  ✅ 3학년 2반 학생 명단 저장 완료!")
    print(f"  📁 저장 경로: {OUTPUT_CSV}")
    print(f"  👥 추출 인원: 총 {len(unique_rows)}명")
    print("=" * 60)
    return True

if __name__ == "__main__":
    extract_students()
