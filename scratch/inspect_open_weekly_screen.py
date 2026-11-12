import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS = """() => {
 const p=cpr.core.Platform.INSTANCE;
 const apps=p.getAllRunningAppInstances().map(ai=>ai&&ai.app).filter(Boolean);
 return apps.map(app=>{
  const ctrls=[];
  try { for(const c of app.getContainer().getAllRecursiveChildren()) { ctrls.push({id:c.id||'',type:c.type||'',name:c.name||'',text:(typeof c.text==='string'?c.text:'').slice(0,60)}); } } catch(e){}
  return {appId:app.id,controls:ctrls};
 });
}"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 for ci,c in enumerate(b.contexts):
  for pi,page in enumerate(c.pages):
   if 'gbe.neis.go.kr' not in page.url: continue
   try: apps=page.evaluate(JS)
   except Exception: apps=[]
   print(json.dumps({'context':ci,'page':pi,'url':page.url,'apps':apps},ensure_ascii=False))
