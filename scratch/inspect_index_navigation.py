import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
INSPECT = """() => {
 const p=cpr.core.Platform.INSTANCE;
 const ai=p.getAllRunningAppInstances().find(x=>x&&x.app&&x.app.id==='app/com/main/Index');
 if(!ai)return {error:'Index missing'};
 const methodNames=[]; let proto=Object.getPrototypeOf(ai); let depth=0;
 while(proto&&depth<4){for(const n of Object.getOwnPropertyNames(proto)){if(/menu|open|select|tab|click|navigate/i.test(n))methodNames.push({depth,name:n,type:typeof ai[n]});}proto=Object.getPrototypeOf(proto);depth++;}
 let controls=[]; try {for(const c of ai.getContainer().getAllRecursiveChildren()){const id=String(c.id||''); if(/menu|tab|tre|mdi|search/i.test(id)){controls.push({id,type:c.type||'',value:typeof c.value==='string'?c.value:'',text:typeof c.text==='string'?c.text:''});}}}catch(e){}
 const menu=ai.lookup('dsAllMenu'); let row=-1; try {for(let i=0;i<menu.getRowCount();i++){if(String(menu.getValue(i,'MENU_ID'))==='AMELS40032'){row=i;break;}}}catch(e){}
 return {methods:methodNames,controls:controls.slice(0,80),menuRow:row,bodyHasWeekly:document.body.innerText.includes('주간학습안내조회')};
}"""
with sync_playwright() as p:
 browser=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 page=next(pg for c in browser.contexts for pg in c.pages if 'gbe.neis.go.kr/jsp/main.jsp' in pg.url)
 print(json.dumps(page.evaluate(INSPECT),ensure_ascii=False))
