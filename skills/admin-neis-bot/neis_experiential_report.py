#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
나이스(NEIS) 교외체험학습보고서 접수/결재선 상신 자동화 스크립트
================================================================
교외체험학습보고서 결재라인: 교무(강동휘) 1명 단독 지정 (교감 제외)

사용법:
  python neis_experiential_report.py --dry-run
  python neis_experiential_report.py --apply --confirm APPLY_NEIS
"""

import argparse
import io
import json
import sys
import time
from pathlib import Path

# CP949 터미널 깨짐 방지
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REMOTE_PORT = 9222
TARGET_APP_ID = "edu/sa/eds/eaa/ae/eds_eaaae02_m01" # 보고서관리 메인 앱
DETAIL_POP_ID = "edu/sa/eds/eaa/ae/eds_eaaae02_p01" # 보고서 상세 팝업 앱

def attach(port=REMOTE_PORT):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{port}")
    driver = webdriver.Chrome(options=opts)
    print(f"[connect] {driver.title}")
    return driver

def find_neis_window(driver) -> str:
    for handle in driver.window_handles:
        try:
            driver.switch_to.window(handle)
            driver.switch_to.default_content()
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr and "vpn" not in driver.current_url.lower():
                print(f"[window] NEIS 창 확보: {driver.title}")
                return handle
        except:
            pass
    raise RuntimeError("NEIS가 실행 중인 창을 찾을 수 없습니다.")

def js_wrap(body: str) -> str:
    find = f'cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai){{ return ai.app && ai.app.id === "{TARGET_APP_ID}"; }})'
    return f'return (function(){{ var inst = {find}; if (!inst) return {{error: "app not found"}}; {body} }})();'

def dismiss_confirm_alert(driver, action_name=""):
    js = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var target = null;
    instances.forEach(function(ai) {
        if (!ai || !ai.app) return;
        var aid = ai.app.id || "";
        if (aid === "app/cmn/confirm" || aid === "app/cmn/alert") {
            target = ai;
        }
    });
    if (!target) return {found: false};
    
    var msg = "";
    var btn = null;
    target.getContainer().getAllRecursiveChildren().forEach(function(ctrl) {
        var val = ctrl.value || ctrl.text || "";
        if (ctrl.type === "output" || ctrl.type === "htmlsnippet") {
            msg += " | " + val;
        }
        if (val === "확인" || val === "예" || ctrl.id === "btnOk" || ctrl.id === "btnConfirm") {
            btn = ctrl;
        }
    });
    if (btn) {
        btn.click();
        var appId = (target.app && target.app.id) ? target.app.id : "unknown";
        return {found: true, appId: appId, msg: msg, clicked: btn.id || btn.value};
    }
    var appId2 = (target.app && target.app.id) ? target.app.id : "unknown";
    return {found: true, appId: appId2, msg: msg, error: "btn not found"};
    """
    res = driver.execute_script(js)
    if res.get("found"):
        print(f"  [modal-{action_name}] 팝업 발견({res.get('appId')}): {res.get('msg')} -> 클릭: {res.get('clicked')}")
        time.sleep(1.5)
        return True
    return False

def clean_popups(driver, duration_sec=4.0):
    end = time.time() + duration_sec
    while time.time() < end:
        dismissed = dismiss_confirm_alert(driver, "clean")
        time.sleep(0.5 if dismissed else 0.3)

def activate_tab(driver, tab_name):
    print(f"[tab] '{tab_name}' 메뉴 검색 및 활성화 시작...")
    
    # 1) 검색창에 텍스트 입력 및 search 이벤트 발생
    js_search = """
    var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "app/com/main/Index";
    });
    if (!inst) return {error: "Index app not found"};
    
    var searchInput = inst.lookup("siFindMenu");
    if (!searchInput) return {error: "siFindMenu not found"};
    
    searchInput.value = "TARGET_NAME";
    if (typeof searchInput.dispatchEvent === 'function') {
        var event = new cpr.events.CUIEvent("search");
        searchInput.dispatchEvent(event);
        return {ok: true};
    }
    return {error: "dispatchEvent not supported"};
    """.replace("TARGET_NAME", tab_name)
    
    res = driver.execute_script(js_search)
    if res.get("error"):
        print(f"  [tab-오류] 검색창 제어 실패: {res['error']}")
        return False
        
    time.sleep(2.0)
    
    # 2) 검색 결과 메뉴 클릭
    js_click = """
    var all = document.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
        var el = all[i];
        var text = (el.innerText || el.textContent || "").trim();
        if (text === "TARGET_NAME" && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "A")) {
            el.click();
            return {ok: true};
        }
    }
    return {error: "menu text TARGET_NAME not found"};
    """.replace("TARGET_NAME", tab_name)
    
    res_click = driver.execute_script(js_click)
    if res_click.get("error"):
        print(f"  [tab-오류] 메뉴 클릭 실패: {res_click['error']}")
        return False
        
    print(f"  [tab] '{tab_name}' 메뉴 전환 완료")
    time.sleep(3.0) # 탭 로딩 대기
    return True

