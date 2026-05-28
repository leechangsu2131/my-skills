import asyncio
import os
from playwright.async_api import async_playwright

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
            print("에듀파인 페이지 없음")
            return
            
        await page.bring_to_front()
        artifact_dir = r"C:\Users\user\.gemini\antigravity\brain\042b9ca2-8b35-4263-a331-c65b11186f02"
        
        # 1. 시스템 메뉴 (업무관리) 클릭 시도
        # 업무관리 텍스트의 부모를 찾아본다
        print("시스템 메뉴 클릭 시도...")
        await page.mouse.move(90, 20, steps=10)
        await asyncio.sleep(1)
        await page.screenshot(path=os.path.join(artifact_dir, "test_hover_sys.png"))
        
        await page.mouse.click(90, 20)
        await asyncio.sleep(1.5)
        await page.screenshot(path=os.path.join(artifact_dir, "test_click_sys.png"))
        
        # 2. 학교회계 클릭 시도 (드롭다운 열렸다고 가정)
        print("학교회계 클릭 시도...")
        await page.mouse.move(90, 60, steps=10)
        await asyncio.sleep(1)
        await page.screenshot(path=os.path.join(artifact_dir, "test_hover_acct.png"))
        
        await page.mouse.click(90, 60)
        await asyncio.sleep(3)
        await page.screenshot(path=os.path.join(artifact_dir, "test_click_acct.png"))
        
        print("테스트 완료")

if __name__ == "__main__":
    asyncio.run(main())
