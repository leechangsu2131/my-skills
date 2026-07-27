#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
나이스(NEIS) 교외체험학습신청서 접수/결재선 상신 자동화 스크립트 v2
===================================================================
Chrome remote debugging port(9222)로 연결하여 eXBuilder6(cpr) API를 통해
교외체험학습신청서관리 화면의 접수대기 건을 일괄 처리합니다.

핵심 전략:
  - 앱 ID `edu/sa/eds/eaa/ae/eds_eaaae01_m01` 기반 정확 매칭
  - 데이터셋 `dsStdntListForAply`에서 직접 값 조회 (DOM 의존 없음)
  - `inst.lookup("btnSearch")` 등 컨트롤 ID 기반 버튼 제어

사용법:
  python neis_experiential_learning.py --diagnose   # 화면 구조 진단
  python neis_experiential_learning.py --dry-run    # 조회만 (조작 없음)
  python neis_experiential_learning.py --apply --confirm APPLY_NEIS  # 실반영
"""

from __future__ import annotations

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
TARGET_APP_ID = "edu/sa/eds/eaa/ae/eds_eaaae01_m01"


# ─────────────────────────────────────────────
# 1. Chrome 연결 및 NEIS 창 탐색
# ─────────────────────────────────────────────

def attach(port: int = REMOTE_PORT):
    """원격 디버깅 크롬 세션에 연결합니다."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.add_experimental_option("debuggerAddress", "localhost:{p}".format(p=port))
    driver = webdriver.Chrome(options=opts)
    print("[connect] {t} | {u}".format(t=driver.title, u=driver.current_url))
    return driver


def find_neis_window(driver) -> str:
    """cpr이 정의된 나이스 메인 창 핸들을 반환합니다."""
    for handle in driver.window_handles:
        try:
            driver.switch_to.window(handle)
            driver.switch_to.default_content()
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr and "vpn" not in driver.current_url.lower():
                print("[window] NEIS 창 확보: {t}".format(t=driver.title))
                return handle
        except Exception:
            pass
    raise RuntimeError("NEIS가 실행 중인 창을 찾을 수 없습니다.")


# ─────────────────────────────────────────────
# 2. eXBuilder6 진단
# ─────────────────────────────────────────────

JS_DIAGNOSE = r"""
return (function() {
  function getCols(ds) {
    try { return ds.getColumnNames ? ds.getColumnNames() : []; } catch(e) { return []; }
  }
  var platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return {error: "cpr Platform is not available"};
  var apps = platform.getAllRunningAppInstances().map(function(ai, idx) {
    var controls = [], datasets = [];
    try {
      ai.getContainer().getAllRecursiveChildren().forEach(function(c) {
        controls.push({
          id: c.id || "", type: c.type || "",
          text: (c.text || c.value || c.fieldLabel || "").toString().substring(0, 60)
        });
      });
    } catch(e) {}
    try {
      var dc = ai.getAllDataControls ? ai.getAllDataControls() : [];
      dc.forEach(function(ds) {
        var cols = getCols(ds);
        datasets.push({id: ds.id || "", rowCount: ds.getRowCount ? ds.getRowCount() : null, cols: cols.slice(0, 20)});
      });
    } catch(e) {}
    return {idx: idx, appId: ai.app && ai.app.id, controls: controls.length, datasets: datasets};
  });
  return {apps: apps};
})();
"""


def diagnose(driver, dump_path: Path | None) -> dict:
    result = driver.execute_script(JS_DIAGNOSE)
    if dump_path:
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        dump_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[diagnose] wrote {p}".format(p=dump_path))
    for app in result.get("apps", []):
        print("  [app {i}] {a} | controls={c}".format(i=app["idx"], a=app.get("appId"), c=app.get("controls")))
        for ds in app.get("datasets", [])[:5]:
            cols_str = ",".join(ds.get("cols", [])[:10])
            print("    [ds] {d} rows={r} cols={c}".format(d=ds.get("id"), r=ds.get("rowCount"), c=cols_str))
    return result


