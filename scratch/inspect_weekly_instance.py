import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS = """() => cpr.core.Platform.INSTANCE.getAllRunningAppInstances().filter(ai=>ai&&ai.app&&ai.app.id==='edu/sw/els/edc/tm/els_edctm06_m00').map(ai=>{
 const controls=[];
 try { for(const c of ai.getContainer().getAllRecursiveChildren()) controls.push({id:c.id||'',type:c.type||''}); } catch(e){}
 const proto=[]; let x=Object.getPrototypeOf(ai); for(let d=0;x&&d<3;d++,x=Object.getPrototypeOf(x)) for(const n of Object.getOwnPropertyNames(x)) if(/data|lookup|child|dataset/i.test(n)) proto.push(n);
 return {appId:ai.app.id,controls,prototypeMethods:[...new Set(proto)]};
})"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 for c in b.contexts:
  for page in c.pages:
   if 'gbe.neis.go.kr' in page.url:
    try:
     result=page.evaluate(JS)
     if result: print(json.dumps(result,ensure_ascii=False))
    except Exception: pass
