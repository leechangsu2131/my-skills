import json, sys, time
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
MENU_CLICK = """() => {
  const platform = cpr.core.Platform.INSTANCE;
  const indexApp = platform.getAllRunningAppInstances().find(ai => ai && ai.app && ai.app.id === 'app/com/main/Index');
  if (!indexApp) return {error:'Index app unavailable'};
  if (typeof indexApp.menuClick !== 'function') return {error:'menuClick unavailable'};
  indexApp.menuClick('AMELS40032');
  return {ok:true, method:'Index.menuClick', menuId:'AMELS40032'};
}"""
APP_IDS = """() => cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(ai => ai && ai.app && ai.app.id).filter(Boolean)"""
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    page = next(pg for ctx in browser.contexts for pg in ctx.pages if 'gbe.neis.go.kr/jsp/main.jsp' in pg.url)
    result = page.evaluate(MENU_CLICK)
    time.sleep(3)
    print(json.dumps({'navigation':result,'appIds':page.evaluate(APP_IDS)},ensure_ascii=False))
