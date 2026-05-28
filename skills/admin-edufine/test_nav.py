import asyncio
import os
import time
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        try:
            print("[Test] Chrome 디버깅 포트(9222)에 연결 시도...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            print("[Test] 연결 성공!")
            
            edufine_page = None
            for ctx in browser.contexts:
                for page in ctx.pages:
                    url = page.url.lower()
                    title = await page.title()
                    print(f" - Found Tab: {title} ({url})")
                    if "klef" in url or "에듀파인" in title:
                        edufine_page = page
                        break
                if edufine_page: break
                
            if not edufine_page:
                print("[Test] 에듀파인 창을 찾지 못했습니다.")
                return
                
            print(f"[Test] 에듀파인 창 선택됨: {await edufine_page.title()}")
            await edufine_page.bring_to_front()
            
            # 스크린샷 1: 현재 상태
            artifact_dir = r"C:\Users\user\.gemini\antigravity\brain\042b9ca2-8b35-4263-a331-c65b11186f02"
            path1 = os.path.join(artifact_dir, "test_step1_init.png")
            await edufine_page.screenshot(path=path1)
            print(f"[Test] 스크린샷 1 저장됨: {path1}")
            
            # 텍스트 노드 강제 검색 및 바운딩 박스 출력
            print("[Test] 프레임 탐색을 통한 텍스트 위치 분석 시작...")
            target_texts = ["업무관리", "학교회계", "사업담당"]
            for target in target_texts:
                found = False
                for i, frame in enumerate([edufine_page] + edufine_page.frames):
                    try:
                        locs = await frame.locator(f"text='{target}'").all()
                        for j, loc in enumerate(locs):
                            box = await loc.bounding_box()
                            if box:
                                print(f"  -> '{target}' 발견! (Frame {i}, Match {j}): x={box['x']}, y={box['y']}, w={box['width']}, h={box['height']}")
                                found = True
                    except Exception as e:
                        pass
                if not found:
                    print(f"  -> '{target}' 요소를 찾지 못했습니다 (또는 bounding_box가 없음).")

            # DOM 저장 (분석용)
            html_path = os.path.join(artifact_dir, "edufine_dom.html")
            html = await edufine_page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[Test] 메인 페이지 HTML 저장됨: {html_path}")
            
        except Exception as e:
            print(f"[Test] 에러 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())
