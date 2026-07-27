# -*- coding: utf-8 -*-
"""나이스 학급 콤보박스의 선택 항목들을 진단합니다."""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)
print(f"[연결] {driver.title}")

# 반 콤보박스(Combobox) 데이터셋 조회
result = driver.execute_script("""
    var insts = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var comboData = [];
    
    for (var i = 0; i < insts.length; i++) {
        var inst = insts[i];
        if (!inst || !inst.app) continue;
        
        // udcSwcAuth 컴포넌트나 콤보박스에 바인딩된 데이터셋 탐색
        var datasets = inst.getAllDataControls ? inst.getAllDataControls() : [];
        for (var j = 0; j < datasets.length; j++) {
            var ds = datasets[j];
            if (ds && ds.type === 'dataset' && (ds.id.indexOf('cls') >= 0 || ds.id.indexOf('Cls') >= 0 || ds.id.indexOf('Auth') >= 0)) {
                var rowCount = ds.getRowCount();
                var cols = ds.getColumnNames ? ds.getColumnNames() : [];
                var rows = [];
                for (var r = 0; r < rowCount; r++) {
                    var row = {};
                    for (var cc = 0; cc < cols.length; cc++) {
                        var val = ds.getValue(r, cols[cc]);
                        // 디코딩
                        if (typeof val === 'string') {
                            try {
                                val = val.encode('latin1').decode('euc-kr');
                            } catch(e) {
                                try {
                                    // 브라우저 내부이므로 TextDecoder 사용 가능
                                    var bytes = new Uint8Array(val.split('').map(function(c) { return c.charCodeAt(0); }));
                                    val = new TextDecoder('euc-kr').decode(bytes);
                                } catch(err) {}
                            }
                        }
                        row[cols[cc]] = val;
                    }
                    rows.push(row);
                }
                comboData.push({
                    app: inst.app.id,
                    ds: ds.id,
                    rows: rows
                });
            }
        }
    }
    return comboData;
""")

print("\n--- 반 콤보박스 데이터셋 정보 ---")
for item in result:
    print(f"📂 App: {item['app']} | DS: {item['ds']}")
    for r in item['rows']:
        print(f"  {r}")

driver.quit()
