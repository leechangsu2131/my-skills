#!/usr/bin/env python3
"""Find the actual CPR combo inside udcSwcAuth that controls subjects."""
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

o = Options()
o.add_experimental_option("debuggerAddress", "localhost:9222")
d = webdriver.Chrome(options=o)
print(f"Connected: {d.title}")

# The udcSbjt uses udcSwcAuth app instance. 
# There are multiple udcSwcAuth instances (indices 5-9 in the app list).
# Let's find the right one and look for its internal combo.
r = d.execute_script("""
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var result = [];
    
    for (var i = 0; i < instances.length; i++) {
        var ai = instances[i];
        if (ai.app && ai.app.id === "udc/sw/swc/udcSwcAuth") {
            // Check if this instance has dsAuth with subjects
            var dsAuth = ai.lookup("dsAuth");
            var info = {index: i, rowCount: 0, firstNm: ""};
            if (dsAuth && dsAuth.getRowCount) {
                info.rowCount = dsAuth.getRowCount();
                if (dsAuth.getRowCount() > 0) {
                    info.firstNm = dsAuth.getValue(0, "nm");
                }
            }
            
            // Find ALL controls
            var allData = ai.getAllDataControls();
            info.dataControlCount = allData.length;
            info.dataControls = allData.map(function(c) { return c.id || "no-id"; });
            
            // Look for a combo
            var container = ai.getContainer();
            if (container) {
                // Try to find UI controls by iterating children
                var uiControls = [];
                function findControls(ctrl) {
                    if (!ctrl) return;
                    var id = ctrl.id || "";
                    var type = ctrl.constructor ? ctrl.constructor.name : "?";
                    var hasItems = typeof ctrl.getItems === 'function';
                    var hasSIBV = typeof ctrl.selectItemByValue === 'function';
                    if (hasItems || hasSIBV) {
                        var itemCount = 0;
                        var sampleItems = [];
                        try {
                            var items = ctrl.getItems();
                            itemCount = items.length;
                            sampleItems = items.slice(0, 3).map(function(it) { return it.label || ""; });
                        } catch(e) {}
                        uiControls.push({id: id, type: type, hasItems: hasItems, hasSIBV: hasSIBV, 
                                         itemCount: itemCount, sampleItems: sampleItems});
                    }
                    // Check children
                    if (typeof ctrl.getChildren === 'function') {
                        try {
                            var ch = ctrl.getChildren();
                            for (var j = 0; j < ch.length; j++) findControls(ch[j]);
                        } catch(e) {}
                    }
                }
                findControls(container);
                info.uiControls = uiControls;
            }
            
            result.push(info);
        }
    }
    return result;
""")

print(json.dumps(r, ensure_ascii=False, indent=2))
