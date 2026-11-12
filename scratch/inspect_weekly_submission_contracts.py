import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS="""() => {const ai=cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(x=>x&&x.app&&x.app.id==='edu/sw/els/edc/tm/els_edctm06_m00');if(!ai)return {error:'app missing'};return ['subSelectWikInfo','subSelectHcnt','subWikInfoSave','subSaveAllWikLrn'].map(id=>{const s=ai.lookup(id);if(!s)return{id,available:false};let url='';try{url=s.getRequestActionUrl()}catch(e){};let requests=[];try{for(let i=0;i<s.getRequestDataCount();i++){const x=s.getRequestData(i);requests.push({index:i,id:x&&x.id||'',type:x&&x.type||'',constructor:x&&x.constructor&&x.constructor.name||'',keys:x&&typeof x==='object'?Object.keys(x).slice(0,16):[]});}}catch(e){};let responses=[];try{for(const x of (s.getResponseDatas()||[])){responses.push({id:x&&x.id||'',type:x&&x.type||'',constructor:x&&x.constructor&&x.constructor.name||'',keys:x&&typeof x==='object'?Object.keys(x).slice(0,16):[]});}}catch(e){};let path='';try{path=new URL(String(url),location.origin).pathname}catch(e){path=String(url).split('?')[0]};return{id,path,requestDataCount:requests.length,requests,responses,successNow:typeof s.isSuccess==='function'?s.isSuccess():null};});}"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 for c in b.contexts:
  for pg in c.pages:
   if 'gbe.neis.go.kr' in pg.url:
    try:
     result=pg.evaluate(JS)
     if result and not isinstance(result,dict):print(json.dumps(result,ensure_ascii=False))
    except Exception:pass
