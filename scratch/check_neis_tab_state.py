import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 out=[]
 for c in b.contexts:
  for pg in c.pages:
   if 'gbe.neis.go.kr' in pg.url:
    out.append({'url':pg.url,'title':pg.title(),'inputs':pg.locator('input').evaluate_all("els => els.map(e=>({aria:e.getAttribute('aria-label'),visible:!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length)}))")})
 print(json.dumps(out,ensure_ascii=False))
