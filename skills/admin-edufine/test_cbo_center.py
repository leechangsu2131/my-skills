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
        
        cbo = page.locator("[id='mainframe.MainVFrameSet.TopFrame.form.cboJobList']")
        box = await cbo.bounding_box()
        if box:
            print('Clicking center of cboJobList:', box['x'] + 50)
            await page.mouse.click(box['x'] + 50, box['y'] + box['height']/2)
            await asyncio.sleep(1)
            
            acct_items = await page.locator("[id^='mainframe.MainVFrameSet.TopFrame.form.cboJobList.combolist.item_']:has-text('학교회계')").all()
            found = False
            for item in acct_items:
                b = await item.bounding_box()
                if b and b['x'] >= 0:
                    print('Visible item found:', b)
                    found = True
            if not found:
                print('No visible items found')

asyncio.run(main())
