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
        
        btns = await page.locator("text='행추가'").all()
        target_btn = None
        for btn in btns:
            b = await btn.bounding_box()
            if b and b['y'] > 300: # Ensure it's the bottom grid
                target_btn = btn
                break
                
        if target_btn:
            b = await target_btn.bounding_box()
            print('Clicking 행추가 at', b)
            await page.mouse.click(b['x'] + b['width']/2, b['y'] + b['height']/2)
            await asyncio.sleep(1)
            
            # Now try to type
            print('Pressing Enter to edit name...')
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.5)
            await page.keyboard.type("테스트물품")
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.5)
            
            print('Tabbing to quantity...')
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.2)
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.2)
            
            print('Entering quantity...')
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.2)
            await page.keyboard.type("5")
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.2)
            
            print('Tabbing to price...')
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.2)
            
            print('Entering price...')
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.2)
            await page.keyboard.type("15000")
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.5)
            
            await page.screenshot(path="C:\\Users\\user\\.gemini\\antigravity\\brain\\042b9ca2-8b35-4263-a331-c65b11186f02\\test_row_added.png")
            print('Done, screenshot saved.')

asyncio.run(main())
