#!/usr/bin/env python3
"""
NEIS 전체 과목 성취수준 자동 입력 스크립트.

배정표 JSON에서 각 과목/영역/성취기준별로:
1. 교과 선택 (udcSbjt)
2. 영역 선택 (cmbRelm01)  
3. 성취기준 선택 (cmbSccesCtr)
4. 조회 (btnSearch)
5. dsMain에 데이터 채우기
6. 저장 (btnSave) - 사용자 확인 후
7. 저장 확인 대화상자 처리
"""

import argparse
import json
import time
import sys
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

FIND_APP = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = null;
    for (var i = 0; i < instances.length; i++) {
        if (instances[i].app && instances[i].app.id === "edu/sw/els/scr/es/els_scres00_m00") {
            inst = instances[i];
            break;
        }
    }
    if (!inst) return {error: "App instance not found"};
"""

LEVEL_TO_CODE = {
    "매우잘함": "1 ",
    "잘함": "2 ",
    "노력요함": "3 ",
    "미응시": "99",
}


def dismiss_alerts(driver):
    """Dismiss any unexpected browser system alerts (like certificate prompts)."""
    from selenium.common.exceptions import NoAlertPresentException
    try:
        alert = driver.switch_to.alert
        text = alert.text
        print(f"  [alert] Dismissing browser system alert: '{text}'")
        alert.accept()
        time.sleep(1)
        # Recursively dismiss if there are multiple alerts
        dismiss_alerts(driver)
    except NoAlertPresentException:
        pass


def connect_cdp(port=9222):
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{port}")
    driver = webdriver.Chrome(options=opts)
    print(f"[connect] {driver.title}")
    
    # Dismiss any system alerts first
    dismiss_alerts(driver)
    
    # Try to dismiss any custom HTML confirmation dialogs left on the page
    try:
        driver.execute_script("""
            var btns = document.querySelectorAll('button, [role="button"]');
            for (var i = 0; i < btns.length; i++) {
                var text = (btns[i].innerText || "").trim();
                if (text === "확인" || text === "OK" || text === "예") {
                    btns[i].click();
                }
            }
        """)
        time.sleep(1)
    except Exception:
        pass
        
    return driver


def get_all_subjects(driver):
    """Get all available subjects from dsAuth."""
    dismiss_alerts(driver)
    return driver.execute_script(FIND_APP + """
        var udc = inst.lookup("udcSbjt");
        var embApp = udc.getEmbeddedAppInstance();
        var dsAuth = embApp.lookup("dsAuth");
        
        var subjects = [];
        for (var i = 0; i < dsAuth.getRowCount(); i++) {
            subjects.push({
                index: i,
                nm: dsAuth.getValue(i, "nm"),
                cd: dsAuth.getValue(i, "cd"),
                osuCd: dsAuth.getValue(i, "osuCd")
            });
        }
        return {current: udc.getText(), subjects: subjects};
    """)


def switch_subject(driver, osu_cd, expected_name):
    """Switch NEIS to a different subject using the internal cmbUdcAuth."""
    dismiss_alerts(driver)
    # Revert any unsaved changes in dsMain to prevent UI blocking
    driver.execute_script(FIND_APP + """
        var ds = inst.lookup("dsMain");
        if (ds && ds.isModified && ds.isModified()) {
            ds.revert();
        }
    """)
    
    result = driver.execute_script(FIND_APP + f"""
        var udc = inst.lookup("udcSbjt");
        var embApp = udc.getEmbeddedAppInstance();
        var cmb = embApp.lookup("cmbUdcAuth");
        if (!cmb) return {{error: "Internal cmbUdcAuth not found in udcSbjt"}};
        
        cmb.selectItemByValue("{osu_cd}", true); // Trigger change events
        return {{ok: true, selected: cmb.getSelectionFirst() ? cmb.getSelectionFirst().label : "none"}};
    """)
    
    if result.get("error"):
        print(f"  [switch] ERROR: {result['error']}")
        return False
    
    time.sleep(3)
    
    # Verify switch
    verify = driver.execute_script(FIND_APP + """
        var udc = inst.lookup("udcSbjt");
        return {text: udc.getText(), value: udc.getValue()};
    """)
    
    print(f"  [switch] Verified Subject: text='{verify.get('text')}' value='{verify.get('value')}'")
    if verify.get("text") != expected_name:
        print(f"  [switch] WARNING: Expected '{expected_name}', got '{verify.get('text')}'")
        return False
    return True


def get_realms(driver):
    """Get available realms for current subject."""
    return driver.execute_script(FIND_APP + """
        var cmb = inst.lookup("cmbRelm01");
        if (!cmb) return {error: "cmbRelm01 not found"};
        var items = cmb.getItems();
        return items.map(function(it) { return {label: it.label, value: it.value}; });
    """)


def select_realm(driver, value):
    """Select a realm by value."""
    dismiss_alerts(driver)
    driver.execute_script(FIND_APP + f"""
        var ds = inst.lookup("dsMain");
        if (ds && ds.isModified && ds.isModified()) {{
            ds.revert();
        }}
        var cmb = inst.lookup("cmbRelm01");
        cmb.selectItemByValue("{value}", true); // Trigger change events
        return true;
    """)
    time.sleep(2)


def get_standards(driver):
    """Get available standards for current realm."""
    return driver.execute_script(FIND_APP + """
        var cmb = inst.lookup("cmbSccesCtr");
        if (!cmb) return [];
        var items = cmb.getItems();
        return items.map(function(it) { return {label: it.label, value: it.value}; });
    """)


def select_standard_and_search(driver, value):
    """Select a standard and click search."""
    dismiss_alerts(driver)
    driver.execute_script(FIND_APP + f"""
        var ds = inst.lookup("dsMain");
        if (ds && ds.isModified && ds.isModified()) {{
            ds.revert();
        }}
        var cmb = inst.lookup("cmbSccesCtr");
        cmb.selectItemByValue("{value}", true); // Trigger change events
        return true;
    """)
    time.sleep(1.5) # Wait for standard binding
    
    driver.execute_script(FIND_APP + """
        inst.lookup("btnSearch").click();
        return true;
    """)
    time.sleep(3)


def get_grid_state(driver):
    """Get current dsMain grid state."""
    dismiss_alerts(driver)
    return driver.execute_script(FIND_APP + """
        var ds = inst.lookup("dsMain");
        if (!ds) return {error: "dsMain not found"};
        
        var rows = [];
        for (var i = 0; i < ds.getRowCount(); i++) {
            rows.push({
                i: i,
                name: ds.getValue(i, "stuFlnm"),
                cd: ds.getValue(i, "evlCtrCd"),
                nm: ds.getValue(i, "evlCtrNm"),
                sbjtNm: ds.getValue(i, "sbjtNm"),
                relmNm: ds.getValue(i, "relmNm")
            });
        }
        return {modified: ds.isModified(), total: ds.getRowCount(), rows: rows};
    """)


def fill_grid(driver, records):
    """Fill dsMain with records. Returns fill result."""
    level_map = {}
    for r in records:
        level_map[r["student"]] = r["level"]
    
    js_level_map = json.dumps(level_map, ensure_ascii=False)
    js_code_map = json.dumps(LEVEL_TO_CODE, ensure_ascii=False)
    
    return driver.execute_script(FIND_APP + f"""
        var levelMap = {js_level_map};
        var codeMap = {js_code_map};
        
        var ds = inst.lookup("dsMain");
        var evl = inst.lookup("dsEvlCn");
        var grid = inst.lookup("grdMain");
        
        if (!ds || !evl || !grid) return {{error: "Controls not found"}};
        
        var evlByCd = {{}};
        for (var i = 0; i < evl.getRowCount(); i++) {{
            var cd = evl.getValue(i, "evlCtrCd");
            evlByCd[String(cd).trim()] = {{
                nm: evl.getValue(i, "evlCtrNm"),
                cn: evl.getValue(i, "evlCtrCn")
            }};
        }}
        
        var filled = 0;
        var skipped = [];
        var unmatched = [];
        
        for (var i = 0; i < ds.getRowCount(); i++) {{
            var stuName = ds.getValue(i, "stuFlnm");
            var baseName = stuName.replace(/\\(.+\\)/, "").trim();
            
            if (!(baseName in levelMap)) {{
                unmatched.push(baseName);
                continue;
            }}
            
            var level = levelMap[baseName];
            var code = codeMap[level];
            
            if (!code) {{
                skipped.push({{name: baseName, level: level, reason: "unknown level"}});
                continue;
            }}
            
            // Skip 미응시 - leave blank
            if (level === "\ubbf8\uc751\uc2dc") {{
                skipped.push({{name: baseName, level: level, reason: "미응시 skip"}});
                continue;
            }}
            
            // Check if already filled with same value
            var currentCd = ds.getValue(i, "evlCtrCd");
            if (currentCd === code) {{
                continue;  // already correct
            }}
            
            var trimCode = code.trim();
            var evlInfo = evlByCd[trimCode];
            
            ds.setValue(i, "evlCtrCd", code);
            if (evlInfo) {{
                ds.setValue(i, "evlCtrNm", evlInfo.nm);
                ds.setValue(i, "evlCtrCn", evlInfo.cn);
            }}
            filled++;
        }}
        
        grid.redraw();
        
        return {{
            ok: true,
            filled: filled,
            skipped: skipped,
            unmatched: unmatched,
            modified: ds.isModified(),
            total: ds.getRowCount()
        }};
    """)


def save_grid(driver):
    """Click save and handle confirmation dialogs."""
    driver.execute_script(FIND_APP + """
        inst.lookup("btnSave").click();
        return true;
    """)
    time.sleep(3)
    
    # Dismiss any browser system alerts (like certificate prompts)
    dismiss_alerts(driver)
    
    # Click OK/확인 on the first confirmation dialog (app/cmn/confirm or app/cmn/alert) using framework API
    driver.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var confirmApp = instances.find(ai => ai.app && (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert"));
        if (confirmApp) {
            var container = confirmApp.getContainer();
            if (container) {
                var clicked = false;
                function findAndClick(ctrl) {
                    if (!ctrl || clicked) return;
                    var val = ctrl.value || ctrl.text || "";
                    var id = ctrl.id || "";
                    if (id === "btnOk" || id === "btnConfirm" || val === "확인" || val === "예" || val === "OK") {
                        if (typeof ctrl.click === 'function') {
                            ctrl.click();
                            clicked = true;
                        }
                    }
                    if (typeof ctrl.getChildren === 'function') {
                        var children = ctrl.getChildren();
                        for (var j = 0; j < children.length; j++) {
                            findAndClick(children[j]);
                        }
                    }
                }
                findAndClick(container);
            }
        }
    """)
    time.sleep(3)
    
    # Dismiss alerts again if any appeared after the confirm click
    dismiss_alerts(driver)
    
    # Click OK/확인 on any secondary dialog that might appear
    driver.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var confirmApp = instances.find(ai => ai.app && (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert"));
        if (confirmApp) {
            var container = confirmApp.getContainer();
            if (container) {
                var clicked = false;
                function findAndClick(ctrl) {
                    if (!ctrl || clicked) return;
                    var val = ctrl.value || ctrl.text || "";
                    var id = ctrl.id || "";
                    if (id === "btnOk" || id === "btnConfirm" || val === "확인" || val === "예" || val === "OK") {
                        if (typeof ctrl.click === 'function') {
                            ctrl.click();
                            clicked = true;
                        }
                    }
                    if (typeof ctrl.getChildren === 'function') {
                        var children = ctrl.getChildren();
                        for (var j = 0; j < children.length; j++) {
                            findAndClick(children[j]);
                        }
                    }
                }
                findAndClick(container);
            }
        }
    """)
    time.sleep(1)
    
    # Final alert cleanup
    dismiss_alerts(driver)


def verify_saved(driver):
    """Verify that data is saved (not modified)."""
    dismiss_alerts(driver)
    state = get_grid_state(driver)
    return not state.get("modified", True)


def match_standard(subject, std_label, records):
    """Match a NEIS standard label to records by standard_code or math unit mapping."""
    import re
    match = re.search(r'\[([^\]]+)\]', std_label)
    if not match:
        return []
    
    neis_code = match.group(1).strip()
    
    # Custom mapping for Art (미술) due to NEIS plan typo (Math code instead of Art code)
    if subject == "미술" and neis_code == "4수02-03":
        neis_code = "4미02-03"
    
    # Custom mapping for Mathematics
    if subject == "수학":
        target_assessment = None
        if neis_code in ("4수01-03", "4수01-04"):
            target_assessment = "4단원: 곱셈"
        elif neis_code in ("4수03-10", "4수03-14"):
            target_assessment = "5단원: 길이와 시간"
            
        if not target_assessment:
            return []
            
        return [r for r in records if r["subject"] == "수학" and r["assessment"] == target_assessment]
    
    # Match against records for other subjects
    matched = []
    for r in records:
        if r.get("subject") != subject:
            continue
        rec_code = r.get("standard_code", "")
        # Normalize: 4국05-04/05 -> try matching 4국05-04 or 4국05-05
        if "/" in rec_code:
            parts = rec_code.split("/")
            base = parts[0]  # e.g., "4국05-04"
            prefix = base.rsplit("-", 1)[0]  # e.g., "4국05"
            codes = [base] + [f"{prefix}-{p}" for p in parts[1:]]
        else:
            codes = [rec_code]
        
        if neis_code in codes or rec_code == neis_code:
            matched.append(r)
    
    return matched


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", default="scratch/neis-achievement-levels.json")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--subjects", nargs="*", help="Specific subjects to process (e.g., 도덕 수학)")
    parser.add_argument("--list-only", action="store_true", help="List subjects and exit")
    parser.add_argument("--no-save", action="store_true", help="Fill but don't save")
    args = parser.parse_args()
    
    all_records = json.loads(Path(args.records).read_text(encoding="utf-8"))
    print(f"[init] Loaded {len(all_records)} total records")
    
    driver = connect_cdp(args.port)
    
    # Get all subjects
    subj_info = get_all_subjects(driver)
    print(f"\n[subjects] Current: {subj_info['current']}")
    print(f"[subjects] Available: {len(subj_info['subjects'])}")
    for s in subj_info["subjects"]:
        print(f"  {s['index']}: {s['nm']} ({s['cd']})")
    
    if args.list_only:
        return
    
    # Build subject name -> osuCd mapping
    subject_map = {s["nm"]: s["cd"] for s in subj_info["subjects"]}
    
    # Determine which subjects to process
    target_subjects = args.subjects if args.subjects else ["도덕", "사회", "수학", "음악", "미술"]
    
    results_log = []
    
    for subject_name in target_subjects:
        osu_cd = subject_map.get(subject_name)
        if not osu_cd:
            # Try partial match
            for nm, cd in subject_map.items():
                if subject_name in nm or nm in subject_name:
                    osu_cd = cd
                    subject_name = nm
                    break
        
        if not osu_cd:
            print(f"\n{'='*60}")
            print(f"⚠ Subject '{subject_name}' not found in NEIS. Skipping.")
            print(f"{'='*60}")
            continue
        
        print(f"\n{'='*60}")
        print(f"📚 Processing: {subject_name}")
        print(f"{'='*60}")
        
        # Get records for this subject
        subj_records = [r for r in all_records if r["subject"] == subject_name]
        if not subj_records:
            print(f"  No records found for {subject_name}")
            continue
        print(f"  Records: {len(subj_records)}")
        
        # Switch subject
        if not switch_subject(driver, osu_cd, subject_name):
            print(f"  ❌ Failed to switch to {subject_name}")
            continue
        
        # Get realms
        realms = get_realms(driver)
        print(f"  Realms: {len(realms)}")
        for r in realms:
            print(f"    - {r['label']} (value={r['value']})")
        
        # Process each realm
        for realm in realms:
            print(f"\n  📂 Realm: {realm['label']}")
            select_realm(driver, realm["value"])
            
            standards = get_standards(driver)
            print(f"    Standards: {len(standards)}")
            
            for std in standards:
                print(f"\n    📋 Standard: {std['label']}")
                
                # Match records to this standard
                matched_records = match_standard(subject_name, std["label"], all_records)
                if not matched_records:
                    print(f"      No matching records. Skipping.")
                    continue
                print(f"      Matched records: {len(matched_records)}")
                
                # Select standard and search
                select_standard_and_search(driver, std["value"])
                
                # Check current state
                grid = get_grid_state(driver)
                if grid.get("error"):
                    print(f"      ❌ Grid error: {grid['error']}")
                    continue
                
                filled_count = sum(1 for r in grid["rows"] if r.get("nm"))
                empty_count = sum(1 for r in grid["rows"] if not r.get("nm"))
                print(f"      Grid: {grid['total']} students ({filled_count} filled, {empty_count} empty)")
                
                if filled_count == grid["total"]:
                    print(f"      ✅ Already fully filled. Skipping.")
                    results_log.append({
                        "subject": subject_name,
                        "realm": realm["label"],
                        "standard": std["label"],
                        "status": "already_filled",
                        "count": filled_count
                    })
                    continue
                
                # Fill data
                fill_result = fill_grid(driver, matched_records)
                if fill_result.get("error"):
                    print(f"      ❌ Fill error: {fill_result['error']}")
                    continue
                
                print(f"      Filled: {fill_result.get('filled', 0)} new entries")
                if fill_result.get("skipped"):
                    for s in fill_result["skipped"]:
                        print(f"      ⏭ Skipped: {s['name']} ({s['reason']})")
                if fill_result.get("unmatched"):
                    print(f"      ⚠ Unmatched NEIS students: {fill_result['unmatched']}")
                
                if fill_result.get("modified") and not args.no_save:
                    print(f"      💾 Saving...")
                    save_grid(driver)
                    
                    # Wait for server transaction to finalize
                    print(f"      Waiting 7 seconds for save finalization...")
                    time.sleep(7)
                    
                    # Verify directly on the current grid without re-searching
                    if verify_saved(driver):
                        print(f"      ✅ Saved successfully!")
                        results_log.append({
                            "subject": subject_name,
                            "realm": realm["label"],
                            "standard": std["label"],
                            "status": "saved",
                            "filled": fill_result.get("filled", 0)
                        })
                    else:
                        print(f"      ⚠ Save verification failed - may still be modified")
                        # Revert unsaved data as fallback to prevent blocking
                        driver.execute_script(FIND_APP + "var ds = inst.lookup('dsMain'); if(ds) ds.revert();")
                        results_log.append({
                            "subject": subject_name,
                            "realm": realm["label"],
                            "standard": std["label"],
                            "status": "save_unverified"
                        })
                elif not fill_result.get("modified"):
                    print(f"      ℹ No changes needed (data already correct)")
                    results_log.append({
                        "subject": subject_name,
                        "realm": realm["label"],
                        "standard": std["label"],
                        "status": "no_change"
                    })
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    for entry in results_log:
        status_icon = {"saved": "✅", "already_filled": "✅", "no_change": "ℹ️", "save_unverified": "⚠️"}.get(entry["status"], "❓")
        print(f"  {status_icon} {entry['subject']} / {entry['realm']} / {entry['standard']}: {entry['status']}")
    
    # Save log
    log_path = Path("scratch/neis-entry-log.json")
    log_path.write_text(json.dumps(results_log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nLog saved to {log_path}")


if __name__ == "__main__":
    main()
