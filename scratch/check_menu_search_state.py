import json,sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 for c in b.contexts:
  for pg in c.pages:
   if 'gbe.neis.go.kr' in pg.url:
    pg.set_default_timeout(2000)
    print(json.dumps({'url':pg.url,'searchCount':pg.locator('input[aria-label="메뉴검색"]').count(),'searchVisible':pg.locator('input[aria-label="메뉴검색"]').is_visible(),'weeklyMatches':pg.get_by_text('주간학습안내조회',exact=True).count()},ensure_ascii=False))
