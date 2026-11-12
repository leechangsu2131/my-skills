import json
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    results = []
    for context in browser.contexts:
        for page in context.pages:
            if 'neis.go.kr' not in page.url:
                continue
            page_info = {'url': page.url, 'title': page.title(), 'frames': []}
            for frame in page.frames:
                try:
                    app_ids = frame.evaluate("""() => {
                        try {
                            return cpr.core.Platform.INSTANCE.getAllRunningAppInstances()
                                .map(ai => ai && ai.app && ai.app.id).filter(Boolean);
                        } catch (e) { return []; }
                    }""")
                except Exception:
                    app_ids = []
                page_info['frames'].append({'url': frame.url, 'app_ids': app_ids})
            results.append(page_info)
    print(json.dumps(results, ensure_ascii=False))