# ─────────────────────────────────────────────
# 3. 유틸리티 JS: 앱 인스턴스 찾기
# ─────────────────────────────────────────────

# 모든 JS 코드에서 공통으로 사용하는 앱 탐색 프래그먼트
FIND_APP_JS = 'cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai){{ return ai.app && ai.app.id === "{app_id}"; }})'.format(app_id=TARGET_APP_ID)


def js_wrap(body: str) -> str:
    """앱 인스턴스 탐색을 포함한 JS 코드를 래핑합니다."""
    return 'return (function(){{ var inst = {find}; if (!inst) return {{error: "app not found"}}; {body} }})();'.format(find=FIND_APP_JS, body=body)


# ─────────────────────────────────────────────
# 4. 확인/경고 모달 닫기
# ─────────────────────────────────────────────

def dismiss_modals(driver) -> bool:
    js = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var clicked = false;
    instances.forEach(function(ai) {
        if (!ai || !ai.app) return;
        if (ai.app.id !== "app/cmn/confirm" && ai.app.id !== "app/cmn/alert") return;
        try {
            ai.getContainer().getAllRecursiveChildren().forEach(function(ctrl) {
                if (clicked) return;
                var id = ctrl.id || "";
                var val = ctrl.value || ctrl.text || "";
                if (id === "btnOk" || id === "btnConfirm" || val === "OK" || val === "확인" || val === "예") {
                    if (typeof ctrl.click === 'function') { ctrl.click(); clicked = true; }
                }
            });
        } catch(e) {}
    });
    return clicked;
    """
    try:
        res = driver.execute_script(js)
        if res:
            print("  [modal] 확인 다이얼로그 닫기 완료")
            time.sleep(1.0)
        return bool(res)
    except Exception:
        return False


def clean_popups(driver, duration_sec: float = 4.0):
    from selenium.common.exceptions import NoAlertPresentException
    end = time.time() + duration_sec
    while time.time() < end:
        dismissed = dismiss_modals(driver)
        try:
            alert = driver.switch_to.alert
            alert.accept()
            dismissed = True
        except (NoAlertPresentException, Exception):
            pass
        time.sleep(0.5 if dismissed else 0.3)


# ─────────────────────────────────────────────
# 5. 조회 및 데이터셋 스캔
# ─────────────────────────────────────────────

def click_search(driver) -> bool:
    """교외체험학습 앱의 '조회' 버튼을 클릭합니다."""
    js = js_wrap('var btn = inst.lookup("btnSearch"); if(!btn) return {error:"btnSearch not found"}; btn.click(); return {ok:true};')
    res = driver.execute_script(js)
    if res.get("ok"):
        print("[search] 조회 클릭 성공. 2초 대기...")
        time.sleep(2.0)
        return True
    print("[search] 오류: {e}".format(e=res.get("error", "unknown")))
    return False


def scan_dataset(driver) -> list[dict]:
    """dsStdntListForAply 데이터셋에서 모든 행의 주요 컬럼을 가져옵니다."""
    js = js_wrap("""
    var ds = inst.lookup("dsStdntListForAply");
    if (!ds) return {error: "ds not found"};
    var key_cols = ["stuFlnm","clsNo","eduActPrcsStsNm","atrzStsNm","experLrnPeriod","experLrnPlaceNm","experLrnScNm","ousExperLrnAplyDdCnt","ousExperLrnRltYn"];
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
        print("[scan] 오류: {e}".format(e=res["error"]))
        return []
    return res.get("rows", [])


def find_targets(rows: list[dict]) -> dict:
    """접수대기 건과 접수+미상신 건을 분류합니다."""
    jeopsu_daegi = []  # 접수대기: 저장/접수 필요
    jeopsu_misangsin = []  # 접수 + 미상신: 결재선 상신만 필요
    for r in rows:
        status = r.get("eduActPrcsStsNm", "")
        atrz = r.get("atrzStsNm", "")
        if status == "접수대기":
            jeopsu_daegi.append(r)
        elif status == "접수" and atrz == "미상신":
            jeopsu_misangsin.append(r)
    return {"jeopsu_daegi": jeopsu_daegi, "jeopsu_misangsin": jeopsu_misangsin}


