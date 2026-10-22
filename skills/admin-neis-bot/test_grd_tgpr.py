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
    var popup = null;
    for (var i = 0; i < apps.length; i++) {
        if (apps[i].app && apps[i].app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00') {
            popup = apps[i];
            break;
        }
    }
    if (!popup) return {error: 'Popup not found'};
    
    var grdTgpr = popup.lookup('grdTgpr');
    var methods = [];
    for (var m in grdTgpr) {
        if (typeof grdTgpr[m] === 'function') methods.push(m);
    }
    
    // Check if checkRow or selectRows exist
    var relevant = methods.filter(function(m){
        return m.indexOf('select') !== -1 || m.indexOf('check') !== -1 || m.indexOf('Row') !== -1;
    });
    
    // Try to check first row or select first row
    try {
        if (grdTgpr.setCheckRowIndex) grdTgpr.setCheckRowIndex(0, true);
        else if (grdTgpr.selectRows) grdTgpr.selectRows([0]);
    } catch(e) {}
    
    // Check button click
    var btnDdHr = popup.lookup('btnDdHr');
    var clickRes = 'btn not clicked';
    if (btnDdHr) {
        btnDdHr.click();
        clickRes = 'btnDdHr clicked';
    }
    
    return {
        methods: relevant,
        clickRes: clickRes,
        dsTgpr: popup.lookup('dsTgpr').getRowDataRanged()
    };
"""
res = driver.execute_script(js)
print(json.dumps(res, ensure_ascii=False, indent=2))
