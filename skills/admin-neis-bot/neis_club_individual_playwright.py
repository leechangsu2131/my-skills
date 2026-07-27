import asyncio
import io
import json
import os
import re
import sys
from playwright.async_api import async_playwright

# CP949 터미널 한글 깨짐 방지 및 EVPN 용 no_proxy 설정
import os
os.environ["no_proxy"] = "localhost,127.0.0.1"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

draft_path = r"C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\admin-neis-bot\data\독서동아리_누가기록_초안 (1).md"


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

# 메인 업데이트 자바스크립트 로직
JS_INDIVIDUAL_UPDATE = """
(function() {
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
        
        // 1. 7/9 일자 (Index 0) - 회차 ① 적용
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

        // 2. 7/16 일자 (Index 1) - 회차 ②, ③ 분할 적용
        grdActYmd.selectRows([1]);
        await new Promise(r => setTimeout(r, 2000));
        
        var count1 = dsGicRec.getRowCount();
        var seen = {};
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

        // 3. 7/24 일자 (Index 2) - 회차 ④ 적용
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
})();
""".replace("DRAFT_DATA_JSON", json.dumps(draft_records, ensure_ascii=False))


async def main():
    async with async_playwright() as p:
        try:
            print("Connecting to Chrome over CDP on port 9222...")
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")


            
            # target page 찾기
            target_page = None
            for context in browser.contexts:
                for page in context.pages:
                    url = page.url.lower()
                    try:
                        has_cpr = await page.evaluate("typeof cpr !== 'undefined'")
                    except:
                        has_cpr = False
                    
                    if has_cpr and "vpn" not in url:
                        target_page = page
                        break
                if target_page:
                    break
            
            if not target_page:
                print("Error: NEIS target page not found.")
                return
            
            print(f"Connected to page: {await target_page.title()}")
            
            # JS 로직 실행
            print("Initiating individual update script...")
            await target_page.evaluate(JS_INDIVIDUAL_UPDATE)
            
            # 결과 대기 (최대 45초)
            result = None
            for _ in range(45):
                await asyncio.sleep(1.0)
                val = await target_page.evaluate("window.__updateResult")
                if val is not None:
                    result = val
                    break
            
            print("INDIVIDUAL UPDATE RESULTS:")
            print(json.dumps(result, ensure_ascii=True, indent=2))
            
            # 스크린샷 저장
            os.makedirs("scratch", exist_ok=True)
            await target_page.screenshot(path="scratch/screenshot.png")
            print("Screenshot saved to scratch/screenshot.png")
            
        except Exception as e:
            print("Error occurred:", e)

if __name__ == "__main__":
    asyncio.run(main())
