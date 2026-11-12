import json, sys
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 browser=p.chromium.connect_over_cdp('http://127.0.0.1:9222')
 context=browser.contexts[0]
 page=context.new_page()
 page.goto('https://gbe.neis.go.kr/jsp/main.jsp',wait_until='domcontentloaded',timeout=30000)
 try: page.wait_for_function("() => !!(window.cpr && cpr.core && cpr.core.Platform)",timeout=20000)
 except Exception: pass
 apps=[]
 try: apps=page.evaluate("() => cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(ai=>ai&&ai.app&&ai.app.id).filter(Boolean)")
 except Exception: pass
 print(json.dumps({'url':page.url,'title':page.title(),'cprReady':bool(apps),'appIds':apps},ensure_ascii=False))
