import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS="""() => {const apps=cpr.core.Platform.INSTANCE.getAllRunningAppInstances();return apps.filter(ai=>ai&&ai.app&&/Index|appHeader/.test(ai.app.id)).map(ai=>{let ctrls=[];try{for(const c of ai.getContainer().getAllRecursiveChildren()){const id=String(c.id||'');if(/menu|nav|tab|home|all|btn/i.test(id))ctrls.push({id,type:c.type||''});}}catch(e){};return{appId:ai.app.id,controls:ctrls};});}"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 pg=next(pg for c in b.contexts for pg in c.pages if 'gbe.neis.go.kr' in pg.url)
 print(json.dumps(pg.evaluate(JS),ensure_ascii=False))
