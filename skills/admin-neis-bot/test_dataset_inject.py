#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""데이터셋 직접 주입(API)을 통한 결재자 강동휘 추가 테스트 스크립트."""

import io, sys, time, json
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)

for handle in driver.window_handles:
    driver.switch_to.window(handle)
    driver.switch_to.default_content()
    try:
        if driver.execute_script("return typeof cpr !== 'undefined';") and "vpn" not in driver.current_url.lower():
            break
    except: pass

print(f"[connect] {driver.title}")

# 1) 데이터셋 직접 로우 추가 및 복사 실행
JS_DATASET_INJECT = """
return (function() {
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var pop = instances.find(function(ai) {
        return ai && ai.app && ai.app.id === "edu/cm/wam/woa/pm/wam_woapm07_p04";
    });
    if (!pop) return {error: "p04 not open"};
    
    var dsMain = pop.lookup("dsMain");
    var dsParam = pop.lookup("dsParam");
    if (!dsMain || !dsParam) return {error: "datasets not found"};
    
    // 강동휘 로우 찾기
    var targetRow = -1;
    for (var i = 0; i < dsMain.getRowCount(); i++) {
        if (dsMain.getValue(i, "userNm") === "강동휘") {
            targetRow = i;
            break;
        }
    }
    if (targetRow === -1) return {error: "강동휘 not found in dsMain"};
    
    // dsParam에 직접 로우 추가 및 모든 공통 컬럼 값 복사
    var cols = ["userDtcNo", "userId", "userNm", "orgCd", "ogdpOrgCd", "jbpsCd", "hffcStsCd", "hffcStsNm", "jbpsNm"];
    
    try {
        // eXBuilder6 데이터셋 insertRow (행인덱스)
        // insertRow가 성공하면 생성된 Row 객체 또는 인덱스를 반환
        var newIdx = dsParam.insertRow(dsParam.getRowCount());
        
        cols.forEach(function(col) {
            var val = dsMain.getValue(targetRow, col);
            dsParam.setValue(newIdx, col, val);
        });
        
        // kornOrgNm 컬럼 채우기 (dsMain의 allKornOrgNm 등에서 가져옴)
        var orgNm = dsMain.getValue(targetRow, "allKornOrgNm") || dsMain.getValue(targetRow, "kornOrgNm") || "";
        dsParam.setValue(newIdx, "kornOrgNm", orgNm);
        
        // 결재구분 등 다른 컬럼이 있다면 추가 세팅
        // (보통 결재선은 atrzScCd, atrzScNm 등 구분 컬럼이 결재자로 세팅되어야 함)
        // 이전 덤프된 dsSancr 컬럼: ['userDtcNo', 'userId', 'userNm', 'orgCd', 'ogdpOrgCd', 'jbpsCd', 'jbpsNm', 'hffcStsCd', 'hffcStsNm', 'kornOrgNm']
        
        // 변경사항 화면 그리드에 그리도록 지시
        var grdTo = pop.lookup("grdUserListTo");
        if (grdTo) grdTo.redraw();
        
        // 현재 dsParam 덤프
        var list = [];
        for (var k = 0; k < dsParam.getRowCount(); k++) {
            list.push({
                userNm: dsParam.getValue(k, "userNm"),
                userId: dsParam.getValue(k, "userId"),
                userDtcNo: dsParam.getValue(k, "userDtcNo")
            });
        }
        return {ok: true, list: list};
        
    } catch(e) {
        return {error: e.message};
    }
})();
"""

res = driver.execute_script(JS_DATASET_INJECT)
print("직접 데이터셋 주입 결과:", res)
