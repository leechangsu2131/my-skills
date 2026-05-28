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
                    
        await page.bring_to_front()
        artifact_dir = r"C:\Users\user\.gemini\antigravity\brain\042b9ca2-8b35-4263-a331-c65b11186f02"
        
        cbo = page.locator("[id='mainframe.MainVFrameSet.TopFrame.form.cboJobList']")
        box = await cbo.bounding_box()
        print("cboJobList bounding box:", box)
        
        if box:
            print("콤보박스 클릭!")
            await page.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            await asyncio.sleep(1)
            await page.screenshot(path=os.path.join(artifact_dir, "test_click_cbo.png"))
            
            # 학교회계 아이템 찾기
            item = page.locator("[id='mainframe.MainVFrameSet.TopFrame.form.cboJobList.combolist.item_2']")
            item_box = await item.bounding_box()
            print("item_2 bounding box:", item_box)
            
            if item_box and item_box["x"] >= 0:
                print("학교회계 아이템 클릭!")
                await page.mouse.click(item_box["x"] + item_box["width"]/2, item_box["y"] + item_box["height"]/2)
                await asyncio.sleep(4)
                await page.screenshot(path=os.path.join(artifact_dir, "test_click_cbo_item.png"))
            else:
                print("item_box 가 안보임, js로 combolist 내부 뒤지기")

asyncio.run(main())
