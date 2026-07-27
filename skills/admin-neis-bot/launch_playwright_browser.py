#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import os

os.environ["no_proxy"] = "localhost,127.0.0.1"

async def main():
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser_context = await pw.chromium.launch_persistent_context(
        user_data_dir=r"C:\Users\lee21\AppData\Local\Temp\neis_chrome_profile_9222",
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        headless=False,
        no_viewport=True,
        args=["--start-maximized", "--remote-debugging-port=9222"]
    )
    print("Playwright launched Chrome with port 9222!")
    page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
    await page.goto("https://evpn.gbe.kr")
    print("Page navigated to https://evpn.gbe.kr")
    # 24시간 상시 유지 대기
    await asyncio.sleep(86400)

if __name__ == "__main__":
    asyncio.run(main())
