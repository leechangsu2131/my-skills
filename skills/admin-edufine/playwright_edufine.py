import asyncio
import time
import os
from playwright.async_api import async_playwright

# 외부(Flask 또는 CLI) 제어 신호 (process_batch 내에서 초기화됨)
next_event = None
current_event_type = None

# 전역 상태 (중단 여부)
stop_requested = False

async def close_popups(page):
    print("   -> 공지사항 등 팝업 창이 있는지 확인합니다...")
    try:
        # 팝업이 렌더링될 시간을 잠시 대기 (id에 noticePopup이 포함된 요소 대기)
        try:
            await page.wait_for_selector("div[id*='noticePopup']", timeout=3000)
            print("   -> 공지사항 팝업 프레임을 감지했습니다.")
        except:
            pass # 팝업이 없을 수도 있으므로 패스

        # 팝업에 주로 등장하는 텍스트 목록 (띄어쓰기 주의)
        target_texts = ["오늘 하루 이창을 열지 않음", "오늘 하루 이 창을 열지 않음", "확인", "닫기"]
        for text in target_texts:
            elements = await page.locator(f"text='{text}'").all()
            for el in elements:
                if await el.is_visible(timeout=500):
                    box = await el.bounding_box()
                    if box:
                        print(f"   -> 팝업 내 '{text}' 버튼 클릭 시도...")
                        await el.click(force=True)
                        await page.wait_for_timeout(500)
    except Exception as e:
        print(f"   (팝업 닫기 중 오류: {e})")

async def navigate_to_draft_page(page):
    print("   [네비게이션] 에듀파인 메뉴 자동 탐색을 시작합니다...")
    try:
        # 이미 품의등록 화면인지 확인
        try:
            title_input = page.locator("input[id*='edtCnsulSj']")
            if await title_input.first.is_visible(timeout=2000):
                print("   [안내] 이미 '품의등록' 화면이 열려있습니다. 메뉴 탐색을 생략합니다.")
                return True
        except:
            pass
            
        # 네비게이션 시작 전 팝업 닫기
        await close_popups(page)
        
        # '업무관리' -> '학교회계' 시스템 전환
        # 넥사크로 FrameSet 내부 요소이며, 마우스 hover 시 드롭다운이 나타나는 구조
        try:
            print("   -> '업무관리' 영역에 마우스 호버 (드롭다운 열기)...")
            # 스크린샷 기준 '업무관리' 버튼 중심 좌표: 약 x=70, y=70
            await page.mouse.move(70, 70)
            await page.wait_for_timeout(1500)  # 드롭다운 애니메이션 대기
            
            # 드롭다운이 나타나면 '학교회계' 텍스트를 찾아 클릭
            try:
                school_acct = page.locator("text='학교회계'").first
                if await school_acct.is_visible(timeout=3000):
                    print("   -> '학교회계' 메뉴 발견! 클릭합니다.")
                    await school_acct.click()
                    await page.wait_for_timeout(4000)  # 시스템 전환 + 메뉴 로딩 대기
                else:
                    # 텍스트로 못 찾으면 드롭다운 내부 좌표로 직접 클릭 시도
                    print("   -> 텍스트로 못 찾아서 드롭다운 좌표 클릭 시도...")
                    await page.mouse.click(70, 120)  # 드롭다운 첫 번째 항목쯤
                    await page.wait_for_timeout(4000)
            except Exception as e:
                print(f"   -> ('학교회계' 전환 스킵: {e})")
        except Exception as e:
            print(f"   (시스템 전환 오류 무시: {e})")
            
        print("   -> '사업담당' 메뉴 클릭")
        await page.click("text=사업담당")
        await page.wait_for_timeout(1500)
        
        print("   -> '품의/정산' 메뉴 클릭")
        await page.click("text=품의/정산")
        await page.wait_for_timeout(1500)
        
        print("   -> '품의등록' 메뉴 클릭")
        await page.click("text=품의등록")
        await page.wait_for_timeout(3000) # 기안 폼 화면 로딩 대기
        
        print("   [네비게이션 완료] 품의 등록 화면에 진입했습니다.")
        return True
    except Exception as e:
        print(f"   [네비게이션 오류] 메뉴 클릭 실패: {e}")
        print("   -> (수동으로 품의 등록 화면까지 이동해 주셔도 됩니다.)")
        return False

