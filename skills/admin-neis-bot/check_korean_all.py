#!/usr/bin/env python3
"""Check all Korean realms (듣기·말하기, 읽기, 문학) to confirm completion."""
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

o = Options()
o.add_experimental_option("debuggerAddress", "localhost:9222")
d = webdriver.Chrome(options=o)
print(f"Connected: {d.title}")

FIND_APP = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = null;
    for (var i = 0; i < instances.length; i++) {
        if (instances[i].app && instances[i].app.id === "edu/sw/els/scr/es/els_scres00_m00") {
            inst = instances[i];
            break;
        }
    }
    if (!inst) return {error: "App not found"};
"""

# Get all realms
realms = d.execute_script(FIND_APP + """
    var cmb = inst.lookup("cmbRelm01");
    var items = cmb.getItems();
    var result = [];
    for (var j = 0; j < items.length; j++) {
        result.push({label: items[j].label, value: items[j].value});
    }
    return result;
""")
print(f"\nRealms: {json.dumps(realms, ensure_ascii=False)}")

# Check each realm
for realm in realms:
    print(f"\n{'='*50}")
    print(f"Checking realm: {realm['label']} (value={realm['value']})")
    print(f"{'='*50}")

    # Select realm
    d.execute_script(FIND_APP + f"""
        var cmb = inst.lookup("cmbRelm01");
        cmb.selectItemByValue("{realm['value']}");
        return true;
    """)
    time.sleep(2)

    # Get standards
    stds = d.execute_script(FIND_APP + """
        var cmb = inst.lookup("cmbSccesCtr");
        var items = cmb.getItems();
        var result = [];
        for (var j = 0; j < items.length; j++) {
            result.push({label: items[j].label, value: items[j].value});
        }
        return result;
    """)
    print(f"  Standards: {len(stds)}")
    for s in stds:
        print(f"    - {s['label']}")

    # For each standard, select it and search
    for std in stds:
        d.execute_script(FIND_APP + f"""
            var cmb = inst.lookup("cmbSccesCtr");
            cmb.selectItemByValue("{std['value']}");
            return true;
        """)
        time.sleep(0.5)

        d.execute_script(FIND_APP + """
            inst.lookup("btnSearch").click();
            return true;
        """)
        time.sleep(2)

        # Check dsMain
        state = d.execute_script(FIND_APP + """
            var ds = inst.lookup("dsMain");
            if (!ds) return {error: "dsMain not found"};
            var filled = 0;
            var empty = 0;
            var rows = [];
            for (var i = 0; i < ds.getRowCount(); i++) {
                var nm = ds.getValue(i, "evlCtrNm") || "";
                if (nm) filled++; else empty++;
                rows.push({
                    name: ds.getValue(i, "stuFlnm"),
                    nm: nm || "(빈칸)"
                });
            }
            return {
                modified: ds.isModified(),
                total: ds.getRowCount(),
                filled: filled,
                empty: empty,
                rows: rows
            };
        """)
        status = "✅ SAVED" if not state.get("modified") and state.get("filled", 0) > 0 else ("⚠️ EMPTY" if state.get("empty", 0) == state.get("total", 0) else "❓ PARTIAL")
        print(f"\n  [{std['label']}] {status}")
        print(f"    total={state.get('total')}, filled={state.get('filled')}, empty={state.get('empty')}, modified={state.get('modified')}")
        if state.get("empty", 0) > 0 and state.get("filled", 0) > 0:
            for r in state.get("rows", []):
                if r["nm"] == "(빈칸)":
                    print(f"    ⚠ 빈칸: {r['name']}")

print("\n\nDone.")