# 1) 조회 및 스캔
def click_search(driver) -> bool:
    js = js_wrap('var btn = inst.lookup("btnSearch"); if(!btn) return {error:"btnSearch not found"}; btn.click(); return {ok:true};')
    res = driver.execute_script(js)
    if res.get("ok"):
        print("[search] 조회 클릭 성공. 2초 대기...")
        time.sleep(2.0)
        return True
    return False

def scan_dataset(driver) -> list:
    js = js_wrap("""
    var ds = inst.lookup("dsStdntListForRlt");
    if (!ds) return {error: "dsStdntListForRlt not found"};
    var key_cols = ["stuFlnm","clsNo","eduActPrcsStsNm","atrzStsNm","experLrnPeriod"];
    var rows = [];
    for (var r = 0; r < ds.getRowCount(); r++) {
        var row = {dsIndex: r};
        key_cols.forEach(function(c) { try { row[c] = ds.getValue(r, c); } catch(e) {} });
        rows.push(row);
    }
    return {rows: rows};
    """)
    res = driver.execute_script(js)
    if res.get("error"):
        print(f"[scan] 오류: {res['error']}")
        return []
    return res.get("rows", [])

# 2) 접수대기 상세 팝업 접수 처리
def click_student_name(driver, ds_index: int) -> bool:
    js = js_wrap("""
    var grid = inst.lookup("grdMain");
    var ds = inst.lookup("dsStdntListForRlt");
    if (!grid || !ds) return {error: "grid/ds not found"};
    
    var name = ds.getValue(INDEX_VAL, "stuFlnm");
    if (!name) return {error: "student name not found"};
    
    try {
        grid.selectRows([INDEX_VAL]);
        var gridEl = document.getElementById("uuid-" + grid.uuid);
        if (!gridEl) return {error: "grid DOM element not found"};
        
        var rowEl = gridEl.querySelector('[data-rowindex="INDEX_VAL"]');
        if (!rowEl) return {error: "row DOM not found"};
        
        var targetSpan = null;
        var candidates = rowEl.querySelectorAll('span, div, td, a');
        for (var i = 0; i < candidates.length; i++) {
            if (candidates[i].innerText.trim() === name) {
                targetSpan = candidates[i];
                break;
            }
        }
        if (!targetSpan) return {error: "span with text " + name + " not found"};
        
        targetSpan.click();
        return {ok: true, name: name};
    } catch(e) {
        return {error: e.message};
    }
    """).replace("INDEX_VAL", str(ds_index))
    res = driver.execute_script(js)
    if res.get("ok"):
        print("  -> 행 {i} ({name}) 클릭 성공".format(i=ds_index, name=res.get("name")))
        time.sleep(3.0)
        return True
    print("  -> 행 {i} 클릭 실패: {e}".format(i=ds_index, e=res.get("error")))
    return False

