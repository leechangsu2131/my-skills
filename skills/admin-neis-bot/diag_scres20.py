# -*- coding: utf-8 -*-
"""모든 앱 인스턴스에서 데이터셋 전수 탐색"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)
print(f"[연결] {driver.title}")

# 모든 앱 인스턴스를 순회하며 데이터가 있는 데이터셋 탐색
result = driver.execute_script("""
    var insts = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var allFound = [];
    
    var dsNames = [
        'dsGnrlzOpinListByYear', 'dsMain', 'dsGnrlzOpin', 'dsSbjt',
        'dsStdnt', 'dsStudent', 'dsCurrByRec', 'dsGnrlz',
        'dsSpclNote', 'dsSebu', 'dsSubject', 'dsGnrlzOpinList',
        'dsOpinList', 'dsRecList', 'dsSbjtList', 'dsStdntList',
        'dsCurrList', 'dsStdntSpeInfo', 'dsStdntSpclNote',
        'dsGnrlzOpnList', 'dsGnrlzOpnListByYear'
    ];
    
    for (var i = 0; i < insts.length; i++) {
        var inst = insts[i];
        if (!inst || !inst.app) continue;
        var appId = inst.app.id;
        
        for (var j = 0; j < dsNames.length; j++) {
            try {
                var ds = inst.lookup(dsNames[j]);
                if (ds && ds.getRowCount && typeof ds.getRowCount === 'function') {
                    var rowCount = ds.getRowCount();
                    var cols = [];
                    for (var c = 0; c < Math.min(ds.getColCount(), 15); c++) {
                        cols.push(ds.getColID(c));
                    }
                    // 첫 번째 행 샘플
                    var sample = {};
                    if (rowCount > 0) {
                        for (var cc = 0; cc < cols.length; cc++) {
                            sample[cols[cc]] = ds.getValue(0, cols[cc]);
                        }
                    }
                    allFound.push({
                        app: appId,
                        ds: dsNames[j],
                        rows: rowCount,
                        cols: cols,
                        sample: sample
                    });
                }
            } catch(e) {}
        }
    }
    return allFound;
""")

print(f"[전체 데이터셋] {len(result)}개 발견")
for item in result:
    print(f"\n  앱: {item['app']}")
    print(f"  DS: {item['ds']} ({item['rows']}행)")
    print(f"  컬럼: {item['cols']}")
    if item['rows'] > 0:
        print(f"  샘플행[0]: {item['sample']}")

driver.quit()
