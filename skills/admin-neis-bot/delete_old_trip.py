import io
import os
import sys
import time
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

# Step 1: Close popup if open
js_step1 = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (popup) {
        popup.close(false);
        return 'popup closed';
    }
    // Also dismiss any open alerts
    for (var i = 0; i < apps.length; i++) {
        var a = apps[i];
        if (a.app && a.app.id && a.app.id.indexOf('alert') !== -1) {
            var btn = a.lookup('btnConfirm') || a.lookup('btnOk');
            if (btn) btn.click();
        }
    }
    return 'no popup';
"""
print('Step 1:', driver.execute_script(js_step1))
time.sleep(1)

# Step 2: Check row 0 in main grid and click btnDelete
js_step2 = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var main = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_m00'; });
    if (!main) return {error: 'main not found'};
    
    var grd = main.lookup('grdMain');
    // Check first row (bsrpSn 572)
    grd.setCheckRowIndex(0, true);
    grd.selectRows([0]);
    
    var btnDelete = main.lookup('btnDelete');
    if (btnDelete) {
        btnDelete.click();
        return {status: 'btnDelete clicked'};
    }
    return {error: 'btnDelete not found'};
"""
print('Step 2:', driver.execute_script(js_step2))
time.sleep(2)

# Step 3: Confirm deletion modal if open
js_step3 = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var count = 0;
    for (var i = 0; i < apps.length; i++) {
        var a = apps[i];
        if (a.app && a.app.id && (a.app.id.indexOf('confirm') !== -1 || a.app.id.indexOf('alert') !== -1)) {
            var btn = a.lookup('btnConfirm') || a.lookup('btnOk') || a.lookup('btnYes');
            if (btn) {
                btn.click();
                count++;
            }
        }
    }
    return count + ' modals confirmed';
"""
print('Step 3:', driver.execute_script(js_step3))
time.sleep(2)

# Step 3-2: check again for second modal (e.g., '삭제되었습니다' alert)
print('Step 3-2:', driver.execute_script(js_step3))
time.sleep(1)

# Step 4: Verify remaining rows
js_step4 = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var main = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_m00'; });
    var ds = main.lookup('grdMain').dataSet;
    return ds ? ds.getRowDataRanged().map(function(r){
        return {sn: r.bsrpSn, sts: r.atrzStsNm, prd: r.bsrpPrd};
    }) : [];
"""
rows = driver.execute_script(js_step4)
print('Remaining rows in main after delete:')
print(json.dumps(rows, ensure_ascii=False, indent=2))

driver.save_screenshot('C:/Users/user/.gemini/antigravity/brain/0c28257f-d0fa-4331-a07e-b804c459ee32/after_delete_screen.png')
print('Screenshot saved!')
