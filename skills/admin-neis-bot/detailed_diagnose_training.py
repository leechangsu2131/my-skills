#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

os.environ["no_proxy"] = "localhost,127.0.0.1"

opts = Options()
opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=opts)

JS = r"""
return (function() {
  var platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return {error: "cpr Platform is not available"};
  
  return platform.getAllRunningAppInstances().map(function(ai, idx) {
    var controls = [];
    try {
      var container = ai.getContainer ? ai.getContainer() : null;
      if (container && container.getAllRecursiveChildren) {
        container.getAllRecursiveChildren().forEach(function(c) {
          controls.push({
            id: c.id || "",
            type: c.type || "",
            value: (c.value || c.text || c.fieldLabel || "").toString().substring(0, 80)
          });
        });
      }
    } catch(e) {}
    
    var datasets = [];
    try {
      var dc = ai.getAllDataControls ? ai.getAllDataControls() : [];
      dc.forEach(function(ds) {
        var cols = ds.getColumnNames ? ds.getColumnNames() : [];
        datasets.push({
          id: ds.id || "",
          rowCount: ds.getRowCount ? ds.getRowCount() : null,
          cols: cols
        });
      });
    } catch(e) {}
    
    return {
      idx: idx,
      appId: (ai.app && ai.app.id) ? ai.app.id : "unknown",
      controlsCount: controls.length,
      controls: controls,
      datasets: datasets
    };
  });
})();
"""

res = driver.execute_script(JS)
with open("training_screen_dump.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2, ensure_ascii=False)

print(f"Dumped {len(res)} app instances to training_screen_dump.json")
for item in res:
    app_id = item.get("appId", "")
    ctrl_cnt = item.get("controlsCount", 0)
    print(f"App [{item['idx']}]: {app_id} (Controls: {ctrl_cnt})")
