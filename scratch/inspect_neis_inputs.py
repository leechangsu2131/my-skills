import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 browser=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 page=next(pg for c in browser.contexts for pg in c.pages if 'gbe.neis.go.kr/jsp/main.jsp' in pg.url)
 inputs=page.locator('input')
 rows=[]
 for i in range(inputs.count()):
  el=inputs.nth(i)
  try:
   rows.append({'index':i,'id':el.get_attribute('id'),'type':el.get_attribute('type'),'placeholder':el.get_attribute('placeholder'),'aria':el.get_attribute('aria-label'),'visible':el.is_visible()})
  except Exception: pass
 print(json.dumps(rows,ensure_ascii=False))
