import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
JS="""() => {
 const ai=cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(x=>x&&x.app&&x.app.id==='edu/sw/els/edc/tm/els_edctm06_m00');
 if(!ai)return {error:'weekly app unavailable'};
 const ids=['dsWeekList','dsAyrSemGrdByEtbSbjt','dsHcntList','dsSbjtList','dsWikLrn','dsEtbSbjt','dsExMessage','dmSearch','dmReport','dmSemYmd','dmScaSem'];
 return ids.map(id=>{const d=ai.lookup(id);if(!d)return {id,available:false};let cols=[];try{cols=d.getColumnNames?d.getColumnNames():[];if(!cols.length&&d.getColumnCount&&d.getColumnID){for(let i=0;i<d.getColumnCount();i++)cols.push(d.getColumnID(i));}}catch(e){};let rows=null,modified=null;try{if(d.getRowCount)rows=d.getRowCount()}catch(e){};try{if(d.isModified)modified=d.isModified()}catch(e){};return {id,type:d.type||'',rowCount:rows,columnCount:cols.length,columns:cols,modified};});
}"""
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 for c in b.contexts:
  for pg in c.pages:
   if 'gbe.neis.go.kr' in pg.url:
    try:
     result=pg.evaluate(JS)
     if result and not isinstance(result,dict) or (isinstance(result,dict) and not result.get('error')): print(json.dumps(result,ensure_ascii=False))
    except Exception: pass
