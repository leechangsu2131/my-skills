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

# Step 1: Click btnAply to open fresh popup
js_open = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var main = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_m00'; });
    if (!main) return {error: 'main not found'};
    var btn = main.lookup('btnAply');
    btn.click();
    return 'btnAply clicked';
"""
print('Open:', driver.execute_script(js_open))
time.sleep(3)

# Step 2: Fill popup with 2 rows for 관내출장 (11/7 and 11/8)
js_fill_two = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) return {error: 'popup not found'};
    
    var fullPurpose = '2026 AIEDAP 마스터교원 신규연수(초등 1차) 참석 화천초등학교-9604(2026. 9. 17.) 「[참석] 교육부 「2026 AIEDAP 마스터교원 신규연수 초등 1차」 대상자 선정 결과 및 연수 일정 안내」';
    var destination = '경상북도 경주시 더케이호텔 경주';
    var contact = '01042330844';
    var transport = '자가용';
    
    function setControl(id, val) {
        var c = popup.lookup(id);
        if (c) {
            c.value = val;
            try {
                c.dispatchEvent(new cpr.events.CValueChangeEvent('value-change', {oldValue: '', newValue: val}));
            } catch(e) {}
            if (c.redraw) c.redraw();
        }
    }
    
    // Period Row 0: 2026-11-07 11:00 ~ 18:00
    setControl('dti1', '20261107');
    setControl('cmb10', '11');
    setControl('cmb2', '00');
    setControl('dti2', '20261107');
    setControl('cmb3', '18');
    setControl('cmb4', '00');
    
    // Click btnAddPeriod for 2nd day (2026-11-08)
    var btnAdd = popup.lookup('btnAddPeriod');
    if (btnAdd) {
        btnAdd.click();
    }
    
    var dsBsrp = popup.lookup('dsBsrp');
    // Row 0 data
    dsBsrp.setValue(0, 'bgngYmd', '20261107');
    dsBsrp.setValue(0, 'bgngHh', '11');
    dsBsrp.setValue(0, 'bgngMm', '00');
    dsBsrp.setValue(0, 'bgngHm', '1100');
    dsBsrp.setValue(0, 'endYmd', '20261107');
    dsBsrp.setValue(0, 'endHh', '18');
    dsBsrp.setValue(0, 'endMm', '00');
    dsBsrp.setValue(0, 'endHm', '1800');
    dsBsrp.setValue(0, 'allBsrpHrDdCnt', '0');
    dsBsrp.setValue(0, 'allBsrpHrHCnt', '7');
    dsBsrp.setValue(0, 'allBsrpHrMCnt', '0');
    dsBsrp.setValue(0, 'bsrpScCd', '10');
    dsBsrp.setValue(0, 'bsrpScNm', '국내출장(관내)');
    dsBsrp.setValue(0, 'bsrpCn', fullPurpose);
    dsBsrp.setValue(0, 'dobtNm', destination);
    dsBsrp.setValue(0, 'mvmnMteCn', transport);
    dsBsrp.setValue(0, 'emgCnctTelno', contact);
    dsBsrp.setValue(0, 'tvctPyrfYn', 'N');
    dsBsrp.setValue(0, 'ddRpatYn', 'N');
    
    // Row 1 data (2026-11-08 09:00 ~ 18:00)
    if (dsBsrp.getRowCount() > 1) {
        dsBsrp.setValue(1, 'bgngYmd', '20261108');
        dsBsrp.setValue(1, 'bgngHh', '09');
        dsBsrp.setValue(1, 'bgngMm', '00');
        dsBsrp.setValue(1, 'bgngHm', '0900');
        dsBsrp.setValue(1, 'endYmd', '20261108');
        dsBsrp.setValue(1, 'endHh', '18');
        dsBsrp.setValue(1, 'endMm', '00');
        dsBsrp.setValue(1, 'endHm', '1800');
        dsBsrp.setValue(1, 'allBsrpHrDdCnt', '0');
        dsBsrp.setValue(1, 'allBsrpHrHCnt', '9');
        dsBsrp.setValue(1, 'allBsrpHrMCnt', '0');
        dsBsrp.setValue(1, 'bsrpScCd', '10');
        dsBsrp.setValue(1, 'bsrpScNm', '국내출장(관내)');
        dsBsrp.setValue(1, 'bsrpCn', fullPurpose);
        dsBsrp.setValue(1, 'dobtNm', destination);
        dsBsrp.setValue(1, 'mvmnMteCn', transport);
        dsBsrp.setValue(1, 'emgCnctTelno', contact);
        dsBsrp.setValue(1, 'tvctPyrfYn', 'N');
        dsBsrp.setValue(1, 'ddRpatYn', 'N');
    }
    
    // UI controls
    setControl('cmbBsrpScCd', '10');
    setControl('mse1', contact);
    setControl('ipbDobtNm', destination);
    setControl('ipbBsrpCn', fullPurpose);
    setControl('ipbMvmnMteCn', transport);
    
    // Redraw grid
    popup.lookup('grdMain').redraw();
    
    // Sync tgpr
    var grdTgpr = popup.lookup('grdTgpr');
    if (grdTgpr) grdTgpr.setCheckRowIndex(0, true);
    var btnDdHr = popup.lookup('btnDdHr');
    if (btnDdHr) btnDdHr.click();
    
    // Focus down
    popup.lookup('ipbBsrpCn').focus();
    
    return {
        success: true,
        periodCount: dsBsrp.getRowCount(),
        row0: {
            bgng: dsBsrp.getValue(0, 'bgngYmd') + ' ' + dsBsrp.getValue(0, 'bgngHm'),
            end: dsBsrp.getValue(0, 'endYmd') + ' ' + dsBsrp.getValue(0, 'endHm')
        },
        row1: dsBsrp.getRowCount() > 1 ? {
            bgng: dsBsrp.getValue(1, 'bgngYmd') + ' ' + dsBsrp.getValue(1, 'bgngHm'),
            end: dsBsrp.getValue(1, 'endYmd') + ' ' + dsBsrp.getValue(1, 'endHm')
        } : null,
        purpose: popup.lookup('ipbBsrpCn').value,
        destination: popup.lookup('ipbDobtNm').value
    };
"""

time.sleep(1)
fill_info = driver.execute_script(js_fill_two)
print('Fill info:')
print(json.dumps(fill_info, ensure_ascii=False, indent=2))

time.sleep(1)
driver.save_screenshot('C:/Users/user/.gemini/antigravity/brain/0c28257f-d0fa-4331-a07e-b804c459ee32/kwan_nae_perfect_screen.png')
print('Screenshot saved: kwan_nae_perfect_screen.png')
