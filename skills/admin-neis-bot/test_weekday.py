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

js_test_weekday = """
    var callback = arguments[arguments.length - 1];
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) { callback({error: 'Popup not found'}); return; }
    
    var sub = popup.lookup('subSave');
    var dsBsrp = popup.lookup('dsBsrp');
    var dsTgpr = popup.lookup('dsTgpr');
    
    // Change to weekday 1 day
    popup.lookup('dti1').value = '20261021';
    popup.lookup('cmb10').value = '14';
    popup.lookup('cmb2').value = '40';
    
    popup.lookup('dti2').value = '20261021';
    popup.lookup('cmb3').value = '16';
    popup.lookup('cmb4').value = '40';
    
    dsBsrp.setValue(0, 'bgngYmd', '20261021');
    dsBsrp.setValue(0, 'bgngHh', '14');
    dsBsrp.setValue(0, 'bgngMm', '40');
    dsBsrp.setValue(0, 'bgngHm', '1440');
    
    dsBsrp.setValue(0, 'endYmd', '20261021');
    dsBsrp.setValue(0, 'endHh', '16');
    dsBsrp.setValue(0, 'endMm', '40');
    dsBsrp.setValue(0, 'endHm', '1640');
    
    dsBsrp.setValue(0, 'allBsrpHrDdCnt', '0');
    dsBsrp.setValue(0, 'allBsrpHrHCnt', '2');
    dsBsrp.setValue(0, 'allBsrpHrMCnt', '0');
    
    // sync tgpr
    dsTgpr.setValue(0, 'bgngYmd', '20261021');
    dsTgpr.setValue(0, 'bgngHh', '14');
    dsTgpr.setValue(0, 'bgngMm', '40');
    dsTgpr.setValue(0, 'bgngHm', '1440');
    
    dsTgpr.setValue(0, 'endYmd', '20261021');
    dsTgpr.setValue(0, 'endHh', '16');
    dsTgpr.setValue(0, 'endMm', '40');
    dsTgpr.setValue(0, 'endHm', '1640');
    
    var listener = function(e) {
        sub.removeEventListener('submit-done', listener);
        callback({
            success: true,
            res: e.control.xhr ? e.control.xhr.responseText : null
        });
    };
    sub.addEventListener('submit-done', listener);
    sub.send();
"""

driver.set_script_timeout(10)
try:
    res = driver.execute_async_script(js_test_weekday)
    print('Weekday test result:', res)
except Exception as e:
    print('Error:', e)
