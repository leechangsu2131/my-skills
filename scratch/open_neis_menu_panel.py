import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS="""() => {const ai=cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(x=>x&&x.app&&x.app.id==='app/com/main/Index');ai.lookup('btnTlbrMn').click();const s=ai.lookup('siFindMenu');return {searchVisible:s?s.visible:null,menuButtonValue:ai.lookup('btnTlbrMn').value||'',appIds:cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(x=>x&&x.app&&x.app.id).filter(Boolean)};}"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 pg=next(pg for c in b.contexts for pg in c.pages if 'gbe.neis.go.kr' in pg.url)
 print(json.dumps(pg.evaluate(JS),ensure_ascii=False))
