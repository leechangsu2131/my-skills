#!/usr/bin/env python3
"""Inspect CPR combo box API for cmbRelm01."""
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

o = Options()
o.add_experimental_option("debuggerAddress", "localhost:9222")
d = webdriver.Chrome(options=o)
print(f"Connected: {d.title}")

# Get combo methods
r = d.execute_script("""
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = null;
    for (var i = 0; i < instances.length; i++) {
        if (instances[i].app && instances[i].app.id === "edu/sw/els/scr/es/els_scres00_m00") {
            inst = instances[i];
            break;
        }
    }
    if (!inst) return {error: "App not found"};

    var cmb = inst.lookup("cmbRelm01");
    if (!cmb) return {error: "cmbRelm01 not found"};

    var methods = [];
    for (var k in cmb) {
        if (typeof cmb[k] === 'function') {
            methods.push(k);
        }
    }

    // Also get properties
    var props = [];
    for (var k in cmb) {
        if (typeof cmb[k] !== 'function') {
            var val = cmb[k];
            var typeStr = typeof val;
            if (typeStr === 'object' && val !== null) {
                props.push({key: k, type: "object"});
            } else {
                props.push({key: k, type: typeStr, value: String(val).slice(0, 100)});
            }
        }
    }

    // Check specific method patterns
    var hasSetValue = typeof cmb.setValue === 'function';
    var hasSetSelection = typeof cmb.setSelection === 'function';
    var hasSetSelectedItem = typeof cmb.setSelectedItem === 'function';
    var hasSetText = typeof cmb.setText === 'function';
    var hasSelect = typeof cmb.select === 'function';
    var hasSetItemIndex = typeof cmb.setItemIndex === 'function';
    var hasSetSelectedIndex = typeof cmb.setSelectedIndex === 'function';
    var hasValue = typeof cmb.value;

    // Try to get current value
    var currentValue = null;
    try { currentValue = cmb.getValue ? cmb.getValue() : cmb.value; } catch(e) {}

    return {
        constructorName: cmb.constructor ? cmb.constructor.name : "unknown",
        methodCount: methods.length,
        methods: methods.sort(),
        propCount: props.length,
        hasSetValue: hasSetValue,
        hasSetSelection: hasSetSelection,
        hasSetSelectedItem: hasSetSelectedItem,
        hasSetText: hasSetText,
        hasSelect: hasSelect,
        hasSetItemIndex: hasSetItemIndex,
        hasSetSelectedIndex: hasSetSelectedIndex,
        valueType: hasValue,
        currentValue: currentValue
    };
""")

print(json.dumps(r, ensure_ascii=False, indent=2))
