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

js_setup = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) return {error: 'no popup'};
    
    var fullPurpose = '2026 AIEDAP 마스터교원 신규연수(초등 1차) 참석 화천초등학교-9604(2026. 9. 17.) 「[참석] 교육부 「2026 AIEDAP 마스터교원 신규연수 초등 1차」 대상자 선정 결과 및 연수 일정 안내」';
    var destination = '경상북도 경주시 더케이호텔 경주';
    var contact = '01042330844';
    var transport = '자가용';
    
    function setCtrl(id, val) {
        var c = popup.lookup(id);
        if (c) {
            c.value = val;
            try {
                c.dispatchEvent(new cpr.events.CValueChangeEvent('value-change', {oldValue: '', newValue: val}));
            } catch(e) {}
            if (c.redraw) c.redraw();
        }
    }
    
    // 1. 기간정보 목록 (dsBsrp) 정돈
    var dsBsrp = popup.lookup('dsBsrp');
    dsBsrp.clear();
    
    // Row 0: 2026-11-07 09:00 ~ 17:00
    var row0 = {
        "instCd": "R100006630",
        "instNm": "화천초등학교",
        "bsrpSn": "0",
        "bsrpScCd": "10",
        "bsrpScNm": "국내출장(관내)",
        "bgngYmd": "20261107",
        "bgngHm": "0900",
        "bgngHh": "09",
        "bgngMm": "00",
        "endYmd": "20261107",
        "endHm": "1700",
        "endHh": "17",
        "endMm": "00",
        "allBsrpHrDdCnt": "0",
        "allBsrpHrHCnt": "8",
        "allBsrpHrMCnt": "0",
        "emgCnctTelno": contact,
        "dobtNm": destination,
        "bsrpCn": fullPurpose,
        "mvmnMteCn": transport,
        "offlVhcUtilzYn": "N",
        "tvctPyrfYn": "N",
        "tngrAssBsrpYn": "N",
        "frntnInvieYn": "N",
        "ddRpatYn": "N",
        "eduDisciYn": "N",
        "lunchHrWorkInclsYn": "Y",
        "bfrBsrpSn": "-1",
        "bsrpPuoCnt": "1",
        "bsrpNpoCnt": "0",
        "delYn": "N",
        "atrzStsCd": "9",
        "rveFlnm": "이창수",
        "apsInvlNo": "R101053140"
    };
    
    // Row 1: 2026-11-08 09:00 ~ 17:00
    var row1 = {
        "instCd": "R100006630",
        "instNm": "화천초등학교",
        "bsrpSn": "1",
        "bsrpScCd": "10",
        "bsrpScNm": "국내출장(관내)",
        "bgngYmd": "20261108",
        "bgngHm": "0900",
        "bgngHh": "09",
        "bgngMm": "00",
        "endYmd": "20261108",
        "endHm": "1700",
        "endHh": "17",
        "endMm": "00",
        "allBsrpHrDdCnt": "0",
        "allBsrpHrHCnt": "8",
        "allBsrpHrMCnt": "0",
        "emgCnctTelno": contact,
        "dobtNm": destination,
        "bsrpCn": fullPurpose,
        "mvmnMteCn": transport,
        "offlVhcUtilzYn": "N",
        "tvctPyrfYn": "N",
        "tngrAssBsrpYn": "N",
        "frntnInvieYn": "N",
        "ddRpatYn": "N",
        "eduDisciYn": "N",
        "lunchHrWorkInclsYn": "Y",
        "bfrBsrpSn": "-1",
        "bsrpPuoCnt": "1",
        "bsrpNpoCnt": "0",
        "delYn": "N",
        "atrzStsCd": "9",
        "rveFlnm": "이창수",
        "apsInvlNo": "R101053140"
    };
    
    dsBsrp.insertRowData(0, true, row0);
    dsBsrp.insertRowData(1, true, row1);
    
    // 2. 출장자 목록 (dsTgpr) 정돈 - 이창수 교사 딱 1행!
    var dsTgpr = popup.lookup('dsTgpr');
    dsTgpr.clearFilter();
    dsTgpr.clear();
    
    var tgprRow = {
        "instCd": "R100006630",
        "dptCd": "R100006630",
        "dptNm": "화천초등학교",
        "invlNo": "R101053140",
        "invlFlnm": "이창수",
        "jbgdCd": "04147",
        "jbgdNm": "초등학교교사",
        "rprsYn": "Y",
        "cncdSn": "1",
        "bsrpSn": "0",
        "bgngYmd": "20261107",
        "bgngHh": "09",
        "bgngMm": "00",
        "bgngHm": "0900",
        "endYmd": "20261107",
        "endHh": "17",
        "endMm": "00",
        "endHm": "1700",
        "puoYn": "Y",
        "puoYnNm": "정규직원",
        "chgYn": "N",
        "srvPsnScCd": "",
        "sameBsrpPriodYn": "Y",
        "emgCnctTelno": "010-4233-0844"
    };
    dsTgpr.insertRowData(0, true, tgprRow);
    
    // 3. UI 컨트롤 채움
    setCtrl('cmbBsrpScCd', '10');
    setCtrl('mse1', contact);
    setCtrl('ipbDobtNm', destination);
    setCtrl('ipbBsrpCn', fullPurpose);
    setCtrl('ipbMvmnMteCn', transport);
    
    // 4. 기간정보 1행 UI 매핑
    setCtrl('dti1', '20261107');
    setCtrl('cmb10', '09');
    setCtrl('cmb2', '00');
    setCtrl('dti2', '20261107');
    setCtrl('cmb3', '17');
    setCtrl('cmb4', '00');
    
    // 5. 그리드 redraw
    popup.lookup('grdMain').redraw();
    popup.lookup('grdTgpr').redraw();
    popup.lookup('grdTgpr').setCheckRowIndex(0, true);
    
    // Focus down
    popup.lookup('btnAply').focus();
    
    return {
        success: true,
        bsrpCount: dsBsrp.getRowCount(),
        tgprCount: dsTgpr.getRowCount(),
        bsrpRows: dsBsrp.getRowDataRanged().map(function(r){
            return r.bgngYmd + ' ' + r.bgngHm + ' ~ ' + r.endYmd + ' ' + r.endHm + ' (' + r.allBsrpHrHCnt + '시간)';
        }),
        tgprRow: dsTgpr.getRowDataRanged()[0]
    };
"""

res = driver.execute_script(js_setup)
print('Setup result:')
print(json.dumps(res, ensure_ascii=False, indent=2))

time.sleep(1)
driver.save_screenshot('C:/Users/user/.gemini/antigravity/brain/0c28257f-d0fa-4331-a07e-b804c459ee32/final_both_days_screen.png')
print('Screenshot final_both_days_screen.png saved!')
