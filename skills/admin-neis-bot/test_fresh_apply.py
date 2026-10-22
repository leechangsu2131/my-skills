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

# 1. Close current popup
js_close = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (popup) {
        popup.close(false);
        return 'closed';
    }
    return 'not open';
"""
print('Close:', driver.execute_script(js_close))
time.sleep(2)

# 2. Open fresh popup from main
js_open = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var main = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_m00'; });
    var btn = main.lookup('btnAply');
    btn.click();
    return 'clicked';
"""
print('Reopen:', driver.execute_script(js_open))
time.sleep(2)

# 3. Fill via pure UI controls with events
js_fill_pure = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) return 'no popup';
    
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
    
    // 1. 기간: 11/07 11:00 ~ 11/07 18:00 (1일차)
    setControl('dti1', '20261107');
    setControl('cmb10', '11');
    setControl('cmb2', '00');
    setControl('dti2', '20261107');
    setControl('cmb3', '18');
    setControl('cmb4', '00');
    
    // 2. 출장종류: 국내출장(관내) '10'
    setControl('cmbBsrpScCd', '10');
    
    // 3. 연락처
    setControl('mse1', '01042330844');
    
    // 4. 출장지
    setControl('ipbDobtNm', '경상북도 경주시 더케이호텔 경주');
    
    // 5. 출장목적
    setControl('ipbBsrpCn', '2026 AIEDAP 마스터교원 신규연수(초등 1차) 참석 화천초등학교-9604(2026. 9. 17.) 「[참석] 교육부 「2026 AIEDAP 마스터교원 신규연수 초등 1차」 대상자 선정 결과 및 연수 일정 안내」');
    
    // 6. 이동사항
    setControl('ipbMvmnMteCn', '자가용');
    
    // 7. 출장자 목록 동일시간 동기화
    var grdTgpr = popup.lookup('grdTgpr');
    if (grdTgpr) grdTgpr.setCheckRowIndex(0, true);
    var btnDdHr = popup.lookup('btnDdHr');
    if (btnDdHr) btnDdHr.click();
    
    return {
        success: true,
        dsBsrp: popup.lookup('dsBsrp').getRowDataRanged()[0],
        dsTgpr: popup.lookup('dsTgpr').getRowDataRanged()[0]
    };
"""
res = driver.execute_script(js_fill_pure)
print('Fill result:')
print(json.dumps(res, ensure_ascii=False, indent=2))

driver.save_screenshot('C:/Users/user/.gemini/antigravity/brain/0c28257f-d0fa-4331-a07e-b804c459ee32/fresh_filled.png')
print('Screenshot saved!')
