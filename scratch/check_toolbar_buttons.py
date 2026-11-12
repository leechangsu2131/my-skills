import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS="""() => {const ai=cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(x=>x&&x.app&&x.app.id==='app/com/main/Index');if(!ai)return {error:'Index missing'};return ['btnTlbrMn','btnTlbrSrch','btn_allMenu'].map(id=>{const c=ai.lookup(id);return{id,available:!!c,visible:c?c.visible:null,enabled:c?c.enabled:null,value:c&&typeof c.value==='string'?c.value:''}})}"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 pg=next(pg for c in b.contexts for pg in c.pages if 'gbe.neis.go.kr' in pg.url)
 print(json.dumps(pg.evaluate(JS),ensure_ascii=False))
