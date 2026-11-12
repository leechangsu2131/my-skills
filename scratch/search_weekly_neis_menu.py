import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 browser=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 page=next(pg for c in browser.contexts for pg in c.pages if pg.url=='https://gbe.neis.go.kr/jsp/main.jsp' and pg.locator('input[aria-label="메뉴검색"]').count()==1)
 page.evaluate("() => cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai=>ai&&ai.app&&ai.app.id==='app/com/main/Index').lookup('btn_allMenu').click()")
 search=page.locator('input[aria-label="메뉴검색"]')
 search.wait_for(state='visible',timeout=10000)
 search.fill('주간학습안내조회')
 page.wait_for_timeout(1000)
 matches=page.get_by_text('주간학습안내조회',exact=True)
 print(json.dumps({'searchVisible':search.is_visible(),'matchCount':matches.count(),'visibleMatches':sum(1 for i in range(matches.count()) if matches.nth(i).is_visible())},ensure_ascii=False))
