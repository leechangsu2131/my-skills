import asyncio
import io
import json
import os
import sys
from playwright.async_api import async_playwright

# CP949 터미널 한글 깨짐 방지 및 EVPN 용 no_proxy 설정
os.environ["no_proxy"] = "localhost,127.0.0.1"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

JS_TEST_UPDATE = """
(function() {
    var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
    });
    if (!main) return {error: "Main app not found"};

    var dsGicRec = main.lookup("dsGicRec");
    var grdMain = main.lookup("grdMain");

    // 2명 테스트용 데이터
    var testData = {
        "강시우": "봉사활동의 의미와 필요성에 대해 성실한 태도로 학습함 (테스트)",
        "김가을": "봉사활동 교육에 집중하여 참여함 (테스트)"
    };

    var logs = [];
    var count = dsGicRec.getRowCount();
    for (var r=0; r<count; r++) {
        var name = dsGicRec.getValue(r, "stuFlnm");
        var val = testData[name];
        if (val) {
            dsGicRec.setValue(r, "speclActSpablMteCn", val);
            logs.push(name + " 행 " + r + "번에 테스트 문구 입력 완료");
        }
    }

    grdMain.redraw();
    return {status: "success", logs: logs};
})();
"""


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
            
            # JS 테스트 구동
            print("Injecting test update for 2 students (강시우, 김가을)...")
            result = await target_page.evaluate(JS_TEST_UPDATE)
            print("TEST UPDATE RESULTS:")
            print(json.dumps(result, ensure_ascii=True, indent=2))
            
            # 2초간 화면 반영 대기 후 캡처
            await asyncio.sleep(2.0)
            os.makedirs("scratch", exist_ok=True)
            await target_page.screenshot(path="scratch/test_entry_screenshot.png")
            print("Screen verification captured at scratch/test_entry_screenshot.png")
            
        except Exception as e:
            print("Error occurred during test:", e)

if __name__ == "__main__":
    asyncio.run(main())
