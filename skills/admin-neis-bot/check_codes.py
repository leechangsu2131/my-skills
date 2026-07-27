#!/usr/bin/env python3
"""Check dsEvlCn codes for current standard and fill 박서우(미응시)."""
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

o = Options()
o.add_experimental_option("debuggerAddress", "localhost:9222")
d = webdriver.Chrome(options=o)
print(f"Connected: {d.title}")

# Step 1: Check evlCtrCd codes
codes = d.execute_script("""
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = null;
    for (var i = 0; i < instances.length; i++) {
        if (instances[i].app && instances[i].app.id === "edu/sw/els/scr/es/els_scres00_m00") {
            inst = instances[i];
            break;
        }
    }
    if (!inst) return {error: "App not found"};

    var evl = inst.lookup("dsEvlCn");
    if (!evl) return {error: "dsEvlCn not found"};

    var codes = [];
    for (var i = 0; i < evl.getRowCount(); i++) {
        codes.push({
            cd: evl.getValue(i, "evlCtrCd"),
            nm: evl.getValue(i, "evlCtrNm"),
            cn: (evl.getValue(i, "evlCtrCn") || "").slice(0, 80)
        });
    }
    return {codes: codes, count: evl.getRowCount()};
""")
print(f"\n[dsEvlCn] Available codes:")
print(json.dumps(codes, ensure_ascii=False, indent=2))

# Step 2: Check row 5 (박서우, index=5)
row5 = d.execute_script("""
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = null;
    for (var i = 0; i < instances.length; i++) {
        if (instances[i].app && instances[i].app.id === "edu/sw/els/scr/es/els_scres00_m00") {
            inst = instances[i];
            break;
        }
    }
    var ds = inst.lookup("dsMain");
    var row = {
        name: ds.getValue(5, "stuFlnm"),
        cd: ds.getValue(5, "evlCtrCd"),
        nm: ds.getValue(5, "evlCtrNm"),
        cn: ds.getValue(5, "evlCtrCn")
    };
    return row;
""")
print(f"\n[Row 5 - 박서우] Current state:")
print(json.dumps(row5, ensure_ascii=False, indent=2))