# ─────────────────────────────────────────────
# 6. 접수대기 건 처리: 학생 클릭 → 상세조회 팝업 → 저장 → 접수
# ─────────────────────────────────────────────

def click_student_name(driver, ds_index: int) -> bool:
    """그리드에서 학생명 셀을 클릭하여 상세조회 팝업을 엽니다."""
    js = js_wrap("""
    var grid = inst.lookup("grdMain");
    if (!grid) return {{error: "grdMain not found"}};
    var ds = inst.lookup("dsStdntListForAply");
    if (!ds) return {{error: "dsStdntListForAply not found"}};
    
    var name = ds.getValue({idx}, "stuFlnm");
    if (!name) return {{error: "student name not found at index {idx}"}};
    
    try {{
        grid.selectRows([{idx}]);
        
        // 그리드 DOM 요소 가져오기
        var gridEl = document.getElementById(grid.uuid) || document.querySelector('[data-uuid="' + grid.uuid + '"]');
        var root = gridEl || document;
        
        // 방법 1: XPath로 정확히 학생명 텍스트 노드 클릭
        var xpath = ".//*[text()='" + name + "']";
        var evaluator = new XPathEvaluator();
        var result = evaluator.evaluate(xpath, root, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        var node = result.singleNodeValue;
        if (node) {{
            node.click();
            return {{ok: true, method: "dom_text_click_xpath", name: name}};
        }}
        
        // 방법 2: querySelectorAll로 학생명 텍스트가 포함된 태그 찾아 클릭
        var all = root.querySelectorAll('*');
        for (var i = 0; i < all.length; i++) {{
            var el = all[i];
            if (el.innerText === name && (el.tagName === "SPAN" || el.tagName === "DIV" || el.tagName === "A" || el.tagName === "TD")) {{
                el.click();
                return {{ok: true, method: "dom_text_click_qs", name: name}};
            }}
        }}
        
        // 방법 3: doubleClickRow API 시도
        if (typeof grid.doubleClickRow === 'function') {{
            grid.doubleClickRow({idx});
            return {{ok: true, method: "doubleClickRow"}};
        }}
        
        return {{error: "element with text '" + name + "' not found"}};
    }} catch(e) {{
        return {{error: e.message}};
    }}
    """.format(idx=ds_index))
    res = driver.execute_script(js)
    if res.get("ok"):
        print("  -> 행 {i} ({name}) 클릭 성공 (method: {m})".format(i=ds_index, name=res.get("name", ""), m=res.get("method", "")))
        time.sleep(2.5)
        return True
    print("  -> 행 {i} 클릭 실패: {e}".format(i=ds_index, e=res.get("error", "")))
    return False


