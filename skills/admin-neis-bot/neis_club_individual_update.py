import io, sys, time, json, re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# CP949 터미널 한글 깨짐 방지 및 EVPN 용 no_proxy 설정
import os
os.environ["no_proxy"] = "localhost,127.0.0.1"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

draft_path = r"C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\admin-neis-bot\data\독서동아리_누가기록_초안.md"

def parse_draft(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    student_blocks = re.split(r'##\s+\d+\.\s+', content)
    records = {}
    
    for block in student_blocks[1:]:
        lines = block.strip().split('\n')
        name_raw = lines[0].strip()
        # 전입생 등 괄호 제거
        name = re.sub(r'\(.*\)', '', name_raw).strip()
        
        student_data = {}
        for line in lines[1:]:
            line_str = line.strip()
            if line_str.startswith('①'):
                student_data["1"] = line_str[1:].strip().lstrip('.').strip()
            elif line_str.startswith('②'):
                student_data["2"] = line_str[1:].strip().lstrip('.').strip()
            elif line_str.startswith('③'):
                student_data["3"] = line_str[1:].strip().lstrip('.').strip()
            elif line_str.startswith('④'):
                student_data["4"] = line_str[1:].strip().lstrip('.').strip()
        records[name] = student_data
    return records

draft_records = parse_draft(draft_path)
print("Parsed draft data counts:", len(draft_records))
# 샘플 출력
print("Sample (강시우):", json.dumps(draft_records.get("강시우"), ensure_ascii=False))

# selenium 연결
driver_path = r"C:\Users\lee21\.cache\selenium\chromedriver\win64\150.0.7871.115\chromedriver.exe"
service = Service(executable_path=driver_path)

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(service=service, options=opts)







# Find target window
target_handle = None
for handle in driver.window_handles:
    driver.switch_to.window(handle)
    driver.switch_to.default_content()
    try:
        if driver.execute_script("return typeof cpr !== 'undefined';") and "vpn" not in driver.current_url.lower():
            target_handle = handle
            break
    except: pass

if not target_handle:
    print("Error: Target window not found.")
    driver.quit()
    sys.exit(1)

# 메인 업데이트 자바스크립트 로직
JS_INDIVIDUAL_UPDATE = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "Main app not found"};

var dsGicRec = main.lookup("dsGicRec");
var dsActYmd = main.lookup("dsActYmd");
var grdActYmd = main.lookup("grdActYmd");
var grdMain = main.lookup("grdMain");

// 확인 다이얼로그 클릭 헬퍼
function clickCprDialogOk() {
    var clicked = false;
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    apps.forEach(function(ai) {
        if (ai && ai.app && (ai.app.id.indexOf("confirm") !== -1 || ai.app.id.indexOf("alert") !== -1 || ai.app.id.indexOf("cmn") !== -1)) {
            try {
                var container = ai.getContainer ? ai.getContainer() : null;
                if (container && container.getAllRecursiveChildren) {
                    container.getAllRecursiveChildren().forEach(function(c) {
                        if (c && c.type === "button") {
                            var val = c.value || c.text || "";
                            if (val === "예" || val === "확인" || val.indexOf("확인") !== -1 || val.indexOf("예") !== -1) {
                                try { c.click(); clicked = true; } catch(e) {}
                            }
                        }
                    });
                }
            } catch(err) {}
        }
    });
    return clicked;
}

async function waitDialog(ms) {
    var start = Date.now();
    while (Date.now() - start < ms) {
        if (clickCprDialogOk()) return true;
        await new Promise(r => setTimeout(r, 300));
    }
    return false;
}

var draftData = DRAFT_DATA_JSON;

