#!/usr/bin/env python3
"""Check if dsMain is already modified / saved for current literature standard."""
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

o = Options()
o.add_experimental_option("debuggerAddress", "localhost:9222")
d = webdriver.Chrome(options=o)
print(f"Connected: {d.title}")

result = d.execute_script("""
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = null;
    for (var i = 0; i < instances.length; i++) {
        if (instances[i].app && instances[i].app.id === "edu/sw/els/scr/es/els_scres00_m00") {
            inst = instances[i];
            break;
        }
    }
    if (!inst) return {error: "App not found"};

    var ds = inst.lookup("dsMain");
    if (!ds) return {error: "dsMain not found"};

    var rows = [];
    for (var i = 0; i < ds.getRowCount(); i++) {
        var rowState = ds.getRowState ? ds.getRowState(i) : "unknown";
        rows.push({
            i: i,
            name: ds.getValue(i, "stuFlnm"),
            cd: ds.getValue(i, "evlCtrCd"),
            nm: ds.getValue(i, "evlCtrNm"),
            state: String(rowState)
        });
    }

    return {
        modified: ds.isModified(),
        rowCount: ds.getRowCount(),
        rows: rows
    };
""")

print(f"modified: {result.get('modified')}")
print(f"rows: {result.get('rowCount')}")
for row in result.get("rows", []):
    nm = row.get("nm", "") or "(빈칸)"
    state = row.get("state", "")
    print(f"  {row['i']+1}. {row['name']}: {nm} [state={state}]")
