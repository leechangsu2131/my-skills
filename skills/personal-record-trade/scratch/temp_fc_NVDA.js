
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 50 });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  const page = await context.newPage();
  
  try {
    await page.goto('https://www.financecharts.com/stocks/NVDA/all-metrics', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000); // Wait for CF or lazy loads
    const text = await page.evaluate(() => document.body.innerText);
    console.log(text);
  } catch (e) {
    console.error('Error:', e);
  } finally {
    await browser.close();
  }
})();
