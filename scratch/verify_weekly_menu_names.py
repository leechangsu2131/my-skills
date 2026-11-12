import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS="""() => {const ai=cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(x=>x&&x.app&&x.app.id==='app/com/main/Index');const ds=ai&&ai.lookup('dsAllMenu');if(!ds)return {error:'menu dataset unavailable'};const rows=[];for(let i=0;i<ds.getRowCount();i++){const id=String(ds.getValue(i,'PGM_ID')||ds.getValue(i,'pgeId')||'');if(id==='els_edctm06_m00'||id==='els_edctm06_m02')rows.push({row:i,menuId:ds.getValue(i,'MENU_ID'),menuName:ds.getValue(i,'MENU_NM'),pageId:id,callPage:ds.getValue(i,'CALL_PAGE')});}return rows;}"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 for c in b.contexts:
  for pg in c.pages:
   if 'gbe.neis.go.kr' in pg.url:
    try:
     out=pg.evaluate(JS)
     if out: print(json.dumps(out,ensure_ascii=False))
    except Exception: pass
