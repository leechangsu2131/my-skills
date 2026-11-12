import json
from playwright.sync_api import sync_playwright

MENU_READ = """() => {
  const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
  if (!platform) return {error: 'cpr unavailable'};
  const indexApp = platform.getAllRunningAppInstances().find(ai => ai && ai.app && ai.app.id === 'app/com/main/Index');
  if (!indexApp) return {error: 'Index app unavailable'};
  const ds = indexApp.lookup('dsAllMenu');
  if (!ds || !ds.getRowCount) return {error: 'dsAllMenu unavailable'};
  const cols = ['MENU_ID','MENU_NM','UP_MENU_ID','CALL_PAGE','PGM_ID','pgeId','pgeClfId'];
  const rows = [];
  for (let r=0; r<ds.getRowCount(); r++) {
    const name = String(ds.getValue(r, 'MENU_NM') || ds.getValue(r, 'menuNm') || '');
    if (name.includes('주간학습안내조회')) {
      const row = {rowIndex:r};
      for (const col of cols) { try { const v=ds.getValue(r,col); if (v !== undefined && v !== null && String(v)) row[col]=String(v); } catch(e) {} }
      rows.push(row);
    }
  }
  return {menuMatches:rows, appIds:platform.getAllRunningAppInstances().map(ai=>ai&&ai.app&&ai.app.id).filter(Boolean)};
}"""
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    page = next(pg for ctx in browser.contexts for pg in ctx.pages if 'gbe.neis.go.kr/jsp/main.jsp' in pg.url)
    frame = next(fr for fr in page.frames if fr.url == page.url)
    print(json.dumps(frame.evaluate(MENU_READ), ensure_ascii=False))
