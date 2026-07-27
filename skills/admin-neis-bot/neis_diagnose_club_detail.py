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

JS_DIAGNOSE_DETAIL = """
(function() {
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var info = [];
    apps.forEach(function(ai) {
        if (!ai || !ai.app) return;
        var dsList = {};
        // 모든 데이터셋 스캔
        try {
            var keys = Object.keys(ai);
            // ai 내부의 lookup을 통해 데이터셋 스캔 시도
            if (ai.getContainer) {
                var c = ai.getContainer();
                if (c && c.getAllRecursiveChildren) {
                    c.getAllRecursiveChildren().forEach(function(ctrl) {
                        if (ctrl && ctrl.type === "grid") {
                            var ds = ctrl.dataSet;
                            if (ds && ds.id) {
                                var cols = ds.getColumnNames ? ds.getColumnNames() : [];
                                var rows = [];
                                for (var r = 0; r < Math.min(ds.getRowCount(), 3); r++) {
                                    var row = {};
                                    cols.forEach(function(col) {
                                        row[col] = ds.getValue(r, col);
                                    });
                                    rows.push(row);
                                }
                                dsList[ds.id] = {
                                    cols: cols,
                                    rowCount: ds.getRowCount(),
                                    sample: rows
                                };
                            }
                        }
                    });
                }
            }
        } catch(e) {
            dsList.error = e.toString();
        }
        info.push({
            appId: ai.app.id,
            datasets: dsList
        });
    });
    return info;
})();
"""

async def main():
    async with async_playwright() as p:
        try:
            print("Connecting to Chrome over CDP on port 9222 for detailed diagnosis...")
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
            
            # 상세 진단 구동
            result = await target_page.evaluate(JS_DIAGNOSE_DETAIL)
            print("DETAILED APP DIAGNOSTIC DUMP:")
            print(json.dumps(result, ensure_ascii=True, indent=2))
            
            # 스크린샷 캡처
            os.makedirs("scratch", exist_ok=True)
            await target_page.screenshot(path="scratch/club_diagnose_screenshot.png")
            print("Screenshot saved to scratch/club_diagnose_screenshot.png")
            
        except Exception as e:
            print("Error occurred during detailed diagnosis:", e)

if __name__ == "__main__":
    asyncio.run(main())
