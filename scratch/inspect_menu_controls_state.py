import json,sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS="""() => {const ai=cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(x=>x&&x.app&&x.app.id==='app/com/main/Index');const ids=['btnTlbrMn','btnTlbrSrch','btn_allMenu','snavMn','siFindMenu','navMn'];return ids.map(id=>{const c=ai.lookup(id);if(!c)return{id,missing:true};const el=document.getElementById('uuid-'+c.uuid);const r=el&&el.getBoundingClientRect();return{id,visible:c.visible,enabled:c.enabled,type:c.type,dom:el?{id:el.id,display:getComputedStyle(el).display,visibility:getComputedStyle(el).visibility,rect:r?{x:r.x,y:r.y,w:r.width,h:r.height}:null}:null,events:Object.keys(c._eventListenerList||{})};});}"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 pg=next(pg for c in b.contexts for pg in c.pages if 'gbe.neis.go.kr' in pg.url)
 print(json.dumps(pg.evaluate(JS),ensure_ascii=False))
