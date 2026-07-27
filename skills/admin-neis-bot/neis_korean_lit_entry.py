#!/usr/bin/env python3
"""
NEIS 국어 문학영역 성취수준 입력 스크립트.

Phase 1: NEIS 화면에서 영역을 "문학"으로 전환 → 성취기준 선택 → 조회
Phase 2: dsMain에 값 채우기 → grdMain.redraw()
Phase verify: 채운 결과 확인
Phase save: btnSave 클릭 (사용자 승인 후에만)

사용법:
  python -X utf8 scratch/neis_korean_lit_entry.py --phase 1
  python -X utf8 scratch/neis_korean_lit_entry.py --phase 2
  python -X utf8 scratch/neis_korean_lit_entry.py --phase verify
  python -X utf8 scratch/neis_korean_lit_entry.py --phase save
"""

import argparse
import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def connect_cdp(port=9222):
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{port}")
    driver = webdriver.Chrome(options=opts)
    print(f"[connect] title: {driver.title}")
    return driver


def find_app(driver):
    """JS snippet to find the app instance."""
    return """
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


def phase1_switch_realm(driver):
    """Switch NEIS screen to 문학 realm, select standard, and search."""

    # Step 1: Select 문학 using selectItemByValue
    result = driver.execute_script(find_app(driver) + """
        var cmb = inst.lookup("cmbRelm01");
        if (!cmb) return {error: "cmbRelm01 not found"};

        // Use selectItemByValue to set to 문학 (value="5")
        cmb.selectItemByValue("5");

        // Verify by checking selected item label
        var sel = cmb.getSelectionFirst ? cmb.getSelectionFirst() : null;
        var selLabel = sel ? (sel.label || sel.toString()) : "unknown";

        return {ok: true, selectedLabel: String(selLabel), message: "Realm set to 문학(5)"};
    """)
    print(f"[phase1] Realm switch: {json.dumps(result, ensure_ascii=False, indent=2)}")

    if result.get("error"):
        return False

    # Wait for standards to reload
    time.sleep(3)

    # Step 2: Check available standards
    result2 = driver.execute_script(find_app(driver) + """
        var cmb = inst.lookup("cmbSccesCtr");
        if (!cmb) return {error: "cmbSccesCtr not found"};

        var items = cmb.getItems();
        var stdItems = [];
        for (var j = 0; j < items.length; j++) {
            stdItems.push({label: items[j].label, value: items[j].value});
        }
        return {standards: stdItems};
    """)
    print(f"[phase1] Standards: {json.dumps(result2, ensure_ascii=False, indent=2)}")

    if result2.get("error"):
        return False

    # Step 3: Select the right standard (4국05-04 or 4국05-05)
    result3 = driver.execute_script(find_app(driver) + """
        var cmb = inst.lookup("cmbSccesCtr");
        if (!cmb) return {error: "cmbSccesCtr not found"};

        var items = cmb.getItems();
        var targetValue = null;
        var targetLabel = "";
        for (var j = 0; j < items.length; j++) {
            var lbl = items[j].label || "";
            if (lbl.indexOf("4국05-04") >= 0 || lbl.indexOf("4국05-05") >= 0 ||
                lbl.indexOf("시") >= 0 || lbl.indexOf("낭송") >= 0) {
                targetValue = items[j].value;
                targetLabel = lbl;
                break;
            }
        }

        if (!targetValue && items.length === 1) {
            // Only one standard available - just use it
            targetValue = items[0].value;
            targetLabel = items[0].label;
        }

        if (!targetValue) return {error: "Standard not found", available: items.map(function(it){return it.label})};

        cmb.selectItemByValue(targetValue);
        return {ok: true, label: targetLabel, value: targetValue};
    """)
    print(f"[phase1] Standard selection: {json.dumps(result3, ensure_ascii=False, indent=2)}")

    if result3.get("error"):
        return False

    time.sleep(1)

    # Step 4: Click search button
    result4 = driver.execute_script(find_app(driver) + """
        var btn = inst.lookup("btnSearch");
        if (!btn) return {error: "btnSearch not found"};
        btn.click();
        return {ok: true, message: "Search clicked"};
    """)
    print(f"[phase1] Search: {json.dumps(result4, ensure_ascii=False, indent=2)}")

    time.sleep(3)

    # Step 5: Verify grid loaded
    result5 = driver.execute_script(find_app(driver) + """
        var ds = inst.lookup("dsMain");
        if (!ds) return {error: "dsMain not found"};

        var rows = [];
        for (var i = 0; i < ds.getRowCount(); i++) {
            rows.push({
                i: i,
                name: ds.getValue(i, "stuFlnm"),
                clsNo: ds.getValue(i, "clsNo"),
                cd: ds.getValue(i, "evlCtrCd"),
                nm: ds.getValue(i, "evlCtrNm")
            });
        }
        return {rowCount: ds.getRowCount(), rows: rows};
    """)
    print(f"\n[phase1] Grid: {result5.get('rowCount', 0)} students")
    if result5.get("rows"):
        for row in result5["rows"]:
            current = row.get("nm", "") or "(빈칸)"
            print(f"  {row['clsNo']}번 {row['name']}: {current}")

    return True


def phase2_fill_data(driver, records_path):
    """Fill dsMain with achievement levels from records JSON."""

    records = json.loads(Path(records_path).read_text(encoding="utf-8"))
    print(f"[phase2] Loaded {len(records)} records")

    # Build mapping: student name -> level
    level_map = {}
    for r in records:
        level_map[r["student"]] = r["level"]

    LEVEL_TO_CODE = {
        "매우잘함": "1 ",
        "잘함": "2 ",
        "노력요함": "3 ",
        "미응시": "99",
    }

    print("\n[phase2] Data to fill:")
    for name, level in level_map.items():
        code = LEVEL_TO_CODE.get(level, "??")
        print(f"  {name}: {level} (code={code.strip()})")

    js_level_map = json.dumps(level_map, ensure_ascii=False)
    js_code_map = json.dumps(LEVEL_TO_CODE, ensure_ascii=False)

    result = driver.execute_script(find_app(driver) + f"""
        var levelMap = {js_level_map};
        var codeMap = {js_code_map};

        var ds = inst.lookup("dsMain");
        var evl = inst.lookup("dsEvlCn");
        var grid = inst.lookup("grdMain");

        if (!ds || !evl || !grid) return {{error: "Controls not found (ds/evl/grid)"}};

        // Build evlCtrCd -> evlCtrNm/evlCtrCn map
        var evlByCd = {{}};
        for (var i = 0; i < evl.getRowCount(); i++) {{
            var cd = evl.getValue(i, "evlCtrCd");
            evlByCd[String(cd).trim()] = {{
                nm: evl.getValue(i, "evlCtrNm"),
                cn: evl.getValue(i, "evlCtrCn")
            }};
        }}

        var filled = [];
        var unmatched = [];

        for (var i = 0; i < ds.getRowCount(); i++) {{
            var stuName = ds.getValue(i, "stuFlnm");
            var baseName = stuName.replace(/\\(.+\\)/, "").trim();

            if (!(baseName in levelMap)) {{
                unmatched.push({{i: i, name: stuName, baseName: baseName}});
                continue;
            }}

            var level = levelMap[baseName];
            var code = codeMap[level];
            if (!code) {{
                unmatched.push({{i: i, name: stuName, level: level, reason: "unknown level"}});
                continue;
            }}

            var trimCode = code.trim();
            var evlInfo = evlByCd[trimCode];

            ds.setValue(i, "evlCtrCd", code);
            if (evlInfo) {{
                ds.setValue(i, "evlCtrNm", evlInfo.nm);
                ds.setValue(i, "evlCtrCn", evlInfo.cn);
            }} else {{
                // 미응시(99) might map to 임의입력
                var info99 = evlByCd["99"];
                if (info99) {{
                    ds.setValue(i, "evlCtrNm", info99.nm);
                    ds.setValue(i, "evlCtrCn", info99.cn || "");
                }} else {{
                    ds.setValue(i, "evlCtrNm", level);
                }}
            }}

            filled.push({{
                i: i,
                name: stuName,
                level: level,
                cd: code,
                nm: evlInfo ? evlInfo.nm : (evlByCd["99"] ? evlByCd["99"].nm : level)
            }});
        }}

        grid.redraw();

        return {{
            ok: true,
            filled: filled.length,
            unmatched: unmatched,
            modified: ds.isModified(),
            total: ds.getRowCount(),
            filledDetails: filled,
            evlCodes: evlByCd
        }};
    """)

    print(f"\n[phase2] Result:")
    print(f"  filled: {result.get('filled', 0)}/{result.get('total', 0)}")
    print(f"  unmatched: {result.get('unmatched', [])}")
    print(f"  modified: {result.get('modified', False)}")

    if result.get("filledDetails"):
        print("\n  Details:")
        for d in result["filledDetails"]:
            print(f"    {d['i']+1}. {d['name']}: {d['level']} -> {d['nm']}")

    return result


def phase_verify(driver, out_path=None):
    """Verify current dsMain values."""

    result = driver.execute_script(find_app(driver) + """
        var ds = inst.lookup("dsMain");
        if (!ds) return {error: "dsMain not found"};

        var rows = [];
        for (var i = 0; i < ds.getRowCount(); i++) {
            rows.push({
                i: i,
                name: ds.getValue(i, "stuFlnm"),
                cd: ds.getValue(i, "evlCtrCd"),
                nm: ds.getValue(i, "evlCtrNm"),
                cn: (ds.getValue(i, "evlCtrCn") || "").slice(0, 60)
            });
        }

        return {
            ok: true,
            modified: ds.isModified(),
            rows: rows
        };
    """)

    if result.get("error"):
        print(f"[verify] ERROR: {result['error']}")
        return result

    print(f"[verify] modified: {result['modified']}")
    print(f"[verify] {len(result['rows'])} students:")
    for row in result["rows"]:
        nm = row.get("nm", "") or "(빈칸)"
        print(f"  {row['i']+1}. {row['name']}: {nm}")

    if out_path:
        Path(out_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[verify] Saved to {out_path}")

    return result


def phase_save(driver):
    """Click btnSave to save."""

    result = driver.execute_script(find_app(driver) + """
        var btn = inst.lookup("btnSave");
        if (!btn) return {error: "btnSave not found"};
        btn.click();
        return {ok: true, message: "Save button clicked"};
    """)
    print(f"[save] {json.dumps(result, ensure_ascii=False, indent=2)}")

    time.sleep(3)

    # Check for confirmation dialog
    dialogs = driver.execute_script("""
        var result = [];
        var dialogs = document.querySelectorAll('[role="dialog"], [role="alertdialog"], .cpr-dialog, .cpr-msgbox');
        for (var i = 0; i < dialogs.length; i++) {
            var d = dialogs[i];
            result.push({
                tag: d.tagName,
                text: (d.innerText || "").slice(0, 200),
                visible: d.offsetParent !== null
            });
        }
        return result;
    """)
    print(f"[save] Dialogs: {json.dumps(dialogs, ensure_ascii=False, indent=2)}")

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, help="1, 2, verify, save")
    parser.add_argument("--records", default="scratch/neis-achievement-levels-korean-4guk0504.json")
    parser.add_argument("--port", type=int, default=9222)
    args = parser.parse_args()

    driver = connect_cdp(args.port)

    if args.phase == "1":
        phase1_switch_realm(driver)
    elif args.phase == "2":
        phase2_fill_data(driver, args.records)
    elif args.phase == "verify":
        phase_verify(driver, "scratch/after-fill-korean-4guk0504.json")
    elif args.phase == "save":
        phase_save(driver)
    else:
        print(f"Unknown phase: {args.phase}")


if __name__ == "__main__":
    main()
