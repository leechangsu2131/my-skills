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
        
        dropbtn = page.locator("[id='mainframe.MainVFrameSet.TopFrame.form.cboJobList.dropbutton']")
        box = await dropbtn.bounding_box()
        if box:
            print('Clicking dropbutton...')
            await page.mouse.click(box['x']+box['width']/2, box['y']+box['height']/2)
            await asyncio.sleep(1)
            
            items = await page.locator("text='학교회계'").all()
            found = False
            for item in items:
                b = await item.bounding_box()
                if b and b['x'] >= 0:
                    try:
                        print(f"Found visible: {await item.get_attribute('id')}, box={b}")
                    except:
                        print(f"Found visible: no-id, box={b}")
                    found = True
            
            if not found:
                print('No visible elements with text 학교회계 found!')

asyncio.run(main())
