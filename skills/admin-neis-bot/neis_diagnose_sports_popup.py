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

JS_DIAGNOSE_POPUP_CONTROLS = """
(function() {
    var popup = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai.app && ai.app.id === "edu/sa/phe/phe/sm/phe_phesm02_p01";
    });
    if (!popup) return {error: "Popup app (phe_phesm02_p01) not found"};

    var controls = [];
    var container = popup.getContainer();
    if (container && container.getAllRecursiveChildren) {
        container.getAllRecursiveChildren().forEach(function(c) {
            if (c && c.id) {
                controls.push({
                    id: c.id,
                    type: c.type,
                    value: c.value || c.text || "",
                    placeholder: c.placeholder || ""
                });
            }
        });
    }
    
    return {
        appId: popup.app.id,
        controls: controls
    };
})();
"""

async def main():
    async with async_playwright() as p:
        try:
            print("Connecting to Chrome over CDP on port 9222 for popup controls diagnosis...")
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
            
            # 상세 컨트롤 진단 구동
            result = await target_page.evaluate(JS_DIAGNOSE_POPUP_CONTROLS)
            print("POPUP CONTROLS DUMP:")
            print(json.dumps(result, ensure_ascii=True, indent=2))
            
        except Exception as e:
            print("Error occurred during popup diagnosis:", e)

if __name__ == "__main__":
    asyncio.run(main())
