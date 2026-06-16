import asyncio
import time
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    print("============================================================")
    print("⏳ 대기 중: Chrome 브라우저에서 '확인'을 눌러 로그인해 주세요...")
    print("============================================================")
    
    project_dir = Path(__file__).parent
    screenshot_path = project_dir / "iscream_eval_screenshot.png"
    dom_path = project_dir / "iscream_eval_dom.html"
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            print("✅ Chrome CDP 연결 성공")
        except Exception as e:
            print(f"❌ Chrome CDP 연결 실패: {e}")
            return

        # 2분 동안 감시
        for sec in range(120):
            target_page = None
            for ctx in browser.contexts:
                for pg in ctx.pages:
                    url = pg.url.lower()
                    if "subjectevaluation.do" in url and "check.do" not in url:
                        target_page = pg
                        break
                if target_page:
                    break
            
            if target_page:
                print(f"\n🎉 대상 평가 입력 페이지가 감지되었습니다!")
                print(f"🔗 URL: {target_page.url}")
                
                # 대기 후 캡처
                await target_page.wait_for_timeout(2000)
                await target_page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"📸 스크린샷 저장 완료: {screenshot_path.name}")
                
                html = await target_page.content()
                dom_path.write_text(html, encoding="utf-8")
                print(f"💾 DOM HTML 저장 완료: {dom_path.name} ({len(html):,} bytes)")
                
                await browser.close()
                return
            
            if sec % 10 == 0:
                print(f"   ({sec}초 경과) Chrome 브라우저에서 비밀번호를 입력하고 확인을 눌러주세요...")
            
            await asyncio.sleep(1)
            
        print("\n❌ 대기 시간 초과: 2분 동안 평가 입력 페이지(SubjectEvaluation.do)가 감지되지 않았습니다.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
