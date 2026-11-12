import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS="""() => {const ai=cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(x=>x&&x.app&&x.app.id==='edu/sw/els/edc/tm/els_edctm06_m00');if(!ai)return {error:'app missing'};return ['subSelectWikInfo','subWikInfoSave'].map(id=>{const s=ai.lookup(id);let r={};try{r=s.getRequestObject()||{}}catch(e){};const safe={};for(const k of ['method','httpMethod','type','action','url','async','contentType'])if(typeof r[k]==='string'||typeof r[k]==='boolean')safe[k]=r[k];if(safe.url){try{safe.url=new URL(safe.url,location.origin).pathname}catch(e){safe.url=String(safe.url).split('?')[0]}}if(safe.action){try{safe.action=new URL(safe.action,location.origin).pathname}catch(e){safe.action=String(safe.action).split('?')[0]}}return{id,requestObjectKeys:Object.keys(r),safe};});}"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 for c in b.contexts:
  for pg in c.pages:
   if 'gbe.neis.go.kr' in pg.url:
    try:
     result=pg.evaluate(JS)
     if result and not isinstance(result,dict):print(json.dumps(result,ensure_ascii=False))
    except Exception:pass