async function updateAll() {
    var logs = [];
    var btnSave = main.lookup("btnSave");
    
    // -------------------------------------------------------------------------
    // 1. 7/9 일자 (Index 0) - 회차 ① 적용
    // -------------------------------------------------------------------------
    grdActYmd.selectRows([0]);
    await new Promise(r => setTimeout(r, 2000));
    
    var count0 = dsGicRec.getRowCount();
    for (var r=0; r<count0; r++) {
        var name = dsGicRec.getValue(r, "stuFlnm");
        var val = draftData[name] ? draftData[name]["1"] : null;
        if (val) {
            dsGicRec.setValue(r, "speclActSpablMteCn", val);
        }
    }
    grdMain.redraw();
    if (btnSave) {
        btnSave.click();
        var c1 = await waitDialog(3000);
        var a1 = await waitDialog(4000);
        logs.push({date: "7/9", confirm: c1, alert: a1});
    }
    await new Promise(r => setTimeout(r, 1500));

    // -------------------------------------------------------------------------
    // 2. 7/16 일자 (Index 1) - 회차 ②, ③ 분할 적용
    // -------------------------------------------------------------------------
    grdActYmd.selectRows([1]);
    await new Promise(r => setTimeout(r, 2000));
    
    var count1 = dsGicRec.getRowCount();
    var seen = {}; // 학생별 중복 횟수 트래킹
    for (var r=0; r<count1; r++) {
        var name = dsGicRec.getValue(r, "stuFlnm");
        if (!seen[name]) {
            seen[name] = 1;
            var val = draftData[name] ? draftData[name]["2"] : null;
            if (val) dsGicRec.setValue(r, "speclActSpablMteCn", val);
        } else {
            seen[name] += 1;
            var val = draftData[name] ? draftData[name]["3"] : null;
            if (val) dsGicRec.setValue(r, "speclActSpablMteCn", val);
        }
    }
    grdMain.redraw();
    if (btnSave) {
        btnSave.click();
        var c2 = await waitDialog(3000);
        var a2 = await waitDialog(4000);
        logs.push({date: "7/16", confirm: c2, alert: a2});
    }
    await new Promise(r => setTimeout(r, 1500));

    // -------------------------------------------------------------------------
    // 3. 7/24 일자 (Index 2) - 회차 ④ 적용
    // -------------------------------------------------------------------------
    grdActYmd.selectRows([2]);
    await new Promise(r => setTimeout(r, 2000));
    
    var count2 = dsGicRec.getRowCount();
    for (var r=0; r<count2; r++) {
        var name = dsGicRec.getValue(r, "stuFlnm");
        var val = draftData[name] ? draftData[name]["4"] : null;
        if (val) {
            dsGicRec.setValue(r, "speclActSpablMteCn", val);
        }
    }
    grdMain.redraw();
    if (btnSave) {
        btnSave.click();
        var c3 = await waitDialog(3000);
        var a3 = await waitDialog(4000);
        logs.push({date: "7/24", confirm: c3, alert: a3});
    }
    await new Promise(r => setTimeout(r, 1500));

    // 최종 검색 새로고침
    var btnSearch = main.lookup("btnSearch");
    if (btnSearch) {
        btnSearch.click();
    }
    
    return {status: "completed", logs: logs};
}

window.__updateResult = null;
updateAll().then(function(res) {
    window.__updateResult = res;
}).catch(function(err) {
    window.__updateResult = {error: err.toString()};
});

return "Individual update sequence started...";
""".replace("DRAFT_DATA_JSON", json.dumps(draft_records, ensure_ascii=False))

try:
    res = driver.execute_script(JS_INDIVIDUAL_UPDATE)
    print("JS sequence response:", res)
except Exception as e:
    print("Error:", e)

# 결과 대기 (최대 45초)
update_result = None
for attempt in range(45):
    time.sleep(1.0)
    try:
        val = driver.execute_script("return window.__updateResult;")
        if val is not None:
            update_result = val
            break
    except: pass

print("INDIVIDUAL UPDATE RESULTS:")
print(json.dumps(update_result, ensure_ascii=True, indent=2))

driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved.")

