const { chromium } = require('playwright');
const fs = require('fs');

const TARGET_URL = 'https://www.gurufocus.com/stock/ADBE/summary';

(async () => {
  // Use non-headless mode to try to bypass Cloudflare
  const browser = await chromium.launch({ headless: false, slowMo: 50 });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  const page = await context.newPage();

  console.log('Navigating to', TARGET_URL);
  
  try {
    // We increase timeout to allow time for Cloudflare challenge if it appears
    await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
    
    // Wait for the specific element that indicates the page has loaded successfully
    // e.g., the stock ticker title, or just wait for 10 seconds for CF to pass
    console.log('Waiting 10 seconds for Cloudflare challenge to potentially resolve...');
    await page.waitForTimeout(10000);
    
    const title = await page.title();
    console.log('Title:', title);
    
    // Attempt to extract specific metrics
    // GF Value, Financial Strength, Profitability Rank, Piotroski F-Score, Altman Z-Score
    
    // Evaluate in browser context to get text
    const extractedData = await page.evaluate(() => {
      const data = {
        title: document.title,
        text: document.body.innerText,
        html: document.body.innerHTML
      };
      return data;
    });
    
    fs.writeFileSync('C:\\Users\\lee21\\.gemini\\antigravity\\scratch\\my-skills\\skills\\personal-record-trade\\gurufocus_test2.txt', extractedData.text);
    console.log('Data successfully extracted and saved. Length:', extractedData.text.length);
    
    if (title.includes('Attention Required') || title.includes('Cloudflare')) {
        console.log('STILL BLOCKED BY CLOUDFLARE');
    }
    
  } catch (e) {
    console.error('Error fetching page:', e);
  } finally {
    await browser.close();
  }
})();
