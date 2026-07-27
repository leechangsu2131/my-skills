import asyncio
import io
import json
import os
import re
import sys
import argparse
from playwright.async_api import async_playwright

# CP949 터미널 한글 깨짐 방지 및 EVPN 용 no_proxy 설정
os.environ["no_proxy"] = "localhost,127.0.0.1"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

draft_path = r"C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\admin-neis-bot\data\독서동아리_누가기록_초안 (1).md"

def parse_opinions(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 창체(동아리활동) 특기사항 섹션 추출
    section_match = re.search(r'#\s*창체\(동아리활동\)\s*특기사항.*?(?=\Z)', content, re.DOTALL)
    if not section_match:
        print("Error: 창체(동아리활동) 특기사항 섹션을 찾을 수 없습니다.")
        return {}
        
    section = section_match.group(0)
    lines = section.split('\n')
    opinions = {}
    
    # 1. 강시우: ... 형태의 줄 파싱
    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = re.match(r'^\d+\.\s*([^:\(]+)(?:\([^\)]+\))?\s*:\s*(.+)$', line)
        if match:
            name = match.group(1).strip()
            text = match.group(2).strip()
            opinions[name] = text
            
    return opinions

JS_OPINION_UPDATE = """
(function() {
    var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m06";
    });
    if (!main) return {error: "Main app (els_sdlce01_m06) not found. Please click '학생부자료기록' tab and Search."};

    var dsScrgRec = main.lookup("dsScrgRec");
    var grdMain = main.lookup("grdMain");

    var opinionData = OPINION_DATA_JSON;
    var logs = [];
    var count = dsScrgRec.getRowCount();
    
    for (var r=0; r<count; r++) {
        var name_raw = dsScrgRec.getValue(r, "stuFlnm");
        var name = name_raw.replace(/\(.*\)/, "").trim();
        var val = opinionData[name];
        if (val) {
            dsScrgRec.setValue(r, "speclActSpablMteCn", val);
            logs.push(name + " (" + r + "행): 특기사항 주입 완료");
        } else {
            logs.push(name + " (" + r + "행): 매칭되는 의견 없음");
        }
    }

    grdMain.redraw();
    
    // 저장 버튼 클릭 헬퍼 (apply 모드용)
    window.__clickSaveOpinion = function() {
        var btnSave = main.lookup("btnSave");
        if (btnSave) {
            btnSave.click();
            return true;
        }
        return false;
    };
    
    // 모달 승인 헬퍼
    window.__closeOpinionDialog = function() {
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
    };

    return {status: "success", count: count, logs: logs};
})();
"""

async def main():
    parser = argparse.ArgumentParser(description="동아리활동 특기사항 입력 자동화")
    parser.add_argument("--apply", action="store_true", help="실제 저장 반영 여부")
    args = parser.parse_args()
    
    opinions = parse_opinions(draft_path)
    print("Parsed opinions counts:", len(opinions))
    if not opinions:
        return
        
    print("Sample (강시우):", opinions.get("강시우"))
    
    js_payload = JS_OPINION_UPDATE.replace("OPINION_DATA_JSON", json.dumps(opinions, ensure_ascii=False))

    async with async_playwright() as p:
        try:
            print("Connecting to Chrome over CDP on port 9222...")
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            
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
                print("Error: Active NEIS page not found.")
                return
                
            print(f"Connected to page: {await target_page.title()}")
            
            # 주입 로직 실행
            print("Injecting individual opinions into dsScrgRec...")
            res = await target_page.evaluate(js_payload)
            if "error" in res:
                print("Error from JS:", res["error"])
                return
                
            print("INJECTION LOGS:")
            for log in res["logs"][:5]:
                print(" -", log)
            print(f"Total processed: {res['count']} rows")
            
            # 실제 저장
            if args.apply:
                print("Apply flag detected. Clicking save...")
                saved = await target_page.evaluate("window.__clickSaveOpinion()")
                if saved:
                    print("Save button clicked. Resolving eXBuilder confirm/alert dialogs...")
                    for _ in range(5):
                        await asyncio.sleep(1.0)
                        closed = await target_page.evaluate("window.__closeOpinionDialog()")
                        if closed:
                            print(" - Dialog closed successfully.")
                    print("Save sequence finished.")
                else:
                    print("Error: Save button not found or not clickable.")
            else:
                print("[DRY RUN] Apply flag not set. Skipping save.")
                
            # 스크린샷 캡처
            os.makedirs("scratch", exist_ok=True)
            await target_page.screenshot(path="scratch/club_opinion_applied.png")
            print("Screen verification captured at scratch/club_opinion_applied.png")
            
        except Exception as e:
            print("Error occurred:", e)

if __name__ == "__main__":
    asyncio.run(main())
