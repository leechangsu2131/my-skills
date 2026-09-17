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
  if (!platform) return { error: "no platform" };
  var apps = platform.getAllRunningAppInstances();
  var targetApp = apps.find(function(a) { return a.app && a.app.id === "edu/ga/tps/hrd/mm/tps_hrdmm01_p14"; });
  if (!targetApp) return { error: "target app not found" };

  var dsMain = targetApp.lookup ? targetApp.lookup("dsMain") : null;
  var rowData = dsMain ? dsMain.getRowDataRanged() : [];

  var combos = {};
  ["cmbEduTypScCd", "cmbTraiScCd", "cmbEduStleCd", "cmbTraiCnClfCd", "cmbTchTraiEduInstCd"].forEach(function(cId) {
    var c = targetApp.lookup ? targetApp.lookup(cId) : null;
    if (c && c.getItems) {
      combos[cId] = c.getItems().map(function(item) { return { label: item.label, value: item.value }; });
    }
  });

  return { rowData: rowData, combos: combos };
})();
"""

res = driver.execute_script(JS)
with open("ds_main_output.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2, ensure_ascii=False)
print("Saved to ds_main_output.json successfully")
