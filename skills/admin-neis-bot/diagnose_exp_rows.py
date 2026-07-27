#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""4개 행 전체 데이터 확인."""

import io, sys, json
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)

for handle in driver.window_handles:
    driver.switch_to.window(handle)
    driver.switch_to.default_content()
    try:
        if driver.execute_script("return typeof cpr !== 'undefined';") and "vpn" not in driver.current_url.lower():
            break
    except: pass

result = driver.execute_script(r"""
var inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sa/eds/eaa/ae/eds_eaaae01_m01";
});
var ds = inst.lookup("dsStdntListForAply");
var cols = ds.getColumnNames();
var key_cols = ["stuFlnm","clsNo","eduActPrcsStsNm","atrzStsNm","experLrnPeriod","experLrnPlaceNm","experLrnScNm","ousExperLrnAplyDdCnt","ousExperLrnRltYn"];
var rows = [];
for (var r = 0; r < ds.getRowCount(); r++) {
    var row = {};
    key_cols.forEach(function(c) { row[c] = ds.getValue(r, c); });
    rows.push(row);
}
return rows;
""")

for r in result:
    print(json.dumps(r, ensure_ascii=False))
