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
    
    // In cpr, target has lookup
    // Find all datasets or datamaps in target
    var res = {};
    for (var k in target) {
        try {
            if (target[k] && target[k].getRowDataRanged) {
                res[k] = target[k].getRowDataRanged();
            }
        } catch(e) {}
    }
    
    // Also try target.lookup for common ds names
    var names = ['dsMain', 'ds_main', 'dsBsrpList', 'ds_bsrp_list', 'dsList', 'ds_list', 'dsGrd'];
    for (var n = 0; n < names.length; n++) {
        var d = target.lookup(names[n]);
        if (d && d.getRowDataRanged) {
            res[names[n]] = d.getRowDataRanged();
        }
    }
    
    // Also check grdMain bind
    var grd = target.lookup('grdMain');
    if (grd) {
        res.grdBind = grd.dataSet ? (grd.dataSet.id || 'has_dataset') : 'no_dataset';
        if (grd.dataSet && grd.dataSet.getRowDataRanged) {
            res.grdRows = grd.dataSet.getRowDataRanged();
        }
        if (grd.getBindDataSet && grd.getBindDataSet()) {
            res.bindDsId = grd.getBindDataSet().id;
            res.bindDsRows = grd.getBindDataSet().getRowDataRanged();
        }
    }
    return res;
"""
res = driver.execute_script(js)
print(json.dumps(res, ensure_ascii=False, indent=2))
