import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS="""() => {const p=cpr.core.Platform.INSTANCE;const names=[];let q=Object.getPrototypeOf(p);for(let d=0;q&&d<5;d++,q=Object.getPrototypeOf(q))for(const n of Object.getOwnPropertyNames(q))if(/app|menu|open|route|page|mdi|navigate|load/i.test(n))names.push({depth:d,name:n,type:typeof p[n]});const ai=p.getAllRunningAppInstances().find(x=>x&&x.app&&x.app.id==='app/com/main/Index');const c=ai&&ai.lookup('btn_allMenu');return {platformMethods:names,menuButton:c?{visible:c.visible,enabled:c.enabled,events:Object.keys(c._eventListenerList||{})}:null,allMenuSearch:!!(ai&&ai.lookup('siFindMenu'))};}"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 pg=next(pg for c in b.contexts for pg in c.pages if 'gbe.neis.go.kr' in pg.url)
 print(json.dumps(pg.evaluate(JS),ensure_ascii=False))
