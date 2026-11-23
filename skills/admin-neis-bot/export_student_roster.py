#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
나이스(NEIS) 학생 명렬표 다운로드 및 생년월일/보호자명 자동 추출 스크립트
====================================================================
기능:
1. Chrome 9222 포트를 통해 나이스 MDI 화면 제어
2. [명렬표출력] 화면에서 엑셀 다운로드 및 개인정보 사유 팝업(privateCmtPop) 자동 처리
3. [학부모서비스승인관리] 화면을 순회하여 학급 전원의 생년월일, 보호자 성명 및 연락처 추출 후 CSV 저장

사용법:
  python export_student_roster.py --reason "2027 학습지원 신청"
  python export_student_roster.py --grade 3 --class 2 --reason "학습지원 신청"
"""

import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.request
import websocket

# 터미널 인코딩 설정
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REMOTE_PORT = 9222
DOWNLOADS_DIR = os.path.join(os.path.expanduser("~"), "Downloads")

def get_neis_tab(port=REMOTE_PORT):
    resp = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json").read().decode("utf-8"))
    pinned_id = os.environ.get("NEIS_TAB")
    if pinned_id:
        tab = next((t for t in resp if t.get("id") == pinned_id), None)
        if tab:
            return tab
    # Multiple NEIS tabs safety: pick one with main.jsp
    tabs = [t for t in resp if t.get("type") == "page" and "neis.go.kr" in t.get("url", "")]
    if not tabs:
        raise RuntimeError("나이스 탭을 찾을 수 없습니다. 업무포털에서 나이스를 열어주세요.")
    # If more than one, prefer one that has running apps or return the latest
    return tabs[0]

def cdp_eval(ws, expression, return_by_value=True, await_promise=False):
    msg = {
        "id": int(time.time() * 1000) % 1000000,
        "method": "Runtime.evaluate",
        "params": {
            "expression": expression,
            "returnByValue": return_by_value,
            "awaitPromise": await_promise
        }
    }
    ws.send(json.dumps(msg))
    while True:
        raw = ws.recv()
        data = json.loads(raw)
        if data.get("id") == msg["id"]:
            if "error" in data:
                raise RuntimeError(f"CDP eval error: {data['error']}")
            return data.get("result", {}).get("result", {}).get("value")

def handle_privacy_popup(ws, reason_type="업무수행", reason_text="2027 학습지원 신청"):
    """개인정보 포함 파일 다운로드 사유 팝업(privateCmtPop) 처리"""
    js = f"""
    (() => {{
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var pop = instances.find(ai => ai.app && ai.app.id.includes("privateCmtPop"));
        if (!pop) return {{found: false}};
        
        var cmb = pop.lookup("cmbReason");
        if (cmb) {{
            cmb.value = "{reason_type}";
            try {{ cmb.dispatchEvent(new cpr.events.CUIEvent("value-change")); }} catch(e){{}}
        }}
        var txa = pop.lookup("txaReason");
        if (txa) {{
            txa.value = "{reason_text}";
            try {{ txa.dispatchEvent(new cpr.events.CUIEvent("value-change")); }} catch(e){{}}
        }}
        var btn = pop.lookup("btnConfirm");
        if (btn) {{
            btn.click();
            return {{found: true, submitted: true}};
        }}
        return {{found: true, submitted: false}};
    }})()
    """
    for _ in range(10):
        res = cdp_eval(ws, js)
        if res.get("submitted"):
            print(f"[다운로드 사유 입력] 사유구분: {reason_type}, 내용: {reason_text} 제출 완료")
            return True
        time.sleep(0.5)
    return False

def download_excel_roster(ws, download_dir=DOWNLOADS_DIR, reason_text="2027 학습지원 신청"):
    """명렬표출력 화면에서 엑셀 다운로드 실행"""
    print("[1] 명렬표 엑셀 다운로드 시작...")
    # CDP 다운로드 경로 허용
    ws.send(json.dumps({
        "id": 10,
        "method": "Page.setDownloadBehavior",
        "params": {"behavior": "allow", "downloadPath": download_dir}
    }))
    ws.recv()

    # 명렬표출력(AMELS40038) 열기
    cdp_eval(ws, """
    (() => {
        var idx = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes("Index"));
        return idx.callAppMethod("doOpenMenuToMdi", ["AMELS40038"]);
    })()
    """)
    time.sleep(3)

    # 조회 후 엑셀내려받기 클릭
    cdp_eval(ws, """
    (() => {
        var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes("els_srgbm02_m00"));
        if (app) {
            var btnSearch = app.lookup("btnSearch");
            if (btnSearch) btnSearch.click();
        }
    })()
    """)
    time.sleep(2)

    files_before = set(os.listdir(download_dir))
    cdp_eval(ws, """
    (() => {
        var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes("els_srgbm02_m00"));
        if (app) {
            var btn6 = app.lookup("btn6");
            if (btn6) btn6.click();
        }
    })()
    """)
    time.sleep(1)

    # 사유 팝업 처리
    handle_privacy_popup(ws, "업무수행", reason_text)
    
    # 다운로드 완료 대기
    print("  다운로드 완료 대기 중...")
    time.sleep(5)
    files_after = set(os.listdir(download_dir))
    new_files = files_after - files_before
    if new_files:
        print(f"  [성공] 다운로드된 파일: {new_files}")
    else:
        print("  [안내] 다운로드 완료 확인 (기존 파일 덮어쓰기 되었을 수 있음)")

def extract_birth_and_parents(ws, output_csv=None):
    """학부모서비스승인관리 화면에서 학생 생년월일 및 학부모명 일괄 추출"""
    print("\n[2] 학생 생년월일 및 보호자 정보 추출 시작...")
    # 학부모서비스승인관리(AMELS40004) 열기
    cdp_eval(ws, """
    (() => {
        var idx = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes("Index"));
        return idx.callAppMethod("doOpenMenuToMdi", ["AMELS40004"]);
    })()
    """)
    time.sleep(3)

    # 조회 클릭
    cdp_eval(ws, """
    (() => {
        var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes("els_sdlpa00_m00"));
        if (app) {
            var btn = app.lookup("btnSearch");
            if (btn) btn.click();
        }
    })()
    """)
    time.sleep(2)

    # 비동기 순회 수집 스크립트 주입
    js_loop = """
    (() => {
        window.__extract_done = false;
        window.__extract_data = [];
        
        (async () => {
            try {
                var app = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes("els_sdlpa00_m00"));
                if (!app) { window.__extract_done = true; return; }
                
                var grd = app.lookup("grdMain");
                var dsStu = app.lookup("dsStu");
                var dsSchpa = app.lookup("dsSchpaAprv");
                var total = dsStu.getRowCount();
                
                var list = [];
                for (var i = 0; i < total; i++) {
                    var s = dsStu.getRowData(i);
                    grd.selectRows([i]);
                    
                    // 서브미션 응답 대기 (최대 800ms)
                    for (var w = 0; w < 8; w++) {
                        await new Promise(r => setTimeout(r, 100));
                        if (dsSchpa.getRowCount() > 0 && dsSchpa.getRowData(0).stuDtcNo === s.stuDtcNo) break;
                    }
                    
                    var parents = [];
                    for (var p = 0; p < dsSchpa.getRowCount(); p++) {
                        var pData = dsSchpa.getRowData(p);
                        if (pData.stuDtcNo === s.stuDtcNo) {
                            parents.push({
                                name: pData.userNm,
                                tel: pData.mblTelno,
                                status: pData.aprvStsCdNm
                            });
                        }
                    }
                    list.push({
                        no: s.clsNo,
                        name: s.stuFlnm,
                        brdt: s.stuBrdt,
                        parents: parents
                    });
                }
                window.__extract_data = list;
                window.__extract_done = true;
            } catch(e) {
                window.__extract_err = e.toString();
                window.__extract_done = true;
            }
        })();
    })()
    """
    cdp_eval(ws, js_loop)
    print("  학생별 보호자 정보 수집 중...")
    
    # 완료 대기 (최대 30초)
    for _ in range(30):
        time.sleep(1)
        done = cdp_eval(ws, "Boolean(window.__extract_done)")
        if done:
            break

    data = cdp_eval(ws, "window.__extract_data") or []
    print(f"  [완료] 총 {len(data)}명 정보 수집 완료!")

    if not output_csv:
        output_csv = os.path.join(DOWNLOADS_DIR, "3학년2반_학생_생년월일_보호자명단.csv")

    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["번호", "학생성명", "생년월일", "보호자성명", "보호자연락처", "학부모서비스상태"])
        for s in data:
            parents = s.get("parents", [])
            if parents:
                for p in parents:
                    writer.writerow([s["no"], s["name"], s["brdt"], p["name"], p["tel"], p["status"]])
            else:
                writer.writerow([s["no"], s["name"], s["brdt"], "미등록", "", ""])

    print(f"  [저장 완료] CSV 파일: {output_csv}")

def main():
    parser = argparse.ArgumentParser(description="나이스 학생 명렬표 다운로드 및 생년월일/보호자명 추출 도구")
    parser.add_argument("--reason", default="2027 학습지원 신청", help="개인정보 다운로드 사유")
    parser.add_argument("--reason-type", default="업무수행", help="개인정보 다운로드 사유 분류 (기본: 업무수행)")
    parser.add_argument("--out", default=None, help="추출 CSV 저장 경로")
    parser.add_argument("--excel-only", action="store_true", help="명렬표 엑셀만 다운로드")
    parser.add_argument("--data-only", action="store_true", help="생년월일/보호자 CSV만 추출")
    args = parser.parse_args()

    tab = get_neis_tab()
    print(f"[연결] 나이스 탭: {tab.get('title')} ({tab.get('id')})")
    ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=15, suppress_origin=True)

    try:
        if not args.data_only:
            download_excel_roster(ws, reason_text=args.reason)
        if not args.excel_only:
            extract_birth_and_parents(ws, output_csv=args.out)
    finally:
        ws.close()

if __name__ == "__main__":
    main()
