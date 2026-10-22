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

js_fill = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = null;
    for (var i = 0; i < apps.length; i++) {
        if (apps[i].app && apps[i].app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00') {
            popup = apps[i];
            break;
        }
    }
    if (!popup) return {error: 'Popup not found'};
    
    // Fill controls safely
    function setCtrlValue(id, val) {
        var ctrl = popup.lookup(id);
        if (ctrl) {
            ctrl.value = val;
            try {
                ctrl.dispatchEvent(new cpr.events.CValueChangeEvent('value-change', {oldValue: '', newValue: val}));
            } catch(e) {}
            return true;
        }
        return false;
    }
    
    // 1. 기간 설정
    setCtrlValue('dti1', '20261107');
    setCtrlValue('cmb10', '10');
    setCtrlValue('cmb2', '30');
    
    setCtrlValue('dti2', '20261108');
    setCtrlValue('cmb3', '18');
    setCtrlValue('cmb4', '00');
    
    // 2. 출장종류: 국내출장(관내) '10'
    setCtrlValue('cmbBsrpScCd', '10');
    
    // 3. 연락처
    setCtrlValue('mse1', '01042330844');
    
    // 4. 출장지
    setCtrlValue('ipbDobtNm', '경상북도 경주시 더케이호텔 경주');
    
    // 5. 출장목적
    setCtrlValue('ipbBsrpCn', '교육부 「2026 AIEDAP 마스터교원 신규연수 초등 1차」 집합연수 참석');
    
    // 6. 이동사항
    setCtrlValue('ipbMvmnMteCn', '자가용');
    
    // 7. 클릭 동일시간설정 (대상자 그리드 연동)
    var btnDdHr = popup.lookup('btnDdHr');
    if (btnDdHr) {
        btnDdHr.click();
    }
    
    // 8. dsBsrp 및 dsTgpr 상태 확인
    var dsBsrp = popup.lookup('dsBsrp');
    var dsTgpr = popup.lookup('dsTgpr');
    
    return {
        success: true,
        bsrpRow: dsBsrp ? dsBsrp.getRowDataRanged()[0] : null,
        tgprRow: dsTgpr ? dsTgpr.getRowDataRanged()[0] : null
    };
"""

res = driver.execute_script(js_fill)
print('Fill result:')
print(json.dumps(res, ensure_ascii=False, indent=2))

time.sleep(1)
# Take screenshot
driver.save_screenshot('C:/Users/user/.gemini/antigravity/brain/0c28257f-d0fa-4331-a07e-b804c459ee32/trip_filled_screenshot.png')
print('Screenshot saved!')
