const { chromium } = require('playwright');

const TARGET_URL = 'https://www.gurufocus.com/stock/ADBE/summary';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('Navigating to', TARGET_URL);
  
  try {
    await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    
    // Give it a moment to load dynamic content
    await page.waitForTimeout(5000);
    
    const title = await page.title();
    console.log('Title:', title);
    
    // Try to extract some key data points
    // Let's just grab the whole innerText of the main body to see what's there
    const text = await page.evaluate(() => document.body.innerText);
    
    // We'll write this text to a local file so we can inspect it without cluttering the console
    const fs = require('fs');
    fs.writeFileSync('C:\\Users\\lee21\\.gemini\\antigravity\\scratch\\my-skills\\skills\\personal-record-trade\\gurufocus_test.txt', text);
    
    console.log('Data successfully extracted and saved to gurufocus_test.txt. Text length:', text.length);
    
  } catch (e) {
    console.error('Error fetching page:', e);
  } finally {
    await browser.close();
  }
})();
