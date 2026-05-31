const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 50 });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  const page = await context.newPage();

  const urls = [
    'https://www.financecharts.com/stocks/NVDA/dcf-calculator',
    'https://www.financecharts.com/stocks/NVDA/all-metrics'
  ];
  
  let allText = '';
  
  try {
    for (const url of urls) {
      console.log('Navigating to', url);
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(5000); // Wait for CF or lazy loads
      const text = await page.evaluate(() => document.body.innerText);
      allText += `\n\n=== ${url} ===\n\n` + text;
    }
    
    fs.writeFileSync('C:\\Users\\lee21\\.gemini\\antigravity\\scratch\\my-skills\\skills\\personal-record-trade\\financecharts_test.txt', allText);
    console.log('Data successfully extracted and saved. Length:', allText.length);
  } catch (e) {
    console.error('Error fetching page:', e);
  } finally {
    await browser.close();
  }
})();
