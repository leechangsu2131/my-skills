import io
import os
import sys
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os.environ['no_proxy'] = 'localhost,127.0.0.1'

opts = Options()
opts.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
driver = webdriver.Chrome(options=opts)

for h in driver.window_handles:
    driver.switch_to.window(h)
    if 'neis.go.kr' in driver.current_url:
        break

js = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var target = null;
    for (var i = 0; i < apps.length; i++) {
        if (apps[i].app && apps[i].app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_m00') {
            target = apps[i];
            break;
        }
    }
    if (!target) return {error: 'Target app not found'};
    
    // Check all data sets in target
    var dms = [];
    // In cpr, app has dataManager or lookup
    // let's inspect grdMain.getDataSet()
    var grd = target.lookup('grdMain');
    var ds = grd ? grd.getDataSet() : null;
    if (ds && ds.getRowDataRanged) {
        return {
            dsId: ds.id,
            rowCount: ds.getRowCount(),
            rows: ds.getRowDataRanged()
        };
    }
    return {msg: 'no ds'};
"""
res = driver.execute_script(js)
print(json.dumps(res, ensure_ascii=False, indent=2))
