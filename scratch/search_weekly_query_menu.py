import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 page=next(pg for c in b.contexts for pg in c.pages if 'gbe.neis.go.kr' in pg.url)
 search=page.locator('input[aria-label="메뉴검색"]')
 print(json.dumps({'count':search.count(),'visible':search.is_visible()},ensure_ascii=False))
 search.fill('주간학습안내조회')
 page.wait_for_timeout(700)
 loc=page.get_by_text('주간학습안내조회',exact=True)
 print(json.dumps({'matchCount':loc.count(),'visibleMatches':sum(1 for i in range(loc.count()) if loc.nth(i).is_visible())},ensure_ascii=False))