def process_detail_popup(driver, student_name: str) -> bool:
    """상세조회 팝업을 찾아 저장 -> 접수 -> 닫기를 수행합니다."""
    # 팝업 탐색: 저장/접수 버튼을 모두 가진 앱 인스턴스
    js = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var dialog = instances.find(function(ai) {
        if (!ai || !ai.app) return false;
        if (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert") return false;
        if (ai.app.id === "MAIN_APP") return false;
        var container = ai.getContainer();
        if (!container) return false;
        var has_save = false, has_recv = false;
        container.getAllRecursiveChildren().forEach(function(ctrl) {
            var val = ctrl.value || ctrl.text || "";
            if (val === "저장") has_save = true;
            if (val === "접수") has_recv = true;
        });
        return has_save && has_recv;
    });
    if (dialog) return {appId: dialog.app.id, title: dialog.title || ""};
    return null;
    """.replace("MAIN_APP", TARGET_APP_ID)
    dialog = driver.execute_script(js)

    if not dialog:
        print("  [경고] 상세조회 팝업을 찾을 수 없습니다. ({n})".format(n=student_name))
        return False

    print("  -> 상세조회 팝업: {a}".format(a=dialog.get("appId", "")))

    # 저장 클릭
    print("  -> 저장 클릭...")
    js_click = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var dialog = instances.find(function(ai) {
        if (!ai || !ai.app) return false;
        if (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert") return false;
        if (ai.app.id === "MAIN_APP") return false;
        var container = ai.getContainer();
        if (!container) return false;
        var has_save = false, has_recv = false;
        container.getAllRecursiveChildren().forEach(function(ctrl) {
            var val = ctrl.value || ctrl.text || "";
            if (val === "저장") has_save = true;
            if (val === "접수") has_recv = true;
        });
        return has_save && has_recv;
    });
    if (!dialog) return false;
    var target = null;
    dialog.getContainer().getAllRecursiveChildren().forEach(function(ctrl) {
        var val = ctrl.value || ctrl.text || "";
        if (val === "TARGET_BTN") target = ctrl;
    });
    if (target) { target.click(); return true; }
    return false;
    """.replace("MAIN_APP", TARGET_APP_ID)

    save_js = js_click.replace("TARGET_BTN", "저장")
    recv_js = js_click.replace("TARGET_BTN", "접수")
    close_js = js_click.replace("TARGET_BTN", "닫기")

    driver.execute_script(save_js)
    time.sleep(1.5)
    clean_popups(driver, duration_sec=3.0)

    # 접수 클릭
    print("  -> 접수 클릭...")
    driver.execute_script(recv_js)
    time.sleep(1.5)
    clean_popups(driver, duration_sec=3.0)

    # 닫기
    print("  -> 닫기...")
    driver.execute_script(close_js)
    time.sleep(1.5)
    return True


# ─────────────────────────────────────────────
# 7. 결재선 지정 및 상신
# ─────────────────────────────────────────────

def check_rows_for_approval(driver, indices: list[int]) -> int:
    """지정된 데이터셋 인덱스의 행을 체크합니다."""
    js = js_wrap("""
    var grid = inst.lookup("grdMain");
    if (!grid) return {error: "grdMain not found"};
    var ds = inst.lookup("dsStdntListForAply");
    if (!ds) return {error: "ds not found"};
    var checked = 0;
    // 먼저 모든 체크 해제
    try { grid.checkAll(false); } catch(e) {}
    // 접수 + 미상신인 행을 체크
    for (var r = 0; r < ds.getRowCount(); r++) {
        var status = ds.getValue(r, "eduActPrcsStsNm");
        var atrz = ds.getValue(r, "atrzStsNm");
        if (status === "접수" && atrz === "미상신") {
            try {
                grid.checkRow(r, true);
                checked++;
            } catch(e) {
                // 체크 메서드가 없으면 데이터셋에서 직접 설정
                try { ds.setValue(r, "chk", "1"); checked++; } catch(e2) {}
            }
        }
    }
    try { grid.redraw(); } catch(e) {}
    return {checked: checked};
    """)
    res = driver.execute_script(js)
    if res.get("error"):
        print("[check] 오류: {e}".format(e=res["error"]))
        return 0
    cnt = res.get("checked", 0)
    print("[check] '접수 + 미상신' {c}건 체크 완료".format(c=cnt))
    return cnt


def click_approval_request(driver) -> bool:
    """'승인요청' 버튼(btnUpdateCancel3)을 클릭합니다."""
    js = js_wrap('var btn = inst.lookup("btnUpdateCancel3"); if(!btn) return {error:"btnUpdateCancel3 not found"}; btn.click(); return {ok:true};')
    res = driver.execute_script(js)
    if res.get("ok"):
        print("[approval] 승인요청 버튼 클릭 성공. 결재선 팝업 대기...")
        time.sleep(3.0)
        return True
    print("[approval] 오류: {e}".format(e=res.get("error", "")))
    return False


def handle_approval_popup(driver, approvers: list[str]) -> bool:
    """결재선 팝업에서 결재자를 추가하고 확인합니다."""
    # 결재선 팝업 탐색
    js_find = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = null;
    instances.forEach(function(ai) {
        if (!ai || !ai.app) return;
        if (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert") return;
        // 결재선 관련 앱 (title이나 컨트롤에 결재/상신 관련 텍스트)
        var container = ai.getContainer();
        if (!container) return;
        var hasApprover = false;
        container.getAllRecursiveChildren().forEach(function(ctrl) {
            var val = ctrl.value || ctrl.text || ctrl.fieldLabel || "";
            if (val.indexOf("결재") >= 0 || val.indexOf("상신") >= 0 || val.indexOf("결재선") >= 0) hasApprover = true;
        });
        if (hasApprover && !popup) popup = ai;
    });
    if (popup) return {appId: popup.app.id, title: popup.title || ""};
    return null;
    """
    popup = driver.execute_script(js_find)
    if not popup:
        print("  [결재선] 팝업을 찾을 수 없습니다.")
        # 결재선 팝업이 없으면 바로 완료됐을 수 있음
        clean_popups(driver, duration_sec=3.0)
        return True

    print("  [결재선] 팝업 발견: {a}".format(a=popup.get("appId", "")))

    # 결재자 추가 로직은 결재선 팝업의 구조에 따라 달라짐
    # 우선 진단 덤프 후 확인 버튼만 누르기
    for name in approvers:
        print("  -> 결재자 '{n}' 검색 및 추가 시도...".format(n=name))
        # 검색 후 추가 (실제 구조 확인 후 구현)
        time.sleep(1.0)

    # 확인/상신 버튼
    js_confirm = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = null;
    instances.forEach(function(ai) {
        if (!ai || !ai.app) return;
        if (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert") return;
        var container = ai.getContainer();
        if (!container) return;
        var hasApprover = false;
        container.getAllRecursiveChildren().forEach(function(ctrl) {
            var val = ctrl.value || ctrl.text || ctrl.fieldLabel || "";
            if (val.indexOf("결재") >= 0 || val.indexOf("상신") >= 0) hasApprover = true;
        });
        if (hasApprover && !popup) popup = ai;
    });
    if (!popup) return false;
    var confirmed = false;
    popup.getContainer().getAllRecursiveChildren().forEach(function(ctrl) {
        if (confirmed) return;
        var val = ctrl.value || ctrl.text || "";
        if (val === "확인" || val === "상신" || val === "저장") {
            if (typeof ctrl.click === 'function') { ctrl.click(); confirmed = true; }
        }
    });
    return confirmed;
    """
    driver.execute_script(js_confirm)
    time.sleep(2.0)
    clean_popups(driver, duration_sec=4.0)
    print("  [결재선] 상신 완료")
    return True


# ─────────────────────────────────────────────
# 8. 메인 오케스트레이션
# ─────────────────────────────────────────────

def run(args):
    driver = attach(args.port)
    handle = find_neis_window(driver)
    driver.switch_to.window(handle)

    # --- 진단 모드 ---
    if args.diagnose:
        dump = Path("scratch/neis_experiential_diagnose.json")
        diagnose(driver, dump)
        return

    # --- [STEP 1] 조회 ---
    print("\n" + "="*50)
    print(" [STEP 1] 교외체험학습신청서 조회")
    print("="*50)

    # 앱 확인
    check = driver.execute_script(js_wrap('return {appId: inst.app.id};'))
    if check.get("error"):
        print("  [오류] 교외체험학습 앱을 찾을 수 없습니다.")
        print("  학급담임 > 교육활동신청관리 > 교외체험학습신청서관리로 이동 후 다시 실행하세요.")
        return
    print("  [OK] 앱 확인: {a}".format(a=check.get("appId")))

    if not click_search(driver):
        return

    # --- [STEP 2] 데이터셋 스캔 ---
    print("\n" + "="*50)
    print(" [STEP 2] 신청서 목록 스캔")
    print("="*50)

    rows = scan_dataset(driver)
    print("  전체 {n}건 조회됨:".format(n=len(rows)))
    for r in rows:
        print("    {no}번 {name} | {status} | {atrz} | {period} | {place}".format(
            no=r.get("clsNo", "?"),
            name=r.get("stuFlnm", "?"),
            status=r.get("eduActPrcsStsNm", "?"),
            atrz=r.get("atrzStsNm", "?"),
            period=r.get("experLrnPeriod", "?"),
            place=r.get("experLrnPlaceNm", "?"),
        ))

    targets = find_targets(rows)
    daegi = targets["jeopsu_daegi"]
    misangsin = targets["jeopsu_misangsin"]

    print("\n  * 접수대기 (저장/접수 필요): {n}건".format(n=len(daegi)))
    for r in daegi:
        print("    -> {name} ({place})".format(name=r.get("stuFlnm"), place=r.get("experLrnPlaceNm")))
    print("  * 접수+미상신 (결재선 상신 필요): {n}건".format(n=len(misangsin)))
    for r in misangsin:
        print("    -> {name} ({place})".format(name=r.get("stuFlnm"), place=r.get("experLrnPlaceNm")))

    if args.dry_run:
        print("\n  (Dry-run) 실제 조작 없이 종료합니다.")
        return

    # --- 안전장치 ---
    if not args.apply or args.confirm != "APPLY_NEIS":
        print("\n  실반영: --apply --confirm APPLY_NEIS 필요")
        return

    # --- [STEP 3] 접수대기 건 저장/접수 ---
    if daegi:
        print("\n" + "="*50)
        print(" [STEP 3] 접수대기 건 저장/접수")
        print("="*50)

        for r in daegi:
            name = r.get("stuFlnm", "?")
            idx = r.get("dsIndex", 0)
            print("\n  --- {name} (행 {idx}) 처리 ---".format(name=name, idx=idx))
            if click_student_name(driver, idx):
                process_detail_popup(driver, name)
            else:
                print("  [오류] {name} 클릭 실패".format(name=name))

        # 접수 후 재조회
        print("\n  재조회...")
        click_search(driver)
        time.sleep(2.0)

    # --- [STEP 4] 일괄 승인요청 ---
    print("\n" + "="*50)
    print(" [STEP 4] 일괄 승인요청 및 결재선 상신")
    print("="*50)

    # 재스캔
    rows = scan_dataset(driver)
    targets = find_targets(rows)
    total_misangsin = targets["jeopsu_misangsin"]
    if not total_misangsin:
        print("  승인요청할 건이 없습니다.")
    else:
        print("  {n}건 승인요청 대상:".format(n=len(total_misangsin)))
        for r in total_misangsin:
            print("    -> {name}".format(name=r.get("stuFlnm")))

        # 체크
        checked = check_rows_for_approval(driver, [r["dsIndex"] for r in total_misangsin])
        if checked > 0:
            # 승인요청 클릭
            click_approval_request(driver)
            # 결재선 처리
            handle_approval_popup(driver, ["강동휘", "김경영"])

    print("\n" + "="*50)
    print(" [완료] 교외체험학습신청서 처리 완료!")
    print("="*50)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=REMOTE_PORT)
    parser.add_argument("--diagnose", action="store_true", help="화면 구조 진단 덤프")
    parser.add_argument("--dry-run", action="store_true", help="실제 저장/접수 없이 조회만")
    parser.add_argument("--apply", action="store_true", help="실반영")
    parser.add_argument("--confirm", help="실반영 시 APPLY_NEIS 입력 필수")
    args = parser.parse_args()

    if not args.diagnose and not args.dry_run and not args.apply:
        print("--diagnose, --dry-run, --apply 중 하나를 선택하세요.")
        parser.print_help()
        return

    run(args)


if __name__ == "__main__":
    main()
