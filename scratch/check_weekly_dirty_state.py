import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS="""() => cpr.core.Platform.INSTANCE.getAllRunningAppInstances().filter(ai=>ai&&ai.app&&ai.app.id==='edu/sw/els/edc/tm/els_edctm06_m00').map(ai=>{
 const out=[]; try{for(const x of ai.getAllDataControls()){let modified=null;try{if(typeof x.isModified==='function')modified=x.isModified();}catch(e){}out.push({id:x.id||'',type:x.type||'',constructor:x.constructor&&x.constructor.name||'',modified,methods:Object.getOwnPropertyNames(Object.getPrototypeOf(x)||{}).filter(n=>/modified|column|rowcount/i.test(n)).slice(0,8)});}}catch(e){out.push({error:String(e)})}return out;})"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 for c in b.contexts:
  for pg in c.pages:
   if 'gbe.neis.go.kr' in pg.url:
    try:
     result=pg.evaluate(JS)
     if result: print(json.dumps(result,ensure_ascii=False))
    except Exception: pass
