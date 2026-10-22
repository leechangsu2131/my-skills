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

js_force_fill = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) return {error: 'no popup'};
    
    var fullPurpose = '2026 AIEDAP 마스터교원 신규연수(초등 1차) 참석 화천초등학교-9604(2026. 9. 17.) 「[참석] 교육부 「2026 AIEDAP 마스터교원 신규연수 초등 1차」 대상자 선정 결과 및 연수 일정 안내」';
    var destination = '경상북도 경주시 더케이호텔 경주';
    var contact = '01042330844';
    var transport = '자가용';
    
    function setBoth(ctrlId, val) {
        var ctrl = popup.lookup(ctrlId);
        if (ctrl) {
            if (ctrl.setValue) ctrl.setValue(val);
            else ctrl.value = val;
            try {
                ctrl.dispatchEvent(new cpr.events.CValueChangeEvent('value-change', {oldValue: '', newValue: val}));
            } catch(e) {}
            if (ctrl.redraw) ctrl.redraw();
        }
    }
    
    // 1. 기간 설정: 2026-11-07 11:00 ~ 18:00
    setBoth('dti1', '20261107');
    setBoth('cmb10', '11');
    setBoth('cmb2', '00');
    setBoth('dti2', '20261107');
    setBoth('cmb3', '18');
    setBoth('cmb4', '00');
    
    // 2. 출장종류: 국내출장(관내)
    setBoth('cmbBsrpScCd', '10');
    
    // 3. 연락처
    setBoth('mse1', contact);
    
    // 4. 출장지
    setBoth('ipbDobtNm', destination);
    
    // 5. 출장목적
    setBoth('ipbBsrpCn', fullPurpose);
    
    // 6. 이동사항
    setBoth('ipbMvmnMteCn', transport);
    
    // 7. dsBsrp 동기화
    var dsBsrp = popup.lookup('dsBsrp');
    if (dsBsrp && dsBsrp.getRowCount() > 0) {
        dsBsrp.setValue(0, 'bsrpCn', fullPurpose);
        dsBsrp.setValue(0, 'dobtNm', destination);
        dsBsrp.setValue(0, 'mvmnMteCn', transport);
        dsBsrp.setValue(0, 'emgCnctTelno', contact);
        dsBsrp.setValue(0, 'bsrpScCd', '10');
        dsBsrp.setValue(0, 'bsrpScNm', '국내출장(관내)');
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
        dsBsrp.setValue(0, 'ddRpatYn', 'N');
        dsBsrp.setValue(0, 'tvctPyrfYn', 'N');
    }
    
    // 8. 출장자 목록(dsTgpr) 동기화
    var grdTgpr = popup.lookup('grdTgpr');
    if (grdTgpr) {
        try { grdTgpr.setCheckRowIndex(0, true); } catch(e){}
    }
    var btnDdHr = popup.lookup('btnDdHr');
    if (btnDdHr) {
        try { btnDdHr.click(); } catch(e){}
    }
    
    // Focus to bottom
    var ctrlFocus = popup.lookup('ipbBsrpCn');
    if (ctrlFocus) ctrlFocus.focus();
    
    return {
        success: true,
        ipbDobtNm: popup.lookup('ipbDobtNm') ? popup.lookup('ipbDobtNm').value : null,
        ipbBsrpCn: popup.lookup('ipbBsrpCn') ? popup.lookup('ipbBsrpCn').value : null,
        mse1: popup.lookup('mse1') ? popup.lookup('mse1').value : null,
        ipbMvmnMteCn: popup.lookup('ipbMvmnMteCn') ? popup.lookup('ipbMvmnMteCn').value : null
    };
"""

out = driver.execute_script(js_force_fill)
print('Filled values verification:')
print(json.dumps(out, ensure_ascii=False, indent=2))

time.sleep(1)
driver.save_screenshot('C:/Users/user/.gemini/antigravity/brain/0c28257f-d0fa-4331-a07e-b804c459ee32/confirmed_filled_screen.png')
print('Screenshot confirmed_filled_screen.png saved!')
