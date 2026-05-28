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
        
        edit = page.locator("[id='mainframe.MainVFrameSet.TopFrame.form.cboJobList.comboedit']")
        box = await edit.bounding_box()
        if box:
            print('Clicking comboedit...')
            await page.mouse.click(box['x']+box['width']/2, box['y']+box['height']/2)
            await asyncio.sleep(1)
            
            items = await page.locator("[id^='mainframe.MainVFrameSet.TopFrame.form.cboJobList.combolist.item_']").all()
            for item in items:
                b = await item.bounding_box()
                txt = await item.inner_text()
                if b and b['x'] >= 0:
                    print(f"{await item.get_attribute('id')}: box={b}, txt={repr(txt)}")

asyncio.run(main())
