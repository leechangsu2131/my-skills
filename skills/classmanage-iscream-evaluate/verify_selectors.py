"""
verify_selectors.py — i-scream 페이지 연결 및 DOM 셀렉터 검증 스크립트

CDP로 원격 제어되는 Chrome 브라우저에 연결하여
현재 열려 있는 i-scream 평가 페이지와 셀렉터들이 올바르게 감지되는지 검증합니다.
오류 발생 시 상세 진단 결과를 출력하고 스크린샷과 DOM을 덤프합니다.

사용법:
    python verify_selectors.py
    python verify_selectors.py --port 9222
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Windows 콘솔 한글/이모지 출력 인코딩 오류 방지
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 검증할 대상 셀렉터 목록 (iscream_evaluate.py의 상수와 일치)
SELECTOR_SUBJECT_RADIO = 'input[name="searchSubject"]'
SELECTOR_EDIT_BUTTON = 'button#btn-result-edit'
SELECTOR_SAVE_BUTTON = 'button#btn-result-edit-save[onclick="fnfooterSave()"]'
SELECTOR_PASSWORD_INPUT = 'input#psw'
SELECTOR_STUDENT_ITEM = 'span.nm'
SELECTOR_EVAL_INPUT = 'textarea'  # 테이블 내부의 각 학생 textarea

async def check_selector_in_frames(page, label, selector):
    """모든 프레임을 돌며 해당 셀렉터가 존재하는지 찾고 상태를 출력합니다."""
    print(f"\n🔍 [{label}] 셀렉터 검증: '{selector}'")
    found_count = 0
    
    # 메인 페이지 및 모든 하위 프레임 순회
    for idx, frame in enumerate([page] + page.frames):
        frame_name = getattr(frame, 'name', None) or ( "Main Page" if idx == 0 else f"Frame {idx}" )
        try:
            locators = await frame.locator(selector).all()
            if locators:
                for j, loc in enumerate(locators):
                    is_visible = await loc.is_visible()
                    box = await loc.bounding_box()
                    box_str = f"x={box['x']}, y={box['y']}, w={box['width']}, h={box['height']}" if box else "좌표 없음"
                    print(f"  ✅ [프레임: {frame_name}] 발견 #{j+1} | 화면 표시: {is_visible} | 위치: {box_str}")
                    found_count += 1
        except Exception as e:
            # 개별 프레임 접근 에러 무시
            pass
            
    if found_count == 0:
        print(f"  ❌ 감지 실패: 어떤 프레임에서도 '{selector}' 요소를 찾지 못했습니다.")
        
    return found_count > 0

async def main():
    parser = argparse.ArgumentParser(description="i-scream 셀렉터 검증 도구")
    parser.add_argument("--port", type=int, default=9222, help="Chrome 원격 디버깅 포트")
    args = parser.parse_args()

    project_dir = Path(__file__).parent
    screenshot_path = project_dir / "iscream_verification_screenshot.png"
    dom_path = project_dir / "iscream_verification_dom.html"

    print("=" * 60)
    print("🔬 i-scream 평가 페이지 셀렉터 및 연결성 검증 시작")
    print("=" * 60)
    print(f"📡 CDP 연결 포트: localhost:{args.port}")

    async with async_playwright() as p:
        # 1. 브라우저 연결
        try:
            browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{args.port}")
            print("✅ Chrome CDP 연결 성공!")
        except Exception as e:
            print(f"❌ Chrome CDP 연결 실패: {e}")
            print("\n💡 진단 및 조치 사항:")
            print("  1) launch_chrome_iscream.bat이 실행 중인지 확인하세요.")
            print("  2) 다른 일반 크롬 창이 열려 있다면 모두 닫고 다시 실행해 보세요.")
            print("  3) 포트 번호가 일치하는지 확인하세요 (127.0.0.1로 시도됨).")
            return

        # 2. 탭 확인 및 i-scream 페이지 탐색
        target_page = None
        print("\n📄 현재 열려 있는 탭 목록:")
        
        for ctx_idx, ctx in enumerate(browser.contexts):
            for p_idx, pg in enumerate(ctx.pages):
                url = pg.url
                try:
                    title = await pg.title()
                except Exception:
                    title = "(제목 로딩 대기 중)"
                
                print(f"  - [{p_idx}] 제목: {title}")
                print(f"      URL: {url}")
                
                # 키워드 매칭
                url_lower = url.lower()
                if "i-scream" in url_lower or "iscream" in url_lower or "subjectevaluation" in url_lower:
                    target_page = pg

        if not target_page:
            print("\n❌ i-scream 평가 페이지를 감지하지 못했습니다.")
            print("💡 조치 사항: 크롬 브라우저에서 i-scream 교과평가 페이지를 열어 둔 상태에서 실행해 주세요.")
            await browser.close()
            return

        # 3. 대상 탭 포커싱 및 정보 로딩
        await target_page.bring_to_front()
        title = await target_page.title()
        print(f"\n🎯 대상 탭 선택됨: '{title}'")
        await target_page.wait_for_load_state("networkidle")
        await target_page.wait_for_timeout(1000)

        # 4. 스크린샷 및 DOM 덤프 저장 (디버그용)
        print("\n📸 현재 화면 캡처 중...")
        try:
            await target_page.screenshot(path=str(screenshot_path))
            print(f"  ✅ 스크린샷 저장 완료: {screenshot_path.name}")
        except Exception as e:
            print(f"  ❌ 스크린샷 저장 실패: {e}")

        print("💾 현재 페이지 DOM 구조 저장 중...")
        try:
            html = await target_page.content()
            dom_path.write_text(html, encoding="utf-8")
            print(f"  ✅ DOM HTML 저장 완료: {dom_path.name} ({len(html):,} bytes)")
        except Exception as e:
            print(f"  ❌ DOM 저장 실패: {e}")

        # 5. 핵심 셀렉터 검증
        print("\n==================================================")
        print("📋 DOM 핵심 셀렉터 감지 결과")
        print("==================================================")
        
        selectors_to_test = [
            ("과목 라디오 버튼", SELECTOR_SUBJECT_RADIO),
            ("텍스트 편집 버튼", SELECTOR_EDIT_BUTTON),
            ("학생 항목(이름)", SELECTOR_STUDENT_ITEM),
            ("평가 입력 텍스트 영역", SELECTOR_EVAL_INPUT),
            ("저장 버튼", SELECTOR_SAVE_BUTTON),
            ("비밀번호 입력란", SELECTOR_PASSWORD_INPUT),
        ]

        success_count = 0
        for label, selector in selectors_to_test:
            success = await check_selector_in_frames(target_page, label, selector)
            if success:
                success_count += 1

        print("\n==================================================")
        print(f"📊 검증 완료: 총 {len(selectors_to_test)}개 중 {success_count}개 감지 성공")
        print("==================================================")
        
        if success_count == len(selectors_to_test):
            print("\n🎉 모든 핵심 셀렉터가 정상적으로 매핑되었습니다. 바로 자동 기록을 시작할 수 있습니다!")
        else:
            print("\n⚠️ 일부 셀렉터가 누락되었습니다.")
            print("  - i-scream 사이트가 업데이트되었거나 다른 페이지에 접속해 있을 수 있습니다.")
            print("  - 생성된 'iscream_verification_dom.html' 파일을 통해 올바른 셀렉터를 식별하고")
            print("    'iscream_evaluate.py' 및 'verify_selectors.py' 상단의 셀렉터 값을 조정해 주세요.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
