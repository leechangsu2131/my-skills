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
 out=target.evaluate("""() => {const a=cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai=>ai&&ai.app&&ai.app.id==='app/com/main/Index'); const c=a.lookup('btn_allMenu'); const el=document.getElementById('uuid-af'); let x=el; const chain=[]; for(let i=0;x&&i<5;i++,x=x.parentElement) chain.push({tag:x.tagName,id:x.id,cls:String(x.className||'').slice(0,120),display:getComputedStyle(x).display,visibility:getComputedStyle(x).visibility,rect:(()=>{const r=x.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})()}); return {visible:c.visible,enabled:c.enabled,elementExists:!!el,chain};}""")
 print(json.dumps(out,ensure_ascii=False))
