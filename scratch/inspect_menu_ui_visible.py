import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS="""() => {const p=cpr.core.Platform.INSTANCE;const ai=p.getAllRunningAppInstances().find(x=>x&&x.app&&x.app.id==='app/com/main/Index');const c=ai&&ai.lookup('btn_allMenu');const el=c&&document.getElementById('uuid-'+c.uuid);return {controlUuid:c&&c.uuid,visible:c&&c.visible,enabled:c&&c.enabled,rect:el?(()=>{const r=el.getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height,display:getComputedStyle(el).display}})():null,searchInputs:Array.from(document.querySelectorAll('input[aria-label="메뉴검색"]')).map(e=>({visible:!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length),display:getComputedStyle(e).display}))};}"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 pg=next(pg for c in b.contexts for pg in c.pages if 'gbe.neis.go.kr' in pg.url)
 print(json.dumps(pg.evaluate(JS),ensure_ascii=False))