async def fill_draft_form(page, item):
    print("   [폼 입력] 품의등록 폼에 데이터를 입력합니다...")
    data = item.get('data', {})
    
    title = data.get('제목', '빈 기안 (수동 작성)')
    summary = data.get('내용', '')
    
    # 파싱된 공문 메타데이터가 있으면 개요(summary)에 '관련' 문구 자동 생성
    if not summary:
        refs = []
        if data.get('sihaeng_no'):
            sender = data.get('발신처', '')
            sihaeng_no = data.get('sihaeng_no', '')
            date_str = f" ({data['sihaeng_date'].replace('-', '. ')}.)" if data.get('sihaeng_date') else ""
            refs.append(f"관련: {sender} {sihaeng_no}{date_str}".strip())
        elif data.get('jeopsu_no'):
            jeopsu_no = data.get('jeopsu_no', '')
            date_str = f" ({data['jeopsu_date'].replace('-', '. ')}.)" if data.get('jeopsu_date') else ""
            refs.append(f"관련: 본교 {jeopsu_no}{date_str}")
            
        if refs:
            summary = "\n".join(refs) + "\n\n위 호와 관련하여 다음과 같이 업무를 추진하고자 합니다."
        else:
            summary = '내용을 수동으로 입력하세요.'
        
    try:
        print("   -> 제목 입력 중...")
        title_input = page.locator("input[id*='edtCnsulSj']")
        await title_input.first.click(force=True, timeout=3000)
        await page.wait_for_timeout(300)
        await title_input.first.fill(title, force=True)
        
        print("   -> 개요 입력 중...")
        summary_input = page.locator("textarea[id*='txtareaCnsulSumrCn']")
        await summary_input.first.click(force=True, timeout=3000)
        await page.wait_for_timeout(300)
        await summary_input.first.fill(summary[:1900], force=True) # 최대 글자수 고려
        
        print("   -> '예산선택' 버튼 클릭 (팝업 열기)...")
        bgt_btn = page.locator("text='예산선택'").first
        await bgt_btn.click(force=True, timeout=3000)
        await page.wait_for_timeout(1000)
        
        return True
    except Exception as e:
        print(f"   [입력 오류] 폼 입력 중 오류 발생: {e}")
        return False

async def add_draft_row(page):
    try:
        print("   -> '행추가' 버튼 클릭...")
        row_btns = await page.locator(".btn_WF_RowAdd").all()
        clicked = False
        for btn in row_btns:
            if await btn.is_visible():
                box = await btn.bounding_box()
                if box:
                    await page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                    clicked = True
                    break
                    
        if not clicked:
            btns = await page.locator("text='행추가'").all()
            for btn in btns:
                if await btn.is_visible():
                    box = await btn.bounding_box()
                    if box:
                        await page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                        clicked = True
                        break
                        
        if not clicked:
            print("   [경고] 가시적인 '행추가' 버튼을 찾지 못했습니다.")
            
        await page.wait_for_timeout(1000)
        return True
    except Exception as e:
        print(f"   [오류] 행추가 실패: {e}")
        return False

