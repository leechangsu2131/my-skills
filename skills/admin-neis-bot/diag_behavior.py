# -*- coding: utf-8 -*-
"""행동특성 및 종합의견 화면이 정상적으로 감지되는지 검사합니다."""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=opts)
print(f"[연결] {driver.title}")

check_js = """
function checkBehaviorApp() {
    var result = { found: false, appId: null, datasets: [], error: null };
    try {
        var handles = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        for (var i = 0; i < handles.length; i++) {
            var inst = handles[i];
            if (inst && inst.app && inst.app.id && inst.app.id.indexOf('els_sdlbg00') >= 0) {
                result.found = true;
                result.appId = inst.app.id;
                
                // 데이터셋 탐색
                var controls = inst.getAllDataControls ? inst.getAllDataControls() : [];
                for (var j = 0; j < controls.length; j++) {
                    var ctrl = controls[j];
                    if (ctrl && ctrl.type === 'dataset') {
                        var rowCount = ctrl.getRowCount();
                        var cols = ctrl.getColumnNames ? ctrl.getColumnNames() : [];
                        if (cols.length === 0 && ctrl.getColCount) {
                            for (var c = 0; c < ctrl.getColCount(); c++) cols.push(ctrl.getColID(c));
                        }
                        
                        // 첫 2개 행 데이터
                        var rows = [];
                        for (var r = 0; r < Math.min(rowCount, 2); r++) {
                            var row = {};
                            for (var cc = 0; cc < cols.length; cc++) {
                                row[cols[cc]] = ctrl.getValue(r, cols[cc]);
                            }
                            rows.push(row);
                        }
                        
                        result.datasets.push({
                            id: ctrl.id,
                            rows: rowCount,
                            cols: cols,
                            data: rows
                        });
                    }
                }
                break; // 행동특성 앱을 하나만 찾으면 족함
            }
        }
    } catch(e) {
        result.error = e.message;
    }
    return result;
}
return checkBehaviorApp();
"""

# 메인 및 iframe 순회
app_found = None
res = None

# 일단 프레임 순회 함수 구현
def search_in_frames():
    global res
    handles = driver.window_handles
    for handle in handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        try:
            res = driver.execute_script(check_js)
            if res.get("found"):
                return "main"
        except Exception:
            pass
            
        try:
            frames = driver.find_elements(By.TAG_NAME, "iframe")
            for idx, frame in enumerate(frames):
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(frame)
                    res = driver.execute_script(check_js)
                    if res.get("found"):
                        return f"iframe_{idx}"
                except Exception:
                    pass
        except Exception:
            pass
    return None

frame_loc = search_in_frames()
if frame_loc:
    print(f"🎉 '{res['appId']}' 앱 발견! (위치: {frame_loc})")
    for ds in res['datasets']:
        print(f"  📊 [Dataset] {ds['id']} (행 수: {ds['rows']})")
        print(f"    컬럼: {ds['cols']}")
        if ds['rows'] > 0:
            print("    샘플 행:")
            for idx, r in enumerate(ds['data']):
                decoded = {}
                for k, v in r.items():
                    if isinstance(v, str):
                        try:
                            decoded[k] = v.encode('latin1').decode('euc-kr')
                        except Exception:
                            decoded[k] = v
                    else:
                        decoded[k] = v
                print(f"      [{idx}] {decoded}")
else:
    print("❌ 'els_sdlbg00' (행동특성) 앱을 찾을 수 없습니다. 나이스에서 해당 메뉴를 열고 조회해 주세요.")

driver.quit()
