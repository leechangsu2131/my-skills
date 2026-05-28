import asyncio
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
        
        # 학교회계 아이템 찾기
        item = page.locator("[id^='mainframe.MainVFrameSet.TopFrame.form.cboJobList.combolist.item_']:has-text('학교회계')")
        count = await item.count()
        print('Found items:', count)
        if count > 0:
            id_val = await item.first.get_attribute('id')
            print('ID:', id_val)
            
asyncio.run(main())
