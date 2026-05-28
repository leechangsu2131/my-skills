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
        
        # 1. 콤보박스 열기
        dropbtn = page.locator("[id='mainframe.MainVFrameSet.TopFrame.form.cboJobList.dropbutton']")
        box = await dropbtn.bounding_box()
        if box:
            print("드롭버튼 클릭")
            await page.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            await asyncio.sleep(1)
            await page.screenshot(path=os.path.join(artifact_dir, "test_dropdown_open.png"))
            
            # 모든 아이템의 bounding_box 출력
            items = await page.locator("[id^='mainframe.MainVFrameSet.TopFrame.form.cboJobList.combolist.item_']").all()
            for i, item in enumerate(items):
                b = await item.bounding_box()
                txt = await item.inner_text()
                print(f"Item {i}: text={repr(txt)}, box={b}")
                
            # 학교회계를 has-text로 찾아 클릭
            acct_item = page.locator("[id^='mainframe.MainVFrameSet.TopFrame.form.cboJobList.combolist.item_']:has-text('학교회계')").first
            b = await acct_item.bounding_box()
            if b:
                print(f"학교회계 클릭 좌표: {b}")
                await page.mouse.click(b["x"] + b["width"]/2, b["y"] + b["height"]/2)
                await asyncio.sleep(2)
                await page.screenshot(path=os.path.join(artifact_dir, "test_after_click.png"))
        else:
            print("dropbutton 못찾음")

asyncio.run(main())
