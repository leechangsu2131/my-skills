import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://localhost:9222')
        page = None
        for ctx in browser.contexts:
            for p_idx in ctx.pages:
                if 'klef' in p_idx.url.lower():
                    page = p_idx
                    break
        
        await page.bring_to_front()
        # Dropbutton click
        dropbtn = page.locator("[id='mainframe.MainVFrameSet.TopFrame.form.cboJobList.dropbutton']")
        box = await dropbtn.bounding_box()
        if box:
            await page.mouse.click(box['x']+box['width']/2, box['y']+box['height']/2)
            await asyncio.sleep(1)
        
        acct_items = await page.locator("[id^='mainframe.MainVFrameSet.TopFrame.form.cboJobList.combolist.item_']:has-text('학교회계')").all()
        for item in acct_items:
            b = await item.bounding_box()
            print(f"Item: {await item.get_attribute('id')}, box={b}")
            
        print("Now looping through all items to find 학교회계 manually...")
        items = await page.locator("[id^='mainframe.MainVFrameSet.TopFrame.form.cboJobList.combolist.item_']").all()
        for item in items:
            txt = await item.inner_text()
            b = await item.bounding_box()
            # print(f"{await item.get_attribute('id')}: {txt!r}")
            if "학교회계" in txt:
                print(f"Found manually: {await item.get_attribute('id')}, box={b}")

asyncio.run(main())
