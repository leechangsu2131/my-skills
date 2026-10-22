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
    if (!sub) return {error: 'subSave not found'};
    
    var reqData = {};
    if (sub.getRequestDatas) {
        reqData = sub.getRequestDatas();
    }
    
    // Also check what datasets are bound to subSave
    // In cpr, sub.getRequestDataControls or similar
    var reqControls = [];
    if (sub.getRequestDataControls) {
        reqControls = sub.getRequestDataControls().map(function(dc){
            return {
                id: dc.id,
                type: dc.type,
                rows: dc.getRowDataRanged ? dc.getRowDataRanged() : (dc.getDatas ? dc.getDatas() : null)
            };
        });
    }
    
    return {
        reqControls: reqControls,
        reqData: reqData
    };
"""
res = driver.execute_script(js)
print(json.dumps(res, ensure_ascii=False, indent=2))
