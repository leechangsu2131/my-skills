import os
import sys
import json
import subprocess
import re
from pathlib import Path

# Windows cp949 인코딩 오류 방지
if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

GURUFOCUS_CONTEXT_DIR = ROOT / "data" / "gurufocus_context"
GURUFOCUS_CONTEXT_DIR.mkdir(parents=True, exist_ok=True)

PLAYWRIGHT_SKILL_DIR = Path("C:/Users/lee21/.gemini/antigravity/scratch/antigravity-awesome-skills/skills/playwright-skill")

def ingest_gurufocus(ticker: str):
    """
    Playwright-skill을 이용하여 GuruFocus 페이지를 스크래핑하고 데이터를 추출합니다.
    """
    url = f"https://www.gurufocus.com/stock/{ticker}/summary"
    print(f"[{ticker}] GuruFocus 데이터 추출 시작: {url}")
    
    # 임시 Playwright JS 스크립트 작성
    temp_js_path = ROOT / f"temp_playwright_{ticker}.js"
    temp_out_path = ROOT / f"temp_gurufocus_{ticker}.txt"
    
    # 윈도우 경로를 JS 포맷에 맞게 이스케이프
    out_path_js = str(temp_out_path).replace("\\", "\\\\")
    
    js_content = f"""
const {{ chromium }} = require('playwright');
const fs = require('fs');

const TARGET_URL = '{url}';

(async () => {{
  const browser = await chromium.launch({{ headless: false, slowMo: 50 }});
  const context = await browser.newContext({{
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  }});
  const page = await context.newPage();

  try {{
    await page.goto(TARGET_URL, {{ waitUntil: 'domcontentloaded', timeout: 60000 }});
    // Cloudflare 챌린지 통과를 위한 대기
    await page.waitForTimeout(10000);
    
    const text = await page.evaluate(() => document.body.innerText);
    fs.writeFileSync('{out_path_js}', text);
  }} catch (e) {{
    console.error('Error fetching page:', e);
  }} finally {{
    await browser.close();
  }}
}})();
"""
    
    temp_js_path.write_text(js_content, encoding='utf-8')
    
    # Playwright 스킬 실행
    print(f"[{ticker}] Playwright 스킬 실행 중 (브라우저가 열릴 수 있습니다)...")
    try:
        subprocess.run(
            ["node", "run.js", str(temp_js_path)],
            cwd=str(PLAYWRIGHT_SKILL_DIR),
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
    except subprocess.CalledProcessError as e:
        print(f"[{ticker}] Playwright 실행 실패:\n{e.stderr}")
        return
    finally:
        if temp_js_path.exists():
            temp_js_path.unlink()
            
    # 추출된 텍스트 파싱
    if not temp_out_path.exists():
        print(f"[{ticker}] 결과 텍스트 파일이 생성되지 않았습니다.")
        return
        
    text = temp_out_path.read_text(encoding='utf-8')
    Path('data/gf_raw_text.txt').write_text(text, encoding='utf-8'); temp_out_path.unlink()
    
    if "Attention Required!" in text or "Cloudflare" in text[:500]:
        print(f"[{ticker}] Cloudflare 봇 차단에 걸렸습니다. 데이터를 추출할 수 없습니다.")
        return
        
    # 파싱 로직 (정규식 활용)
    data = {}
    
    # GF Value 추출 예: "GF Value™: $632.51"
    gf_match = re.search(r'GF Value(?:™)?:\s*\$([0-9,.]+)', text)
    if gf_match:
        data["gf_value"] = float(gf_match.group(1).replace(',', ''))
        
    # Financial Strength 추출 예: "Financial Strength\n8/10"
    fs_match = re.search(r'Financial Strength\s*([0-9]+)/10', text)
    if fs_match:
        data["financial_strength"] = int(fs_match.group(1))
        
    # Profitability Rank 추출 예: "Profitability Rank\n10/10"
    pr_match = re.search(r'Profitability Rank\s*([0-9]+)/10', text)
    if pr_match:
        data["profitability_rank"] = int(pr_match.group(1))
        
    # Piotroski F-Score 추출 예: "Piotroski F-Score\n8/9"
    fscore_match = re.search(r'Piotroski F-Score\s*([0-9]+)/9', text)
    if fscore_match:
        data["piotroski_f_score"] = int(fscore_match.group(1))
        
    # Altman Z-Score 추출 예: "Altman Z-Score\n7.47"
    zscore_match = re.search(r'Altman Z-Score\s*([0-9,.-]+)', text)
    if zscore_match:
        try:
            data["altman_z_score"] = float(zscore_match.group(1).replace(',', ''))
        except ValueError:
            pass
            
    # ROIC % 추출 예: "ROIC %\n\t\n25.69"
    roic_match = re.search(r'ROIC %\s+([0-9,.-]+)', text)
    if roic_match:
        try:
            data["roic_pct"] = float(roic_match.group(1).replace(',', ''))
        except ValueError:
            pass
            
    # FCF Margin % 추출 예: "FCF Margin %\n\t\n42.19"
    fcf_margin_match = re.search(r'FCF Margin %\s+([0-9,.-]+)', text)
    if fcf_margin_match:
        try:
            data["fcf_margin_pct"] = float(fcf_margin_match.group(1).replace(',', ''))
        except ValueError:
            pass
            
    # Operating Margin % 추출 예: "Operating Margin %\n\t\n64.02"
    op_margin_match = re.search(r'Operating Margin %\s+([0-9,.-]+)', text)
    if op_margin_match:
        try:
            data["op_margin_pct"] = float(op_margin_match.group(1).replace(',', ''))
        except ValueError:
            pass
            
    # EV-to-FCF 추출 예: "EV-to-FCF\n\t\n10.13"
    ev_fcf_match = re.search(r'EV-to-FCF\s+([0-9,.-]+)', text)
    if ev_fcf_match:
        try:
            data["ev_to_fcf"] = float(ev_fcf_match.group(1).replace(',', ''))
        except ValueError:
            pass
            
    # 3-Year ROIIC % 추출 예: "3-Year ROIIC %\n\t\n66.5"
    roiic_match = re.search(r'3-Year ROIIC %\s+([0-9,.-]+)', text)
    if roiic_match:
        try:
            data["roiic_3y_pct"] = float(roiic_match.group(1).replace(',', ''))
        except ValueError:
            pass
            
    # Valuation Ratios
    pe_match = re.search(r'PE Ratio\s+([0-9,.-]+)', text)
    if pe_match:
        try: data["pe_ratio"] = float(pe_match.group(1).replace(',', ''))
        except ValueError: pass

    fwd_pe_match = re.search(r'Forward PE Ratio\s+([0-9,.-]+)', text)
    if fwd_pe_match:
        try: data["fwd_pe_fy"] = float(fwd_pe_match.group(1).replace(',', ''))
        except ValueError: pass

    ps_match = re.search(r'PS Ratio\s+([0-9,.-]+)', text)
    if ps_match:
        try: data["ps_ratio"] = float(ps_match.group(1).replace(',', ''))
        except ValueError: pass

    pb_match = re.search(r'PB Ratio\s+([0-9,.-]+)', text)
    if pb_match:
        try: data["pb_ratio"] = float(pb_match.group(1).replace(',', ''))
        except ValueError: pass

    ev_ebitda_match = re.search(r'EV-to-EBITDA\s+([0-9,.-]+)', text)
    if ev_ebitda_match:
        try: data["ev_ebitda"] = float(ev_ebitda_match.group(1).replace(',', ''))
        except ValueError: pass

    print(f"[{ticker}] 추출 완료: {data}")
    
    # JSON 저장
    out_json = GURUFOCUS_CONTEXT_DIR / f"{ticker}.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print(f"[{ticker}] 저장 완료: {out_json.relative_to(ROOT)}")

    try:
        from pipeline.layer1_store import save_row
        gf_data = {}
        field_map = {
            "gf_value": "fair_value",
            "financial_strength": "fin_strength",
            "profitability_rank": "profit_rank",
            "piotroski_f_score": "piotroski",
            "altman_z_score": "altman_z",
            "roic_pct": "roic",
            "fcf_margin_pct": "fcf_margin",
            "op_margin_pct": "op_margin",
            "ev_to_fcf": "ev_fcf",
            "roiic_3y_pct": "roiic_3y",
            "pe_ratio": "pe_ratio",
            "fwd_pe_fy": "fwd_pe_fy",
            "ps_ratio": "ps_ratio",
            "pb_ratio": "pb_ratio",
            "ev_ebitda": "ev_ebitda",
        }
        for src_key, dest_key in field_map.items():
            if src_key in data and data[src_key] is not None:
                gf_data[dest_key] = data[src_key]
        if gf_data:
            save_row(ticker, "gurufocus", gf_data)
    except Exception as e:
        print(f"Layer 1 저장 실패: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker", help="분석할 주식 티커 (예: ADBE)")
    args = parser.parse_args()
    
    ingest_gurufocus(args.ticker)
