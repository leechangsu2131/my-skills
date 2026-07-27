# -*- coding: utf-8 -*-
"""그리드에서 김주안 학생을 선택하고 오른쪽 상세 데이터셋이 로드되는지 테스트합니다."""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)
print(f"[연결] {driver.title}")

select_and_check_js = """
function runTest() {
    var insts = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var m00 = null;
    var m01 = null;
    
    for (var i = 0; i < insts.length; i++) {
        if (insts[i] && insts[i].app) {
            if (insts[i].app.id.indexOf('els_scres20_m00') >= 0) m00 = insts[i];
            if (insts[i].app.id.indexOf('els_scres20_m01') >= 0) m01 = insts[i];
        }
    }
    
    if (!m00) return { error: 'els_scres20_m00 not found' };
    
    // dsStdnt에서 김주안의 행 인덱스 찾기
    var ds = m00.lookup('dsStdnt');
    if (!ds) return { error: 'dsStdnt not found in m00' };
    
    var targetRow = -1;
    for (var r = 0; r < ds.getRowCount(); r++) {
        var name = ds.getValue(r, 'stdntNm') || '';
        // latin1 decoding 시도
        try {
            var decoded = name.encode ? name : name; // 브라우저 상이므로 간단히 비교
            if (name.indexOf('김주안') >= 0 || decoded.indexOf('김주안') >= 0) {
                targetRow = r;
                break;
            }
        } catch(e) {}
    }
    
    if (targetRow === -1) {
        // 인코딩된 상태로도 비교 시도
        for (var r = 0; r < ds.getRowCount(); r++) {
            var name = ds.getValue(r, 'stdntNm') || '';
            // '김주안'의 EUC-KR latin1 표현: "±èÁÖ¾È"
            if (name.indexOf('±èÁÖ¾È') >= 0) {
                targetRow = r;
                break;
            }
        }
    }
    
    if (targetRow === -1) return { error: '김주안 student not found in dsStdnt', rowCount: ds.getRowCount() };
    
    // 그리드 컴포넌트 찾기
    var grid = m00.lookup('grdStdnt');
    if (!grid) grid = m00.lookup('grdMain');
    if (!grid) return { error: 'Grid not found in m00', row: targetRow };
    
    // 그리드에서 행 선택 실행
    try {
        if (typeof grid.selectRows === 'function') {
            grid.selectRows([targetRow]);
        } else if (typeof grid.select === 'function') {
            grid.select([targetRow]);
        } else {
            // 다른 방식 선택
            return { error: 'grid select function not found', row: targetRow };
        }
    } catch(e) {
        return { error: 'grid selection failed: ' + e.message, row: targetRow };
    }
    
    return { success: true, selectedRow: targetRow, studentName: ds.getValue(targetRow, 'stdntNm') };
}
return runTest();
"""

res = driver.execute_script(select_and_check_js)
print("[선택 테스트 결과]", res)

if res.get("success"):
    # 로드 대기
    print("학생 선택 완료. 디테일 데이터 로드를 위해 3초 대기합니다...")
    time.sleep(3)
    
    # 디테일 데이터셋(m01의 dsGnrlzOpinListByYear00) 정보 조회
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
    
    // dsGnrlzOpinListByYear00 조회
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
