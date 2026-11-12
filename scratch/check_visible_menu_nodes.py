import json,sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 pg=next(pg for c in b.contexts for pg in c.pages if 'gbe.neis.go.kr' in pg.url); pg.set_default_timeout(1500)
 result=[]
 for name in ['교육과정','주간학습안내조회','주간학습안내작성']:
  loc=pg.get_by_text(name,exact=True); n=loc.count(); result.append({'text':name,'count':n,'visible':sum(1 for i in range(n) if loc.nth(i).is_visible())})
 print(json.dumps(result,ensure_ascii=False))
