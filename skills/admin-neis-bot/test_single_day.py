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

# Test with 2 rows via btnAddPeriod
js_test_periods = """
    var callback = arguments[arguments.length - 1];
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) { callback({error: 'Popup not found'}); return; }
    
    // Set common fields
    popup.lookup('cmbBsrpScCd').value = '10'; // 국내출장(관내)
    popup.lookup('mse1').value = '01042330844';
    popup.lookup('ipbDobtNm').value = '경상북도 경주시 더케이호텔 경주';
    popup.lookup('ipbBsrpCn').value = '2026 AIEDAP 마스터교원 신규연수(초등 1차) 참석 화천초등학교-9604(2026. 9. 17.) 「[참석] 교육부 「2026 AIEDAP 마스터교원 신규연수 초등 1차」 대상자 선정 결과 및 연수 일정 안내」';
    popup.lookup('ipbMvmnMteCn').value = '자가용';
    
    // Check if eduDisciYn helps
    // popup.lookup('cbxEduDisciYn').value = 'Y';
    
    // Let's test single row 11/07~11/07 first
    popup.lookup('dti1').value = '20261107';
    popup.lookup('cmb10').value = '11';
    popup.lookup('cmb2').value = '00';
    popup.lookup('dti2').value = '20261107';
    popup.lookup('cmb3').value = '18';
    popup.lookup('cmb4').value = '00';
    
    // sync tgpr
    var grdTgpr = popup.lookup('grdTgpr');
    if (grdTgpr) grdTgpr.setCheckRowIndex(0, true);
    var btnDdHr = popup.lookup('btnDdHr');
    if (btnDdHr) btnDdHr.click();
    
    // Dismiss any alert
    setTimeout(function() {
        var sub = popup.lookup('subSave');
        var listener = function(e) {
            sub.removeEventListener('submit-done', listener);
            callback({
                test: 'single_day_saturday',
                res: e.control.xhr ? e.control.xhr.responseText : null
            });
        };
        sub.addEventListener('submit-done', listener);
        sub.send();
    }, 500);
"""

driver.set_script_timeout(10)
try:
    res = driver.execute_async_script(js_test_periods)
    print('Single day test result:', res)
except Exception as e:
    print('Error:', e)
