import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS="""() => {const ai=cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(x=>x&&x.app&&x.app.id==='edu/sw/els/edc/tm/els_edctm06_m00');if(!ai)return {error:'app missing'};return ['subSelectWikInfo','subSelectHcnt','subWikInfoSave','subSaveAllWikLrn'].map(id=>{const o=ai.lookup(id);if(!o)return{id,available:false};let props=[];try{props=Object.keys(o).map(k=>({name:k,type:typeof o[k]}))}catch(e){};let methods=[];let p=Object.getPrototypeOf(o);for(let d=0;p&&d<3;d++,p=Object.getPrototypeOf(p))try{methods.push(...Object.getOwnPropertyNames(p).filter(k=>/url|action|submit|input|output|target|request|response|success/i.test(k)).map(name=>({depth:d,name,type:typeof o[name]})))}catch(e){};return{id,available:true,properties:props,methods};});}"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 for c in b.contexts:
  for pg in c.pages:
   if 'gbe.neis.go.kr' in pg.url:
    try:
     result=pg.evaluate(JS)
     if result and not isinstance(result,dict): print(json.dumps(result,ensure_ascii=False))
    except Exception: pass
