import asyncio
from playwright.async_api import async_playwright
import re
import sys

current_items_text = """
다우리 뉴좌전굴 허리 유연성 측정기 신체검사 학교체육		2		170500
프로스펙스 디지털 악력계 전자식 악력 측정기 악력기		2		26900
아이워너 초시계 스톱워치		2		32500
"""

async def add_draft_row(page):
    btns = await page.locator("text='행추가'").all()
    target_btn = None
    for btn in btns:
        if await btn.is_visible():
            b = await btn.bounding_box()
            if b and b['y'] > 300:
                target_btn = btn
                break
    if target_btn:
        b = await target_btn.bounding_box()
        await page.mouse.click(b['x'] + b['width']/2, b['y'] + b['height']/2)

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
        
        parsed_items = []
        current_item = None
        for line in current_items_text.strip().split('\n'):
            line = line.strip()
            if not line: continue
            clean_line = re.sub(r'^[-*•]\s*', '', line)
            if '	' in clean_line:
                parts = clean_line.split('	')
                parts = [p.strip() for p in parts if p.strip()]
                if len(parts) >= 3:
                    parsed_items.append({'name': parts[0], 'quantity': int(parts[1].replace(',','')), 'unit_price': int(parts[2].replace(',',''))})
        
        print(f"Parsed {len(parsed_items)} items.")
        
        for i, c_item in enumerate(parsed_items):
            print(f"-> Adding item: {c_item['name']}, qty: {c_item['quantity']}, price: {c_item['unit_price']}")
            await add_draft_row(page)
            await page.wait_for_timeout(500)
            
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(200)
            await page.keyboard.type(c_item['name'])
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(200)
            
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(100)
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(200)
            
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(200)
            await page.keyboard.type(str(c_item['quantity']))
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(200)
            
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(200)
            
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(200)
            await page.keyboard.type(str(c_item['unit_price']))
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(200)
            
            await page.wait_for_timeout(500)
            
        await page.screenshot(path="C:\\Users\\user\\.gemini\\antigravity\\brain\\042b9ca2-8b35-4263-a331-c65b11186f02\\test_s2b_rows.png")
        print("Done, screenshot saved to test_s2b_rows.png")

asyncio.run(main())
