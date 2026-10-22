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
        if (apps[i].app && apps[i].app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00') {
            target = apps[i];
            break;
        }
    }
    if (!target) return {error: 'Target app not found'};
    
    var res = {};
    // Look up common data components
    var names = ['dmBsrp', 'dm_bsrp', 'dsPeriod', 'ds_period', 'dsTgpr', 'ds_tgpr', 'dmParam', 'dsBsrp'];
    for (var n = 0; n < names.length; n++) {
        var d = target.lookup(names[n]);
        if (d) {
            if (d.getDatas) res[names[n]] = d.getDatas();
            else if (d.getRowDataRanged) res[names[n]] = d.getRowDataRanged();
            else res[names[n]] = 'found but unknown type';
        }
    }
    
    // Also check grdMain in popup
    var grd = target.lookup('grdMain');
    if (grd) {
        res.grdBind = grd.dataSet ? grd.dataSet.id : 'no_dataset';
        if (grd.dataSet && grd.dataSet.getRowDataRanged) {
            res.grdRows = grd.dataSet.getRowDataRanged();
        }
    }
    
    // Also check grdTgpr in popup
    var grdTgpr = target.lookup('grdTgpr');
    if (grdTgpr) {
        res.grdTgprBind = grdTgpr.dataSet ? grdTgpr.dataSet.id : 'no_dataset';
        if (grdTgpr.dataSet && grdTgpr.dataSet.getRowDataRanged) {
            res.grdTgprRows = grdTgpr.dataSet.getRowDataRanged();
        }
    }
    return res;
"""
res = driver.execute_script(js)
print(json.dumps(res, ensure_ascii=False, indent=2))
