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

js_test_simple = """
    var callback = arguments[arguments.length - 1];
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) { callback({error: 'Popup not found'}); return; }
    
    var sub = popup.lookup('subSave');
    var dsBsrp = popup.lookup('dsBsrp');
    var dsTgpr = popup.lookup('dsTgpr');
    
    // Simple text without special quotes
    var simplePurpose = '2026 AIEDAP 마스터교원 신규연수 참석 (화천초등학교-9604)';
    popup.lookup('ipbBsrpCn').value = simplePurpose;
    dsBsrp.setValue(0, 'bsrpCn', simplePurpose);
    
    // Format contact consistently
    popup.lookup('mse1').value = '01042330844';
    dsBsrp.setValue(0, 'emgCnctTelno', '01042330844');
    dsTgpr.setValue(0, 'emgCnctTelno', '01042330844');
    
    // Dates: 20261107 ~ 20261108
    popup.lookup('dti1').value = '20261107';
    popup.lookup('cmb10').value = '10';
    popup.lookup('cmb2').value = '30';
    popup.lookup('dti2').value = '20261108';
    popup.lookup('cmb3').value = '18';
    popup.lookup('cmb4').value = '00';
    
    dsBsrp.setValue(0, 'bgngYmd', '20261107');
    dsBsrp.setValue(0, 'bgngHh', '10');
    dsBsrp.setValue(0, 'bgngMm', '30');
    dsBsrp.setValue(0, 'bgngHm', '1030');
    dsBsrp.setValue(0, 'endYmd', '20261108');
    dsBsrp.setValue(0, 'endHh', '18');
    dsBsrp.setValue(0, 'endMm', '00');
    dsBsrp.setValue(0, 'endHm', '1800');
    
    dsTgpr.setValue(0, 'bgngYmd', '20261107');
    dsTgpr.setValue(0, 'bgngHh', '10');
    dsTgpr.setValue(0, 'bgngMm', '30');
    dsTgpr.setValue(0, 'bgngHm', '1030');
    dsTgpr.setValue(0, 'endYmd', '20261108');
    dsTgpr.setValue(0, 'endHh', '18');
    dsTgpr.setValue(0, 'endMm', '00');
    dsTgpr.setValue(0, 'endHm', '1800');
    
    // Ensure ddRpat is N
    dsBsrp.setValue(0, 'ddRpatYn', 'N');
    
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
    res = driver.execute_async_script(js_test_simple)
    print('Simple purpose test result:', res)
except Exception as e:
    print('Error:', e)
