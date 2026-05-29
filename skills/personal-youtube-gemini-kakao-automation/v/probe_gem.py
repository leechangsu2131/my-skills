import asyncio
import os
import re

from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()
url = os.getenv("GEMINI_GEM_URL", "").split("?")[0]
gem_id = url.rstrip("/").split("/")[-1]
profile = os.getenv("PLAYWRIGHT_PROFILE_DIR", "./chrome_profile")


async def main() -> None:
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            profile, headless=False, channel="chrome"
        )
        page = await ctx.new_page()
        await page.goto(url, wait_until="load", timeout=60000)
        await page.wait_for_timeout(5000)
        print("after goto:", page.url)

        if "/gem/" not in page.url:
            await page.evaluate("(u) => { window.location.href = u; }", url)
            await page.wait_for_timeout(5000)
            print("after js nav:", page.url)

        candidates = [
            f"https://gemini.google.com/app/{gem_id}",
            f"https://gemini.google.com/gems/{gem_id}",
            f"https://gemini.google.com/gems/view/{gem_id}",
        ]
        for c in candidates:
            await page.goto(c, wait_until="load", timeout=60000)
            await page.wait_for_timeout(4000)
            print("try", c, "->", page.url)

        gems_url = "https://gemini.google.com/gems"
        await page.goto(gems_url, wait_until="load", timeout=60000)
        await page.wait_for_timeout(3000)
        print("gems page:", page.url)
        for sel in [
            f'a[href*="{gem_id}"]',
            '[data-test-id*="gem"]',
            "mat-card",
            "button",
        ]:
            loc = page.locator(sel)
            print(sel, await loc.count())

        # try open Gems from app sidebar
        await page.goto("https://gemini.google.com/app", wait_until="load")
        await page.wait_for_timeout(3000)
        gems_btn = page.locator('a[href*="/gems"], button:has-text("Gems"), button:has-text("젬")')
        print("gems btn count", await gems_btn.count())
        if await gems_btn.count() > 0:
            await gems_btn.first.click()
            await page.wait_for_timeout(4000)
            print("after gems btn:", page.url)

        await page.wait_for_timeout(5000)
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
