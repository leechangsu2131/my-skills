import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 b=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 for ci,c in enumerate(b.contexts):
  for i,pg in enumerate(c.pages):
   if 'gbe.neis.go.kr' not in pg.url: continue
   try: ids=pg.evaluate("() => cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(ai=>ai&&ai.app&&ai.app.id).filter(Boolean)")
   except Exception: ids=[]
   dirty=None
   try: dirty=pg.evaluate("""() => {const ai=cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(x=>x&&x.app&&x.app.id==='edu/sw/els/edc/tm/els_edctm06_m00');if(!ai)return null;return ['dsExMessage','dsEtbSbjt','dsWikLrn'].map(id=>{const d=ai.lookup(id);return {id,modified:d&&d.isModified?d.isModified():null}})}""")
   except Exception: pass
   print(json.dumps({'context':ci,'page':i,'url':pg.url,'appIds':ids,'weeklyDirty':dirty},ensure_ascii=False))
