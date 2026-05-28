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
        
        print('Clicking comboedit...')
        await page.locator("[id='mainframe.MainVFrameSet.TopFrame.form.cboJobList.comboedit']").click(force=True)
        await asyncio.sleep(1)
        
        print('Clicking 학교회계...')
        # Use exact ID if possible, but let's try visible=true
        loc = page.locator("text='학교회계'").locator("visible=true")
        count = await loc.count()
        print('Visible items:', count)
        if count > 0:
            await loc.first.click(force=True)
            print('Clicked!')
            
asyncio.run(main())