async def process_batch(parsed_items, dry_run=False):
    global stop_requested, next_event
    stop_requested = False
    next_event = asyncio.Event()
    
    results = []
    if not parsed_items:
        return results
        
    print("\n[안내] 에듀파인 기안 자동화 봇을 시작합니다.")
    
    # 단일 처리 모드로 첫 번째 파일만 가져옵니다.
    item = parsed_items[0]
    filepath = item.get('_filepath', 'Unknown')
    data = item.get('data', {})
    title = data.get('제목', '제목 없음')
    
    entry = {
        'filepath': filepath,
        'sihaeng_no': data.get('sihaeng_no', ''),
        'title': title,
        'status': '성공',
        'fail_reason': '',
        'processed_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if dry_run:
        print("   [Dry Run] 기안 폼 입력 시뮬레이션 완료")
        results.append(entry)
        return results
    
    async with async_playwright() as p:
        try:
            print("   (Chrome 원격 디버깅 포트 9222 연결 중...)")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            
            # 열려있는 탭 중에서 에듀파인(또는 K-에듀파인) 페이지 찾기
            portal_page = None
            edufine_pages = []
            for ctx in browser.contexts:
                for p_idx in ctx.pages:
                    url = p_idx.url.lower()
                    try:
                        p_title = await p_idx.title()
                    except:
                        p_title = ""
                        
                    if "klef" in url or "에듀파인" in p_title:
                        edufine_pages.append(p_idx)
                    elif "eduptl" in url or "업무포털" in p_title:
                        portal_page = p_idx
                        
            edufine_page = None
            # 여러 개의 에듀파인 창이 있다면, '품의등록' 폼이 이미 열려있는 창을 최우선으로 선택
            for p_idx in edufine_pages:
                try:
                    if await p_idx.locator("input[id*='edtCnsulSj']").count() > 0:
                        edufine_page = p_idx
                        print("   [안내] 여러 K-에듀파인 창 중 '품의등록' 화면이 있는 창을 찾았습니다!")
                        break
                except:
                    pass
            
            # 없으면 첫 번째 에듀파인 창 선택
            if not edufine_page and edufine_pages:
                edufine_page = edufine_pages[0]
                    
            page = None
            if edufine_page:
                print("   [안내] 이미 열려있는 K-에듀파인 창을 찾았습니다.")
                page = edufine_page
                await page.bring_to_front()
            elif portal_page:
                print("   [안내] 업무포털 창을 찾았습니다. K-에듀파인 새 창을 엽니다.")
                page = portal_page
                await page.bring_to_front()
                try:
                    # K-에듀파인 텍스트가 있는 요소를 찾아 클릭하여 팝업 열기
                    # (정확한 일치 "K-에듀파인" 또는 0번째 요소를 클릭)
                    async with page.context.expect_page(timeout=15000) as new_page_info:
                        locators = page.locator("text='K-에듀파인'")
                        await locators.nth(0).click()
                    page = await new_page_info.value
                    await page.wait_for_load_state()
                    print("   [안내] K-에듀파인 새 창이 성공적으로 열렸습니다.")
                except Exception as e:
                    print(f"   [오류] K-에듀파인 새 창 열기 실패: {e}")
                    print("   -> 업무포털에서 [K-에듀파인] 메뉴를 직접 클릭한 뒤 다시 실행해 주세요.")
                    entry['status'] = '실패'
                    entry['fail_reason'] = 'K-에듀파인 열기 실패'
                    results.append(entry)
                    return results
            else:
                print("[오류] 크롬에 열려있는 'K-에듀파인' 또는 '업무포털' 탭을 찾을 수 없습니다.")
                print(" -> 'launch_chrome.bat'로 열린 크롬에서 로그인 후 이 작업을 실행해주세요.")
                entry['status'] = '실패'
                entry['fail_reason'] = '에듀파인/포털 탭 없음'
                results.append(entry)
                return results
            
            # 네비게이션 자동화 실행
            nav_success = await navigate_to_draft_page(page)
            
            # 실제 폼 입력 단계
            print("-" * 60)
            print(f"[{title[:40]}] 공문 기안 폼 입력 대기...")
            if nav_success:
                # 폼 데이터 입력 및 예산선택 버튼 클릭
                await fill_draft_form(page, item)
                
                print(f"\n   [공문 수동 작업 대기] {os.path.basename(item['_filepath'])}")
                print("   -> 1. 팝업에서 예산을 수동으로 고르신 후 [확인]을 눌러주세요.")
                print("   -> 2. 예산 선택이 완료되면 웹 화면에서 [행추가 하기] 또는 [기안 완료] 버튼을 누르세요.")
                
                # UI에서 'next' 또는 'add_row' 이벤트가 올 때까지 루프
                while True:
                    next_event.clear()
                    await next_event.wait()
                    
                    if stop_requested:
                        print("   [중단] 사용자 요청으로 작업을 중단합니다.")
                        entry['status'] = '사용자 중단'
                        results.append(entry)
                        return results
                        
                    if current_event_type == 'add_row':
                        items_text = getattr(sys.modules[__name__], 'current_items_text', '')
                        import re
                        parsed_items = []
                        for line in items_text.split('\n'):
                            line = line.strip()
                            if not line.startswith('- '): continue
                            m = re.match(r'- (.+) \(수량: (\d+), 단가: (\d+)원\)', line)
                            if m:
                                parsed_items.append({
                                    'name': m.group(1).strip(),
                                    'quantity': int(m.group(2)),
                                    'unit_price': int(m.group(3))
                                })
                                
                        if not parsed_items:
                            await add_draft_row(page)
                            print("   [안내] 기본 행추가를 1개 시도했습니다. 화면을 확인해주세요.")
                        else:
                            print(f"   [안내] 기록된 물품 {len(parsed_items)}개를 기반으로 행추가를 시작합니다.")
                            for i, c_item in enumerate(parsed_items):
                                print(f"      -> {i+1}번째 품목 추가: {c_item['name']} (수량: {c_item['quantity']}, 단가: {c_item['unit_price']})")
                                await add_draft_row(page)
                                # 넥사크로 그리드에서 새 행이 추가되면 보통 첫 번째 입력 가능 셀이 포커스 됨
                                await page.wait_for_timeout(500)
                                # 물품명 편집 모드 진입
                                await page.keyboard.press("Enter")
                                await page.wait_for_timeout(200)
                                await page.keyboard.type(c_item['name'])
                                await page.keyboard.press("Enter")
                                await page.wait_for_timeout(200)
                                
                                # 규격을 건너뛰고 수량으로 이동 (Tab 2회)
                                await page.keyboard.press("Tab") 
                                await page.wait_for_timeout(100)
                                await page.keyboard.press("Tab") 
                                await page.wait_for_timeout(200)
                                
                                # 수량 편집 모드 진입
                                if c_item['quantity']:
                                    await page.keyboard.press("Enter")
                                    await page.wait_for_timeout(200)
                                    await page.keyboard.type(str(c_item['quantity']))
                                    await page.keyboard.press("Enter")
                                    await page.wait_for_timeout(200)
                                    
                                # 단위를 건너뛰고 단가로 이동 (Tab 1회)
                                await page.keyboard.press("Tab") 
                                await page.wait_for_timeout(200)
                                
                                # 단가 편집 모드 진입
                                if c_item['unit_price']:
                                    await page.keyboard.press("Enter")
                                    await page.wait_for_timeout(200)
                                    await page.keyboard.type(str(c_item['unit_price']))
                                    await page.keyboard.press("Enter")
                                    await page.wait_for_timeout(200)
                                    
                                # 다음 항목을 위해 대기
                                await page.wait_for_timeout(500)
                            print("   [안내] 품목 추가 작업이 끝났습니다. 화면에서 직접 세부 내용을 수정해 주세요.")
                    elif current_event_type == 'next':
                        print("   [안내] 수동 작성이 완료되었습니다. 리포트를 저장합니다.")
                        break
                
                entry['status'] = '수동완료'
            
        except Exception as e:
            print(f"[오류] 자동화 진행 중 문제 발생: {e}")
            entry['status'] = '실패'
            entry['fail_reason'] = str(e)
            
    results.append(entry)
    return results
