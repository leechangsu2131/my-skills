import sys
import os
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

def run_playwright_extraction(ticker: str) -> str:
    # Playwright skill path
    playwright_dir = ROOT.parent.parent.parent / "antigravity-awesome-skills" / "skills" / "playwright-skill"
    run_js_path = playwright_dir / "run.js"
    
    if not run_js_path.exists():
        print(f"[{ticker}] Playwright 스킬 경로를 찾을 수 없습니다: {run_js_path}")
        return ""

    # Generate a temporary script for this ticker
    url = f"https://www.financecharts.com/stocks/{ticker}/all-metrics"
    
    temp_script_path = playwright_dir / f"temp_fc_{ticker}.js"
    
    script_content = f"""
const {{ chromium }} = require('playwright');
const path = require('path');
(async () => {{
  const browser = await chromium.launch({{
    headless: false,
    slowMo: 50,
    args: ['--disable-blink-features=AutomationControlled']
  }});
  const context = await browser.newContext({{
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  }});
  const page = await context.newPage();
  
  // Override webdriver property
  await page.addInitScript(() => {{
    Object.defineProperty(navigator, 'webdriver', {{
      get: () => undefined
    }});
  }});
  
  try {{
    console.log("Navigating to URL...");
    await page.goto('{url}', {{ waitUntil: 'domcontentloaded', timeout: 90000 }});
    
    // Check if we are on the Cloudflare challenge / Submit page
    await page.waitForTimeout(5000);
    const submitBtn = await page.$('text=Submit');
    if (submitBtn) {{
      console.log("Found Submit button. Clicking it to bypass automatic submission failure...");
      await page.click('text=Submit');
      await page.waitForTimeout(5000);
    }}
    
    console.log("Waiting for PE RATIO to appear...");
    await page.waitForSelector('text=PE RATIO', {{ timeout: 60000 }}).catch(async () => {{
      // Try clicking Submit again if it appeared late
      const btn = await page.$('text=Submit');
      if (btn) {{
        console.log("Found Submit button during wait. Clicking it...");
        await page.click('text=Submit');
        await page.waitForTimeout(5000);
      }}
    }});
    
    await page.waitForTimeout(5000); // Give it a bit more time to render
    const text = await page.evaluate(() => document.body.innerText);
    console.log(text);
  }} catch (e) {{
    console.error('Error:', e);
  }} finally {{
    await browser.close();
  }}
}})();
"""
    with open(temp_script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    print(f"[{ticker}] FinanceCharts 데이터 추출 시작: {url}")
    print(f"[{ticker}] Playwright 스킬 실행 중 (브라우저가 열릴 수 있습니다)...")
    
    try:
        # Run the script using node directly
        result = subprocess.run(
            ["node", str(temp_script_path)],
            cwd=str(playwright_dir),
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result.stdout
    except Exception as e:
        print(f"[{ticker}] 봇 실행 중 오류 발생: {e}")
        return ""
    finally:
        # Cleanup
        if temp_script_path.exists():
            pass # temp_script_path.unlink()

def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline/ingest_financecharts.py <TICKER>")
        sys.exit(1)
        
    ticker = sys.argv[1].upper()
    text = run_playwright_extraction(ticker)
    
    with open(ROOT / "scratch" / f"fc_debug_raw_{ticker}.txt", "w", encoding="utf-8") as f:
        f.write(text)
        
    if not text.strip():
        print(f"[{ticker}] 추출된 텍스트가 없습니다. Cloudflare 차단이거나 페이지 로드 실패일 수 있습니다.")
        sys.exit(1)
        
    data = {}
    
    def extract_val(pattern):
        match = re.search(pattern, text)
        if match:
            val_str = match.group(1).replace(',', '').replace('%', '')
            try:
                return float(val_str)
            except ValueError:
                return None
        return None
        
    data["pe_ratio"] = extract_val(r'PE RATIO\n([0-9,.-]+)')
    data["pe_ratio_fwd"] = extract_val(r'PE RATIO \(FWD\)\n([0-9,.-]+)')
    data["ps_ratio"] = extract_val(r'PS RATIO\n([0-9,.-]+)')
    data["pb_ratio"] = extract_val(r'PB RATIO\n([0-9,.-]+)')
    data["ev_ebitda"] = extract_val(r'EV/EBITDA RATIO\n([0-9,.-]+)')
    
    data["pe_ratio_avg_3y"] = extract_val(r'PE RATIO AVG 3Y\n([0-9,.-]+)')
    data["pe_current_vs_3y_avg"] = extract_val(r'CURRENT VS 3Y AVG\n([0-9,.-]+)%') # We want the % value. Note: There are multiple "CURRENT VS 3Y AVG" in the page (for PS, PB, etc). The first one after PE RATIO is usually PE's.
    
    # Better to be precise for CURRENT VS 3Y AVG of PE Ratio
    pe_section_match = re.search(r'PE RATIO AVG 3Y[\s\S]*?CURRENT VS 3Y AVG\n([0-9,.-]+)%', text)
    if pe_section_match:
        data["pe_current_vs_3y_avg"] = float(pe_section_match.group(1).replace(',', ''))
        
    data["fair_value_price_fcf"] = extract_val(r'FAIR VALUE PRICE \(FCF\)\n\$?([0-9,.-]+)')
    data["margin_of_safety_fcf"] = extract_val(r'MARGIN OF SAFETY \(FCF\)\n([0-9,.-]+)%')
    data["roic"] = extract_val(r'ROIC\n([0-9,.-]+)%?')
    
    print(f"[{ticker}] 추출 완료: {data}")
    
    # JSON 저장
    out_dir = ROOT / "data" / "financecharts_context"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ticker}.json"
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print(f"[{ticker}] 저장 완료: {out_path.relative_to(ROOT)}")
    
    try:
        from pipeline.layer1_store import save_row
        fc_data = {}
        if data.get("pe_ratio"):
            fc_data["pe_ratio"] = data["pe_ratio"]
        if data.get("pe_ratio_fwd"):
            fc_data["fwd_pe_fy"] = data["pe_ratio_fwd"]
        if data.get("ps_ratio"):
            fc_data["ps_ratio"] = data["ps_ratio"]
        if data.get("pb_ratio"):
            fc_data["pb_ratio"] = data["pb_ratio"]
        if data.get("ev_ebitda"):
            fc_data["ev_ebitda"] = data["ev_ebitda"]
        if data.get("pe_ratio_avg_3y"):
            fc_data["pe_avg_3y"] = data["pe_ratio_avg_3y"]
        if data.get("pe_current_vs_3y_avg") is not None:
            fc_data["pe_vs_3y"] = data["pe_current_vs_3y_avg"]
        if data.get("fair_value_price_fcf"):
            fc_data["fair_value"] = data["fair_value_price_fcf"]
        if data.get("margin_of_safety_fcf"):
            fc_data["mos"] = data["margin_of_safety_fcf"]
        if data.get("roic") is not None:
            fc_data["roic"] = data["roic"]
        if fc_data:
            save_row(ticker, "financecharts", fc_data)
    except Exception as e:
        print(f"Layer 1 저장 실패: {e}")

if __name__ == "__main__":
    main()
