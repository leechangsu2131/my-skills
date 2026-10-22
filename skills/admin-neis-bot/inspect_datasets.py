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
    
    var dm = target.getDataManager();
    var dataSets = dm ? dm.getAllDataControls() : [];
    var res = {};
    for (var i = 0; i < dataSets.length; i++) {
        var ds = dataSets[i];
        if (ds.getRowDataRanged) {
            res[ds.id] = ds.getRowDataRanged();
        }
    }
    return res;
"""
res = driver.execute_script(js)
print(json.dumps(res, ensure_ascii=False, indent=2))
