# -*- coding: utf-8 -*-
"""DOM에서 '김주안' 셀 요소를 직접 찾아 클릭을 트리거한 후 디테일 데이터셋 로드를 검증합니다."""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)
print(f"[연결] {driver.title}")

dom_click_js = """
function clickStudentCell() {
    // 1. 모든 엘리먼트 중 김주안 텍스트를 가진 요소 찾기 (보통 span 이나 div)
    var xpath = "//*[contains(text(), '김주안')]";
    var result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    
    var foundElement = null;
    for (var i = 0; i < result.snapshotLength; i++) {
        var el = result.snapshotItem(i);
        // 그리드(.cl-grid) 내부에 있는 셀인지 또는 클릭 가능한 요소인지 판별
        if (el && el.offsetHeight > 0) {
            foundElement = el;
            break;
        }
    }
    
    if (!foundElement) {
        // 인코딩 깨짐 대응 (EUC-KR 깨진 텍스트로 시도)
        var xpathEncoded = "//*[contains(text(), '±èÁÖ¾È')]";
        var resultEnc = document.evaluate(xpathEncoded, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
        for (var j = 0; j < resultEnc.snapshotLength; j++) {
            var elEnc = resultEnc.snapshotItem(j);
            if (elEnc && elEnc.offsetHeight > 0) {
                foundElement = elEnc;
                break;
            }
        }
    }
    
    if (!foundElement) return { error: '김주안 student cell element not found in DOM' };
    
    // 2. 스크롤 및 클릭 트리거
    try {
        foundElement.scrollIntoView({ block: 'center', inline: 'nearest' });
        
        // 클릭 이벤트 생성 및 디스패치
        var clickEvent = document.createEvent('MouseEvents');
        clickEvent.initEvent('click', true, true);
        foundElement.dispatchEvent(clickEvent);
        
        // 혹은 직접 .click() 호출
        if (typeof foundElement.click === 'function') {
            foundElement.click();
        }
    } catch(e) {
        return { error: 'Click failed: ' + e.message };
    }
    
    return { success: true, tagName: foundElement.tagName, text: foundElement.textContent };
}
return clickStudentCell();
"""

res = driver.execute_script(dom_click_js)
print("[DOM 클릭 테스트 결과]", res)

if res.get("success"):
    print("셀 클릭 완료! 트랜잭션 대기를 위해 4초 대기합니다...")
    time.sleep(4)
    
    # 상세 데이터셋(dsGnrlzOpinListByYear00) 정보 재조회
    check_detail_js = """
    var insts = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var m01 = null;
    for (var i = 0; i < insts.length; i++) {
        if (insts[i] && insts[i].app && insts[i].app.id.indexOf('els_scres20_m01') >= 0) {
            m01 = insts[i];
            break;
        }
    }
    if (!m01) return { error: 'm01 not found' };
    
    var ds = m01.lookup('dsGnrlzOpinListByYear00');
    if (!ds) ds = m01.lookup('dsGnrlzOpinListByYear');
    if (!ds) return { error: 'detail dataset not found' };
    
    var rowCount = ds.getRowCount();
    var cols = ds.getColumnNames ? ds.getColumnNames() : [];
    if (cols.length === 0 && ds.getColCount) {
        for (var c = 0; c < ds.getColCount(); c++) cols.push(ds.getColID(c));
    }
    
    var rows = [];
    for (var r = 0; r < rowCount; r++) {
        var row = {};
        for (var cc = 0; cc < cols.length; cc++) {
            var val = ds.getValue(r, cols[cc]);
            if (typeof val === 'string') {
                try {
                    val = val.encode('latin1').decode('euc-kr');
                } catch(e) {}
            }
            row[cols[cc]] = val;
        }
        rows.push(row);
    }
    return { dsId: ds.id, rows: rowCount, data: rows };
    """
    
    detail_res = driver.execute_script(check_detail_js)
    print("\n[상세 데이터셋 로드 결과]")
    if detail_res.get("error"):
        print("  ⚠️ 오류:", detail_res["error"])
    else:
        print(f"  📊 {detail_res['dsId']} ({detail_res['rows']}행)")
        for idx, r in enumerate(detail_res['data']):
            # 과목명 디코딩
            subj = r.get('sbjtNm') or r.get('subjectName') or ''
            try:
                subj = subj.encode('latin1').decode('euc-kr')
            except Exception:
                pass
            print(f"    [{idx}] 과목: {subj} | 내용 길이: {len(r.get('gnrlzOpiCn') or '')}자")

driver.quit()
