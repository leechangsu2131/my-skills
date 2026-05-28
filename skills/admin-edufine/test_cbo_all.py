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
        
        cbos = await page.locator("[id*='cbo']").all()
        for c in cbos:
            try:
                b = await c.bounding_box()
                if b and b['x'] >= 0:
                    print(f"{await c.get_attribute('id')}: {b}")
            except: pass

asyncio.run(main())
