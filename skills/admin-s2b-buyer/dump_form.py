import asyncio
import os
import sys
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

async def dump_search_form():
    load_dotenv(os.path.join(SCRIPT_DIR, '.env'))
    uid = os.getenv('S2B_USER_ID')
    pwd = os.getenv('S2B_USER_PW')

    from playwright.async_api import async_playwright
    from s2b_login import login as s2b_login

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(viewport={'width': 1280, 'height': 900}, locale='ko-KR')
        page = await context.new_page()

        await s2b_login(page, uid, pwd)
        
        search_url = "https://www.s2b.kr/S2BNCustomer/S2B/scrweb/remu/rema/searchengine/s2bCustomerSearch.jsp?actionType=MAIN_SEARCH&searchQuery=202604067720487"
        await page.goto(search_url, timeout=30000)
        await page.wait_for_timeout(3000)
        
        html = await page.content()
        with open('search_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("--- HTML saved to search_page.html ---")
        
        await browser.close()

if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace') if hasattr(sys, 'stdout') and hasattr(sys.stdout, 'buffer') else sys.stdout
    asyncio.run(dump_search_form())
