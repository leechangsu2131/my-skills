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

# Test sending different payload variants via execute_script
js_test_payload = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) return {error: 'Popup not found'};
    
    var sub = popup.lookup('subSave');
    
    // Test a specific variation
    function trySaveWith(options) {
        return new Promise(function(resolve) {
            var dsBsrp = popup.lookup('dsBsrp');
            var dsTgpr = popup.lookup('dsTgpr');
            
            if (options.bsrpScCd) {
                popup.lookup('cmbBsrpScCd').value = options.bsrpScCd;
                dsBsrp.setValue(0, 'bsrpScCd', options.bsrpScCd);
                dsBsrp.setValue(0, 'bsrpScNm', options.bsrpScNm || '');
            }
            if (options.eduDisciYn !== undefined) {
                popup.lookup('cbxEduDisciYn').value = options.eduDisciYn;
                dsBsrp.setValue(0, 'eduDisciYn', options.eduDisciYn);
            }
            if (options.tvctPyrfYn !== undefined) {
                popup.lookup('cbxTvctPyrfYn').value = options.tvctPyrfYn;
                dsBsrp.setValue(0, 'tvctPyrfYn', options.tvctPyrfYn);
            }
            
            // set bsrpScNm
            var cmb = popup.lookup('cmbBsrpScCd');
            if (cmb && cmb.getItemByValue(cmb.value)) {
                dsBsrp.setValue(0, 'bsrpScNm', cmb.getItemByValue(cmb.value).label);
            }
            
            // Listener for this submission
            var listener = function(e) {
                sub.removeEventListener('submit-done', listener);
                sub.removeEventListener('submit-error', errListener);
                resolve({
                    success: true,
                    res: e.control.xhr ? e.control.xhr.responseText : null
                });
            };
            var errListener = function(e) {
                sub.removeEventListener('submit-done', listener);
                sub.removeEventListener('submit-error', errListener);
                resolve({
                    success: false,
                    err: e.control.xhr ? e.control.xhr.responseText : null
                });
            };
            
            sub.addEventListener('submit-done', listener);
            sub.addEventListener('submit-error', errListener);
            
            // Send submission directly
            sub.send();
        });
    }
    
    return window.__testRunner = trySaveWith;
"""
driver.execute_script(js_test_payload)

# Test 1: bsrpScCd = "40" (출장(연수)), eduDisciYn = "Y"
test_cases = [
    {"name": "연수+교육훈련Y", "bsrpScCd": "40", "bsrpScNm": "출장(연수)", "eduDisciYn": "Y", "tvctPyrfYn": "Y"},
    {"name": "관내+교육훈련Y", "bsrpScCd": "10", "bsrpScNm": "국내출장(관내)", "eduDisciYn": "Y", "tvctPyrfYn": "N"},
    {"name": "관외+교육훈련Y", "bsrpScCd": "20", "bsrpScNm": "국내출장(관외)", "eduDisciYn": "Y", "tvctPyrfYn": "N"},
    {"name": "연수만", "bsrpScCd": "40", "bsrpScNm": "출장(연수)", "eduDisciYn": "N", "tvctPyrfYn": "Y"},
]

for tc in test_cases:
    print(f"Testing {tc['name']}...")
    js_run = f"""
        return window.__testRunner({json.dumps(tc)});
    """
    driver.set_script_timeout(10)
    try:
        res = driver.execute_async_script(f"""
            var callback = arguments[arguments.length - 1];
            window.__testRunner({json.dumps(tc)}).then(callback);
        """)
        print('Result:', res)
        # Check if error message exists
        if res and 'res' in res and res['res']:
            res_obj = json.loads(res['res'])
            if res_obj.get('ErrorCode') != -1:
                print('>>> SUCCESS CASE FOUND! <<<')
                break
    except Exception as e:
        print('Error running test:', e)
    time.sleep(1)
