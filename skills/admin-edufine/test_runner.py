import asyncio
import os
import sys
from playwright.async_api import async_playwright

# playwright_edufine 모듈 임포트를 위해 경로 추가
sys.path.append(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\admin-edufine")
import playwright_edufine

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        page = None
        for ctx in browser.contexts:
            for p_idx in ctx.pages:
                if "klef" in p_idx.url.lower():
                    page = p_idx
                    break
        
        if not page:
            print("에듀파인 페이지를 찾지 못했습니다.")
            return
            
        await page.bring_to_front()
        artifact_dir = r"C:\Users\user\.gemini\antigravity\brain\042b9ca2-8b35-4263-a331-c65b11186f02"
        
        print("네비게이션 시작!")
        success = await playwright_edufine.navigate_to_draft_page(page)
        
        print(f"네비게이션 결과: {success}")
        
        await page.screenshot(path=os.path.join(artifact_dir, "test_final_result.png"))
        print("스크린샷 저장 완료: test_final_result.png")

asyncio.run(main())
