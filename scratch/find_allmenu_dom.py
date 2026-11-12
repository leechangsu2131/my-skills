import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 target=None
 for c in b.contexts:
  for pg in c.pages:
   if 'gbe.neis.go.kr' in pg.url:
    try: ids=pg.evaluate("() => cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(ai=>ai&&ai.app&&ai.app.id).filter(Boolean)")
    except Exception: ids=[]
    if ids and not any('eds_' in x for x in ids): target=pg
 info=target.evaluate("""() => Array.from(document.querySelectorAll('body *')).filter(e=>(e.textContent||'').trim()==='▤').slice(0,20).map(e=>({tag:e.tagName,id:e.id,role:e.getAttribute('role'),aria:e.getAttribute('aria-label'),cls:String(e.className||'').slice(0,100),visible:!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length)}))""")
 print(json.dumps(info,ensure_ascii=False))
