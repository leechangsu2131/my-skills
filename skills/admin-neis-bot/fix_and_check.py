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

# 1. Dismiss alert
js_dismiss = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    for (var i = 0; i < apps.length; i++) {
        var a = apps[i];
        if (a.app && a.app.id && a.app.id.indexOf('alert') !== -1) {
            var btn = a.lookup('btnConfirm') || a.lookup('btnOk');
            if (btn) {
                btn.click();
                return 'alert dismissed';
            }
        }
    }
    return 'no alert';
"""
print('Dismiss:', driver.execute_script(js_dismiss))

# 2. Check subSave details and event listeners
js_check = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) return {error: 'Popup not found'};
    
    // Turn off ddRpat
    var cbxDdRpatYn = popup.lookup('cbxDdRpatYn');
    if (cbxDdRpatYn) {
        cbxDdRpatYn.value = 'N';
        try {
            cbxDdRpatYn.dispatchEvent(new cpr.events.CValueChangeEvent('value-change', {oldValue: 'Y', newValue: 'N'}));
        } catch(e) {}
    }
    
    // Clear ddRpat inputs
    var ipbDd = popup.lookup('ipbDdRpatDd');
    if (ipbDd) ipbDd.value = '';
    var ipbHh = popup.lookup('ipbDdRpatHh');
    if (ipbHh) ipbHh.value = '';
    var ipbMm = popup.lookup('ipbDdRpatMm');
    if (ipbMm) ipbMm.value = '';
    
    // Update dsBsrp
    var dsBsrp = popup.lookup('dsBsrp');
    if (dsBsrp) {
        dsBsrp.setValue(0, 'ddRpatYn', 'N');
    }
    
    // Re-check grdTgpr and btnDdHr
    var grdTgpr = popup.lookup('grdTgpr');
    if (grdTgpr) {
        try { grdTgpr.setCheckRowIndex(0, true); } catch(e){}
    }
    var btnDdHr = popup.lookup('btnDdHr');
    if (btnDdHr) {
        try { btnDdHr.click(); } catch(e){}
    }
    
    return {
        cbxDdRpatYn: cbxDdRpatYn ? cbxDdRpatYn.value : null,
        bsrpRow: dsBsrp ? dsBsrp.getRowDataRanged()[0] : null,
        tgprRow: popup.lookup('dsTgpr') ? popup.lookup('dsTgpr').getRowDataRanged()[0] : null
    };
"""
res = driver.execute_script(js_check)
print('Updated state:')
print(json.dumps(res, ensure_ascii=False, indent=2))
