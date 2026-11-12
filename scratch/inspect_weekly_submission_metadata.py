import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS="""() => {const ai=cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(x=>x&&x.app&&x.app.id==='edu/sw/els/edc/tm/els_edctm06_m00');if(!ai)return {error:'app missing'};return ['subSelectWikInfo','subSelectHcnt','subWikInfoSave','subSaveAllWikLrn'].map(id=>{const s=ai.lookup(id);if(!s)return{id,available:false};const req=[];try{for(let i=0;i<s.getRequestDataCount();i++){const x=s.getRequestData(i)||{},d=x.data||{},p=x.payload||{};req.push({index:i,alias:x.alias||'',dataId:d.id||'',dataType:d.type||'',payloadKeys:Object.keys(p)});}}catch(e){};const res=[];try{for(let i=0;i<s.getResponseDataCount();i++){const x=s.getResponseData(i)||{},d=x.data||{},p=x.payload||{};res.push({index:i,alias:x.alias||'',dataId:d.id||'',dataType:d.type||'',payloadKeys:Object.keys(p)});}}catch(e){};const stringProps=[];try{for(const k of Object.keys(s)){const v=s[k];if(typeof v==='string'&&(/[/.]do|^\/|http/i.test(v)))stringProps.push({key:k,path:(()=>{try{return new URL(v,location.origin).pathname}catch(e){return v.split('?')[0]}})()});}}catch(e){};let action='';try{action=String(s.action||'')}catch(e){};return{id,actionPath:(()=>{try{return new URL(action,location.origin).pathname}catch(e){return action.split('?')[0]}})(),urlProps:stringProps,requests:req,responses:res};});}"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 for c in b.contexts:
  for pg in c.pages:
   if 'gbe.neis.go.kr' in pg.url:
    try:
     result=pg.evaluate(JS)
     if result and not isinstance(result,dict): print(json.dumps(result,ensure_ascii=False))
    except Exception: pass
