import asyncio
import os
from playwright.async_api import async_playwright

async def click_visible_text(page, text):
    print(f"'{text}' 텍스트 요소 찾는 중...")
    frames_to_check = [page] + page.frames
    for frame in frames_to_check:
        try:
            locs = await frame.locator(f"text='{text}'").all()
            for loc in locs:
                box = await loc.bounding_box()
                if box and box['width'] > 0 and box['x'] >= 0:
                    print(f"'{text}' 클릭! 좌표: {box}")
                    await page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2, steps=10)
                    await asyncio.sleep(0.3)
                    await page.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                    return True
        except Exception as e:
            pass
    print(f"'{text}' 요소를 찾지 못했습니다.")
    return False

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        page = None
        for ctx in browser.contexts:
            for p_idx in ctx.pages:
                if "klef" in p_idx.url.lower():
                    page = p_idx
                    break
                    
        await page.bring_to_front()
        artifact_dir = r"C:\Users\user\.gemini\antigravity\brain\042b9ca2-8b35-4263-a331-c65b11186f02"
        
        # 1. 사업담당 클릭
        clicked = await click_visible_text(page, "사업담당")
        if clicked:
            await asyncio.sleep(2)
            await page.screenshot(path=os.path.join(artifact_dir, "test_menu_1.png"))
            
        # 2. 품의/정산 클릭
        clicked = await click_visible_text(page, "품의/정산")
        if clicked:
            await asyncio.sleep(2)
            await page.screenshot(path=os.path.join(artifact_dir, "test_menu_2.png"))
            
        # 3. 품의등록 클릭
        clicked = await click_visible_text(page, "품의등록")
        if clicked:
            await asyncio.sleep(3)
            await page.screenshot(path=os.path.join(artifact_dir, "test_menu_3.png"))

asyncio.run(main())
