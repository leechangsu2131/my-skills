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
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) return {error: 'Popup not found'};
    
    var sub = popup.lookup('subSave');
    
    // Check requestData targets safely
    var reqTargets = [];
    if (sub.getRequestDataMap) {
        var map = sub.getRequestDataMap();
        for (var k in map) {
            reqTargets.push(k);
        }
    }
    
    // Check all data controls in popup and their row count and state
    var dcs = [];
    var names = ['dsBsrp', 'dsTgpr', 'dmSearch', 'dsBsrpTmpr', 'dsTgprTmpr', 'dsPeriod', 'dmParam'];
    for (var i = 0; i < names.length; i++) {
        var d = popup.lookup(names[i]);
        if (d) {
            dcs.push({
                name: names[i],
                type: d.type || (d.getRowDataRanged ? 'dataset' : 'datamap'),
                rowCount: d.getRowCount ? d.getRowCount() : null,
                rows: d.getRowDataRanged ? d.getRowDataRanged() : (d.getDatas ? d.getDatas() : null)
            });
        }
    }
    
    return {
        reqTargets: reqTargets,
        dataControls: dcs
    };
"""
res = driver.execute_script(js)
print(json.dumps(res, ensure_ascii=False, indent=2))
