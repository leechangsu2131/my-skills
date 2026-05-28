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
        
        locs = await page.locator("text='조회 결과가 없습니다.'").all()
        print('Empty messages count:', len(locs))
        for loc in locs:
            if await loc.is_visible():
                box = await loc.bounding_box()
                if box:
                    print('Visible Empty message at:', box)
        
        bgt_btn = await page.locator("text='예산선택'").first.bounding_box()
        print('예산선택 button box:', bgt_btn)

asyncio.run(main())
