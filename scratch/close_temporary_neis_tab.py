import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 closed=0; remaining=[]
 for c in b.contexts:
  for pg in list(c.pages):
   if pg.url!='https://gbe.neis.go.kr/jsp/main.jsp': continue
   try: ids=pg.evaluate("() => cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(ai=>ai&&ai.app&&ai.app.id).filter(Boolean)")
   except Exception: ids=[]
   if set(ids)=={'app/com/main/Index','app/com/main/Dashboard3','udc/com/udcCal02'}:
    pg.close(); closed+=1
  for i,pg in enumerate(c.pages):
   ids=[]
   if 'gbe.neis.go.kr' in pg.url:
    try: ids=pg.evaluate("() => cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(ai=>ai&&ai.app&&ai.app.id).filter(Boolean)")
    except Exception: pass
   remaining.append({'context':len(remaining),'page':i,'url':pg.url,'appIds':ids})
 print(json.dumps({'closedTemporaryTabs':closed,'remaining':remaining},ensure_ascii=False))