def process_detail_popup(driver, student_name: str) -> bool:
    # eds_eaaae02_p01 상세 팝업
    # 접수 버튼: btnUpdate, 닫기 버튼: btnCancel
    js_click = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var pop = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae02_p01";
    });
    if (!pop) return false;
    var btn = pop.lookup("TARGET_BTN");
    if (btn) {
        btn.click();
        return true;
    }
    return false;
    """
    
    print("  -> [접수] 클릭...")
    driver.execute_script(js_click.replace("TARGET_BTN", "btnUpdate"))
    time.sleep(1.5)
    clean_popups(driver, duration_sec=3.0)
    
    print("  -> [닫기] 클릭...")
    driver.execute_script(js_click.replace("TARGET_BTN", "btnCancel"))
    time.sleep(1.5)
    return True

# 3) 일괄 체크 및 승인요청
def check_rows_for_approval(driver, targets: list[dict]) -> int:
    js = js_wrap("""
    var grid = inst.lookup("grdMain");
    var ds = inst.lookup("dsStdntListForRlt");
    if (!grid || !ds) return {error: "grid/ds not found"};
    
    var gridEl = document.getElementById("uuid-" + grid.uuid);
    if (!gridEl) return {error: "grid DOM not found"};
    
    var checked = 0;
    // 모든 체크 해제
    for (var r = 0; r < ds.getRowCount(); r++) {
        ds.setValue(r, "chk", "0");
    }
    
    var targetIndices = TARGET_INDICES;
    targetIndices.forEach(function(r) {
        var rowEl = gridEl.querySelector('[data-rowindex="' + r + '"]');
        if (rowEl) {
            var chkBox = rowEl.querySelector('.cl-grid-checkbox, [role="checkbox"], input[type="checkbox"], .cl-checkbox');
            if (chkBox) {
                chkBox.click();
                checked++;
            }
        }
    });
    try { grid.redraw(); } catch(e) {}
    return {checked: checked};
    """.replace("TARGET_INDICES", str([t["dsIndex"] for t in targets])))
    
    res = driver.execute_script(js)
    if res.get("error"):
        print(f"[check] 오류: {res['error']}")
        return 0
    print(f"[check] '접수 + 미상신' {res.get('checked')}건 체크 완료")
    return res.get("checked", 0)

def click_approval_request(driver) -> bool:
    js = js_wrap('var btn = inst.lookup("btnUpdateCancel3"); if(!btn) return {error:"btnUpdateCancel3 not found"}; btn.click(); return {ok:true};')
    res = driver.execute_script(js)
    if res.get("ok"):
        print("[approval] 승인요청 버튼 클릭 성공. 3초 대기...")
        time.sleep(3.0)
        return True
    return False

# 4) 결재선 강동휘 단독 추가 및 상신
def handle_approval_popup(driver) -> bool:
    # 4-1) 컨펌 경고 수락
    dismiss_confirm_alert(driver, "승인요청컨펌")
    time.sleep(2.0)
    
    # 4-2) [결재자지정] 클릭
    print("  -> [결재자지정] 클릭...")
    js_click_select = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var drftApp = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p00";
    });
    if (!drftApp) return false;
    var btn = drftApp.lookup("btnSelectSancr");
    if (btn) { btn.click(); return true; }
    return false;
    """
    driver.execute_script(js_click_select)
    time.sleep(3.0)
    
    # 4-3) 교무(강동휘) 더블클릭 추가
    print("  -> 결재자 '강동휘' 더블클릭 추가...")
    js_add_sancr = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var pop = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04";
    });
    if (!pop) return {error: "p04 app not found"};
    
    var dsMain = pop.lookup("dsMain");
    var grdUserListFrom = pop.lookup("grdUserListFrom");
    var btnAdd = pop.lookup("btn1");
    if (!dsMain || !grdUserListFrom || !btnAdd) return {error: "ds/grid/btn not found"};
    
    var targetRow = -1;
    for (var i = 0; i < dsMain.getRowCount(); i++) {
        if (dsMain.getValue(i, "userNm") === "강동휘") {
            targetRow = i;
            break;
        }
    }
    if (targetRow === -1) return {error: "강동휘 not found in dsMain"};
    
    var gridEl = document.getElementById("uuid-" + grdUserListFrom.uuid);
    var rowEl = gridEl.querySelector('[data-rowindex="' + targetRow + '"]');
    var targetSpan = null;
    var candidates = rowEl.querySelectorAll('span, div, td, a');
    for (var i = 0; i < candidates.length; i++) {
        if (candidates[i].innerText.trim() === "강동휘") {
            targetSpan = candidates[i];
            break;
        }
    }
    if (!targetSpan) return {error: "span with text 강동휘 not found"};
    
    targetSpan.click();
    var dblEvent = new MouseEvent('dblclick', { bubbles: true, cancelable: true, view: window });
    targetSpan.dispatchEvent(dblEvent);
    
    grdUserListFrom.selectRows([targetRow]);
    btnAdd.click();
    return {ok: true};
    """
    res_add = driver.execute_script(js_add_sancr)
    if res_add.get("error"):
        print(f"    [오류] 결재자 추가 실패: {res_add['error']}")
        return False
    print("    '강동휘' 추가 완수")
    time.sleep(1.5)
    
    # 4-4) 결재선 저장 (btn4 클릭)
    print("  -> 결재선 저장...")
    js_save = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var pop = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04";
    });
    if (!pop) return false;
    var btnSave = pop.lookup("btn4");
    if (btnSave) { btnSave.click(); return true; }
    return false;
    """
    driver.execute_script(js_save)
    time.sleep(2.5)
    dismiss_confirm_alert(driver, "p04저장후")
    
    # 4-5) 최종 상신 클릭
    print("  -> 최종 [상신] 클릭...")
    js_drft = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var drftApp = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p00";
    });
    if (!drftApp) return false;
    var btnDrft = drftApp.lookup("btnDrft");
    if (btnDrft) { btnDrft.click(); return true; }
    return false;
    """
    driver.execute_script(js_drft)
    time.sleep(3.0)
    
    # 최종 모달들 순차 수락
    print("  -> 최종 모달창 일괄 수락...")
    for i in range(5):
        if dismiss_confirm_alert(driver, f"상신완료-{i+1}"):
            time.sleep(1.5)
        else:
            time.sleep(1.0)
            
    print("  -> [성공] 상신 최종 승인 완료")
    return True

# 메인 실행
def run(args):
    driver = attach(args.port)
    handle = find_neis_window(driver)
    driver.switch_to.window(handle)
    
    # 탭 활성화
    if not activate_tab(driver, "교외체험학습보고서관리"):
        print("[오류] '교외체험학습보고서관리' 탭을 활성화할 수 없습니다.")
        return
        
    if not click_search(driver):
        print("[오류] 조회를 실행하지 못했습니다.")
        return
        
    rows = scan_dataset(driver)
    print(f"전체 {len(rows)}건 조회됨:")
    for r in rows:
        print(f"  - {r.get('clsNo')}번 {r.get('stuFlnm')} | 처리상태: {r.get('eduActPrcsStsNm')} | 상신상태: {r.get('atrzStsNm')} | 기간: {r.get('experLrnPeriod')}")
        
    # 대상 분류
    daegi = [r for r in rows if r.get("eduActPrcsStsNm") == "접수대기"]
    misangsin = [r for r in rows if r.get("eduActPrcsStsNm") == "접수" and r.get("atrzStsNm") == "미상신"]
    
    print(f"\n* 접수대기 (접수 필요): {len(daegi)}건")
    for r in daegi:
        print(f"  -> {r.get('stuFlnm')}")
    print(f"* 접수+미상신 (상신 필요): {len(misangsin)}건")
    for r in misangsin:
        print(f"  -> {r.get('stuFlnm')}")
        
    if args.dry_run:
        print("\n(Dry-run) 실제 조작 없이 종료합니다.")
        return
        
    if not args.apply or args.confirm != "APPLY_NEIS":
        print("\n실반영하려면 --apply --confirm APPLY_NEIS 옵션이 필요합니다.")
        return
        
    # Step 3: 접수대기 건 접수 처리
    if daegi:
        print("\n=== [STEP 3] 접수대기 건 접수 처리 ===")
        for r in daegi:
            name = r.get("stuFlnm")
            idx = r.get("dsIndex")
            print(f"\n  --- {name} (행 {idx}) 처리 ---")
            if click_student_name(driver, idx):
                process_detail_popup(driver, name)
            else:
                print(f"  [오류] {name} 클릭 실패")
                
        # 재조회
        click_search(driver)
        time.sleep(2.0)
        rows = scan_dataset(driver)
        misangsin = [r for r in rows if r.get("eduActPrcsStsNm") == "접수" and r.get("atrzStsNm") == "미상신"]
        
    # Step 4: 결재선 상신
    if misangsin:
        print("\n=== [STEP 4] 일괄 승인요청 및 교무(강동휘) 결재선 상신 ===")
        checked = check_rows_for_approval(driver, misangsin)
        if checked > 0:
            if click_approval_request(driver):
                handle_approval_popup(driver)
    else:
        print("\n승인요청 및 상신할 건이 없습니다.")

def main():
    parser = argparse.ArgumentParser(description="교외체험학습보고서 자동 접수/상신")
    parser.add_argument("--port", type=int, default=REMOTE_PORT)
    parser.add_argument("--dry-run", action="store_true", help="조회만 수행")
    parser.add_argument("--apply", action="store_true", help="실반영 실행")
    parser.add_argument("--confirm", help="APPLY_NEIS 입력 필수")
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply:
        print("--dry-run 또는 --apply 를 지정하세요.")
        return
    run(args)

if __name__ == "__main__":
    main()
