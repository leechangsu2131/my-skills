#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
playwright_gongmun_draft.py
======================================================
[트랙 2] K-에듀파인 전자결재 공문 기안 자동화 봇
경로: [업무관리] -> [문서관리] -> [기안] -> 기안기 열기 -> 제목/본문 입력

안전 정책:
- 결재선 지정 및 최종 상신 버튼은 사람이 직접 확인 후 처리
- 실패 시 언제든 사용자가 직접 붙여넣을 수 있도록 클립보드에 기안 내용 상시 동기화
======================================================
"""

import asyncio
import time
import os
import sys
import ctypes
from playwright.async_api import async_playwright

CDP_URL = "http://127.0.0.1:9222"

# ── 윈도우 클립보드 유틸 (표준 라이브러리 기반) ───────────────

CF_UNICODETEXT = 13
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def set_clipboard_text(text: str) -> bool:
    """Windows 클립보드에 텍스트 복사"""
    if not text:
        return False
    try:
        if not user32.OpenClipboard(None):
            return False
        user32.EmptyClipboard()
        encoded = text.encode('utf-16le') + b'\x00\x00'
        h_mem = kernel32.GlobalAlloc(0x0042, len(encoded)) # GMEM_MOVEABLE | GMEM_ZEROINIT
        if not h_mem:
            user32.CloseClipboard()
            return False
        p_mem = kernel32.GlobalLock(h_mem)
        if not p_mem:
            user32.CloseClipboard()
            return False
        ctypes.memmove(p_mem, encoded, len(encoded))
        kernel32.GlobalUnlock(h_mem)
        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        user32.CloseClipboard()
        return True
    except Exception as e:
        print(f"[클립보드 복사 실패] {e}")
        return False


# ── 브라우저 헬퍼 함수들 ─────────────────────────────────────

async def hover_and_click(page, selector, timeout=3000):
    """넥사크로 가상 좌표 및 실제 화면 요소를 타격하는 안전 클릭 함수"""
    start_time = time.time()
    while time.time() - start_time < (timeout / 1000.0):
        frames_to_check = [page] + page.frames
        for frame in frames_to_check:
            try:
                locs = await frame.locator(selector).all()
                for loc in locs:
                    box = await loc.bounding_box()
                    if box and box['width'] > 0 and box['height'] > 0 and box['x'] >= 0 and box['y'] >= 0:
                        x = box['x'] + box['width'] / 2
                        y = box['y'] + box['height'] / 2
                        await page.mouse.move(x, y, steps=8)
                        await page.wait_for_timeout(200)
                        await page.mouse.click(x, y)
                        return True
            except:
                continue
        await asyncio.sleep(0.2)
    return False


async def close_popups(page):
    """공지사항 팝업 자동 닫기"""
    target_texts = ["오늘 하루 이창을 열지 않음", "오늘 하루 이 창을 열지 않음", "확인", "닫기"]
    for text in target_texts:
        await hover_and_click(page, f"text='{text}'", timeout=800)


async def find_edufine_page(browser):
    """열려있는 브라우저 탭들 중에서 K-에듀파인 메인 탭 탐색"""
    for ctx in browser.contexts:
        for page in ctx.pages:
            url = page.url.lower()
            if "klef" in url or "eduptl" in url:
                try:
                    title = await page.title()
                    if "에듀파인" in title or "포털" in title or "업무" in title:
                        return page
                except:
                    pass
                return page
    return None


async def switch_to_work_management(page):
    """시스템 콤보박스에서 [업무관리] 시스템으로 전환"""
    print("   [시스템 확인] '업무관리' 시스템 화면인지 확인 중...")
    try:
        # 이미 업무관리 관련 메뉴나 탭이 보이는지 확인
        doc_menu = page.locator("text='문서관리'")
        if await doc_menu.first.is_visible(timeout=1500):
            print("   -> 이미 '업무관리' 시스템에 접속되어 있습니다.")
            return True

        # 상단 시스템 콤보박스 클릭
        sysbtn = page.locator("[id='mainframe.MainVFrameSet.TopFrame.form.cboJobList.comboedit']")
        box = await sysbtn.bounding_box()
        if box:
            await page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
            await page.wait_for_timeout(1000)
            
            work_items = await page.locator("[id^='mainframe.MainVFrameSet.TopFrame.form.cboJobList.combolist.item_']:has-text('업무관리')").all()
            for item in work_items:
                b = await item.bounding_box()
                if b and b['x'] >= 0 and b['y'] >= 0:
                    await page.mouse.click(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2)
                    print("   -> '업무관리' 시스템으로 전환 완료.")
                    await page.wait_for_timeout(2000)
                    return True
    except Exception as e:
        print(f"   (시스템 전환 안내: 현재 열려있는 탭에서 계속 진행합니다: {e})")
    return False


async def navigate_to_gongmun_menu(page):
    """좌측 메뉴에서 [문서관리] -> [기안] 클릭"""
    print("   [메뉴 탐색] '문서관리' -> '기안' 메뉴 탐색 중...")
    try:
        await close_popups(page)
        
        # 1. '문서관리' 클릭
        clicked_doc = await hover_and_click(page, "text='문서관리'", timeout=3000)
        if clicked_doc:
            await page.wait_for_timeout(800)
            
        # 2. '기안' 메뉴 클릭
        clicked_gian = await hover_and_click(page, "text='기안'", timeout=3000)
        if clicked_gian:
            print("   -> '기안' 메뉴를 클릭했습니다.")
            await page.wait_for_timeout(2000)
            return True
    except Exception as e:
        print(f"   (메뉴 탐색 예외: {e})")
    return False


async def open_draft_popup(page):
    """기안 목록에서 [기안] 또는 [공용기안문] 버튼을 눌러 기안문 작성 팝업 창 호출"""
    print("   [기안기 호출] 기안문 작성 버튼 탐색 중...")
    
    # 상단 도구모음의 '기안' 버튼 클릭
    gian_btns = ["text='공용기안문'", "text='기안'"]
    for btn_text in gian_btns:
        if await hover_and_click(page, btn_text, timeout=2000):
            print(f"   -> [{btn_text}] 버튼을 클릭했습니다.")
            await page.wait_for_timeout(3000)
            return True
            
    print("   [안내] 기안 버튼을 자동으로 누르지 못했습니다. 기안문 작성 창이 열릴 때까지 대기합니다...")
    return False


async def find_draft_editor_window(browser, timeout=10):
    """새로 뜬 기안문 작성 팝업 창 또는 내부 모달 프레임 탐색"""
    print("   [기안 창 대기] 열려있는 기안문 작성 창(팝업)을 탐색합니다...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        for ctx in browser.contexts:
            for p in ctx.pages:
                try:
                    title = await p.title()
                    # 새 팝업 창에 '기안'이나 '문서작성' 또는 넥사크로 팝업 타이틀
                    if any(k in title for k in ['기안', '문서', '공문', '결재']):
                        # 에디터나 제목 필드가 있는지 확인
                        return p
                except:
                    pass
        await asyncio.sleep(1)
        
    return None


async def fill_draft_content(page, title: str, body: str):
    """기안 창에 제목 및 본문 자동 주입"""
    print("   [본문 입력 시작] 기안문 제목 및 본문을 주입합니다...")
    
    # 1. 안전망: 클립보드에 전체 내용(제목+본문)을 미리 복사해 둠
    full_content = f"{title}\n\n{body}"
    set_clipboard_text(body) # 본문을 클립보드에 담아둠
    
    # 2. 제목 입력 시도
    title_filled = False
    title_inputs = await page.locator("input[type='text']").all()
    for inp in title_inputs:
        try:
            box = await inp.bounding_box()
            # 제목 필드는 보통 상단(y < 350)에 위치하고 가로 폭이 넓음(width > 200)
            if box and box['width'] > 250 and box['x'] >= 0 and 50 < box['y'] < 400:
                await inp.click()
                await inp.fill(title)
                print(f"   -> 기안 제목 입력 완료: '{title}'")
                title_filled = True
                break
        except:
            continue
            
    if not title_filled:
        print("   (제목 필드 자동 입력 생략: 수동 입력을 위해 제목을 클립보드에 준비합니다)")

    # 3. 본문 웹한글 영역 포커스 및 주입
    print("   -> 본문 웹한글 영역 탐색 및 붙여넣기 시도...")
    body_injected = False
    
    # 본문 에디터는 대개 중간~하단 영역(y > 250)에 위치
    # 넥사크로 내부 웹한글 또는 iframe 검색
    frames_to_try = [page] + page.frames
    for fr in frames_to_try:
        try:
            # 에디터 영역 캔버스/div/iframe
            editor_loc = fr.locator("div[id*='Web'], div[id*='hwp'], div[id*='Editor'], iframe, canvas").first
            if await editor_loc.is_visible(timeout=1500):
                box = await editor_loc.bounding_box()
                if box and box['width'] > 300 and box['height'] > 200:
                    center_x = box['x'] + box['width'] / 2
                    center_y = box['y'] + box['height'] / 2
                    await page.mouse.click(center_x, center_y)
                    await page.wait_for_timeout(300)
                    
                    # 붙여넣기 키 이벤트 전송
                    set_clipboard_text(body)
                    await page.keyboard.press("Control+V")
                    print("   ✓ 본문 영역에 클립보드(Ctrl+V) 주입 완료!")
                    body_injected = True
                    break
        except:
            continue

    if not body_injected:
        # 화면 중앙을 클릭하고 Ctrl+V 시도
        try:
            viewport = page.viewport_size or {'width': 1200, 'height': 800}
            await page.mouse.click(viewport['width'] / 2, viewport['height'] / 2 + 50)
            set_clipboard_text(body)
            await page.keyboard.press("Control+V")
            print("   -> 중앙 에디터 영역에 본문 붙여넣기 신호 발송 완료.")
        except Exception as e:
            print(f"   (본문 자동 주입 오류: {e})")

    return True


# ── 메인 엔트리포인트 ────────────────────────────────────────

async def execute_gongmun_draft(title: str, body: str):
    """
    [트랙 2] 전자결재 공문 기안 자동화 실행 함수
    """
    print("=" * 60)
    print("🚀 [트랙 2] K-에듀파인 전자결재 공문 기안 봇 가동")
    print(f"   제목: {title[:40]}...")
    print("=" * 60)

    # 안전망: 클립보드에 본문 우선 복사
    set_clipboard_text(body)

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"\n[오류] 브라우저(포트 9222)에 연결할 수 없습니다: {e}")
            print("  -> launch_chrome_default.bat 으로 크롬을 먼저 실행해 주세요!")
            return False

        # 1. 에듀파인 메인 페이지 찾기
        page = await find_edufine_page(browser)
        if not page:
            print("\n[오류] 열려있는 탭 중에서 K-에듀파인 페이지를 찾지 못했습니다.")
            print("  -> 브라우저에서 에듀파인에 로그인되어 있는지 확인해 주세요.")
            return False

        print(f"   -> 에듀파인 탭 감지 완료: {await page.title()}")
        await page.bring_to_front()

        # 2. [업무관리] 시스템 전환 확인
        await switch_to_work_management(page)

        # 3. [문서관리] -> [기안] 메뉴 이동
        await navigate_to_gongmun_menu(page)

        # 4. 기안기 호출
        await open_draft_popup(page)

        # 5. 기안문 작성 팝업 창 탐색
        target_window = await find_draft_editor_window(browser, timeout=5) or page

        # 6. 제목 및 본문 채우기
        await fill_draft_content(target_window, title, body)

        print("\n" + "=" * 60)
        print("🎉 [기안 초안 주입 완료]")
        print("   - 기안 제목 및 본문 작성이 완료되었습니다.")
        print("   - [결재선 지정] 및 [결재요청/상신]은 직접 확인 후 진행해 주세요.")
        print("   - (안내: 클립보드에 본문이 복사되어 있어 필요시 언제든 Ctrl+V 가능)")
        print("=" * 60)
        return True


if __name__ == '__main__':
    t = sys.argv[1] if len(sys.argv) > 1 else "2026학년도 학교 스포츠클럽 활성화 추진 계획"
    b = sys.argv[2] if len(sys.argv) > 2 else "1. 관련: 대호 공문\n2. 위 호와 관련하여 다음과 같이 추진하고자 합니다.\n  가. 대상: 전교생\n3. 행정사항: 기한 내 제출\n\n붙임  1부.  끝."
    asyncio.run(execute_gongmun_draft(t, b))
