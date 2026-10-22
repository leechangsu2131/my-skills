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

js_test_two_rows = """
    var callback = arguments[arguments.length - 1];
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) { callback({error: 'Popup not found'}); return; }
    
    // Check btnAddPeriod
    var btnAdd = popup.lookup('btnAddPeriod');
    if (btnAdd) {
        btnAdd.click();
    }
    
    var dsBsrp = popup.lookup('dsBsrp');
    var rowCount = dsBsrp ? dsBsrp.getRowCount() : 0;
    
    // Row 0: 2026-11-07 11:00 ~ 18:00
    dsBsrp.setValue(0, 'bgngYmd', '20261107');
    dsBsrp.setValue(0, 'bgngHh', '11');
    dsBsrp.setValue(0, 'bgngMm', '00');
    dsBsrp.setValue(0, 'bgngHm', '1100');
    dsBsrp.setValue(0, 'endYmd', '20261107');
    dsBsrp.setValue(0, 'endHh', '18');
    dsBsrp.setValue(0, 'endMm', '00');
    dsBsrp.setValue(0, 'endHm', '1800');
    dsBsrp.setValue(0, 'bsrpScCd', '10');
    dsBsrp.setValue(0, 'bsrpScNm', '국내출장(관내)');
    dsBsrp.setValue(0, 'allBsrpHrDdCnt', '0');
    dsBsrp.setValue(0, 'allBsrpHrHCnt', '7');
    dsBsrp.setValue(0, 'allBsrpHrMCnt', '0');
    
    // Row 1: 2026-11-08 09:00 ~ 18:00
    if (rowCount > 1) {
        dsBsrp.setValue(1, 'bgngYmd', '20261108');
        dsBsrp.setValue(1, 'bgngHh', '09');
        dsBsrp.setValue(1, 'bgngMm', '00');
        dsBsrp.setValue(1, 'bgngHm', '0900');
        dsBsrp.setValue(1, 'endYmd', '20261108');
        dsBsrp.setValue(1, 'endHh', '18');
        dsBsrp.setValue(1, 'endMm', '00');
        dsBsrp.setValue(1, 'endHm', '1800');
        dsBsrp.setValue(1, 'bsrpScCd', '10');
        dsBsrp.setValue(1, 'bsrpScNm', '국내출장(관내)');
        dsBsrp.setValue(1, 'allBsrpHrDdCnt', '0');
        dsBsrp.setValue(1, 'allBsrpHrHCnt', '9');
        dsBsrp.setValue(1, 'allBsrpHrMCnt', '0');
    }
    
    // Sync tgpr
    var grdTgpr = popup.lookup('grdTgpr');
    if (grdTgpr) grdTgpr.setCheckRowIndex(0, true);
    var btnDdHr = popup.lookup('btnDdHr');
    if (btnDdHr) btnDdHr.click();
    
    setTimeout(function() {
        var sub = popup.lookup('subSave');
        var listener = function(e) {
            sub.removeEventListener('submit-done', listener);
            callback({
                test: 'two_rows_period',
                rowCount: rowCount,
                res: e.control.xhr ? e.control.xhr.responseText : null
            });
        };
        sub.addEventListener('submit-done', listener);
        sub.send();
    }, 500);
"""

driver.set_script_timeout(10)
try:
    res = driver.execute_async_script(js_test_two_rows)
    print('Two rows test result:', res)
except Exception as e:
    print('Error:', e)
