import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 for ci,c in enumerate(b.contexts):
  for i,pg in enumerate(c.pages):
   apps=[]
   if 'gbe.neis.go.kr' in pg.url:
    try: apps=pg.evaluate("() => cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(ai=>ai&&ai.app&&ai.app.id).filter(Boolean)")
    except Exception: pass
   print(json.dumps({'context':ci,'page':i,'url':pg.url,'title':pg.title(),'appIds':apps},ensure_ascii=False))
