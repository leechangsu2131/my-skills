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
 if not target: raise RuntimeError('isolated NEIS tab not found')
 state=lambda: target.evaluate("""() => {
  const app=cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai=>ai&&ai.app&&ai.app.id==='app/com/main/Index');
  const b=app&&app.lookup('btn_allMenu'); const s=app&&app.lookup('siFindMenu');
  const inputs=Array.from(document.querySelectorAll('input[aria-label="메뉴검색"]')).map(e=>({visible:!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length),display:getComputedStyle(e).display}));
  return {buttonExists:!!b,buttonEnabled:b?b.enabled:null,buttonValue:b?b.value:null,searchControlExists:!!s,searchInputs:inputs};
 }""")
 before=state()
 target.evaluate("() => cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai=>ai&&ai.app&&ai.app.id==='app/com/main/Index').lookup('btn_allMenu').click()")
 target.wait_for_timeout(500)
 after=state()
 print(json.dumps({'tabUrl':target.url,'before':before,'after':after},ensure_ascii=False))
