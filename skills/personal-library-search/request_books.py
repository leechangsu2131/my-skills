import os
import sys
import time
import argparse
import requests

# =====================================================
# .env 파일에서 환경변수 로드
# =====================================================
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, val = line.partition('=')
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

load_env()

NOTION_TOKEN = os.environ.get('NOTION_TOKEN', '')
DATABASE_ID = os.environ.get('NOTION_DATABASE_ID', '')

# 노션 DB 컬럼 이름
COL_TITLE = "제목"
COL_AUTHOR = "저자"
COL_LIBRARY = "도서관"
COL_ISBN = "ISBN"

# 경주시립도서관 URL
LOGIN_URL = "https://library.gyeongju.go.kr/?page_id=account_login"
REQUEST_URL = "https://library.gyeongju.go.kr/?page_id=search_hbook&mode=hBookRegist"


# =====================================================
# 도서관 계정 관리
# =====================================================
def load_library_accounts():
    """
    .env에서 도서관 계정 목록을 로드합니다.
    형식: LIBRARY_ACCOUNT_1_ID, LIBRARY_ACCOUNT_1_PW, LIBRARY_ACCOUNT_2_ID, ...
    """
    accounts = []
    for i in range(1, 11):  # 최대 10개 계정
        uid = os.environ.get(f'LIBRARY_ACCOUNT_{i}_ID', '')
        pwd = os.environ.get(f'LIBRARY_ACCOUNT_{i}_PW', '')
        if uid and pwd:
            accounts.append({'id': uid, 'pw': pwd})
    return accounts


# =====================================================
# 노션 API 헬퍼
# =====================================================
def call_notion_api(method, endpoint, payload=None):
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    url = f"https://api.notion.com/v1/{endpoint}"
    if method == 'POST':
        r = requests.post(url, headers=headers, json=payload)
    elif method == 'PATCH':
        r = requests.patch(url, headers=headers, json=payload)
    else:
        r = requests.get(url, headers=headers)
    if r.status_code not in (200, 201):
        print(f"[노션 API 오류] {r.status_code}: {r.text[:200]}")
        return None
    return r.json()


def extract_text_from_property(prop):
    if not prop:
        return ""
    if prop['type'] == 'title':
        return "".join(t.get('plain_text', '') for t in prop.get('title', [])).strip()
    elif prop['type'] == 'rich_text':
        return "".join(t.get('plain_text', '') for t in prop.get('rich_text', [])).strip()
    return ""


def get_books_to_request(title_filter=None):
    """노션 DB에서 책 목록을 가져옵니다. title_filter가 없면 '미소장' 태그만 가져옵니다."""
    books = []
    
    # title_filter가 지정된 경우 필터 제거 (모든 도서 중 검색)
    if title_filter:
        payload = {"page_size": 100}
    else:
        payload = {
            "page_size": 100,
            "filter": {
                "property": COL_LIBRARY,
                "multi_select": {
                    "contains": "미소장"
                }
            }
        }
        
    while True:
        response = call_notion_api('POST', f"databases/{DATABASE_ID}/query", payload)
        if not response:
            break
        for page in response.get('results', []):
            props = page.get('properties', {})
            title = extract_text_from_property(props.get(COL_TITLE, {}))
            author = extract_text_from_property(props.get(COL_AUTHOR, {}))
            isbn = extract_text_from_property(props.get(COL_ISBN, {}))
            
            if title:
                # title_filter가 있으면 필터링
                if title_filter and title_filter.lower() not in title.lower():
                    continue
                    
                books.append({
                    'title': title,
                    'author': author,
                    'isbn': isbn,
                    'page_id': page['id'],
                })
        if not response.get('has_more'):
            break
        payload['start_cursor'] = response['next_cursor']
    return books


def update_notion_tag(page_id, tag_name):
    """노션 페이지의 도서관 태그를 업데이트합니다."""
    payload = {
        "properties": {
            COL_LIBRARY: {
                "multi_select": [{"name": tag_name}]
            }
        }
    }
    call_notion_api('PATCH', f"pages/{page_id}", payload)

def update_notion_status(page_id, status_text):
    """노션 페이지의 신청현황(select)을 업데이트합니다."""
    payload = {
        "properties": {
            "신청현황": {
                "select": {"name": status_text}
            }
        }
    }
    call_notion_api('PATCH', f"pages/{page_id}", payload)

# =====================================================
# Playwright 기반 희망도서 신청
# =====================================================
async def login(page, account):
    """경주시립도서관 로그인"""
    await page.goto(LOGIN_URL, wait_until='networkidle')
    await page.fill('#login_id', account['id'])
    await page.fill('#login_pass', account['pw'])
    await page.click('#save-btn')
    await page.wait_for_load_state('networkidle')

    # 로그인 성공 확인 (로그인 페이지에 남아있으면 실패)
    current_url = page.url
    if 'account_login' in current_url:
        return False
    return True


async def request_book(page, book, dry_run=False):
    """
    희망도서 신청 페이지에서 수동입력 방식으로 책을 신청합니다.

    Returns:
        str: 'success', 'limit_reached', 'error'
    """
    try:
        # 팝업/모달(alert) 텍스트를 담을 변수
        dialog_message = ""
        
        async def handle_dialog(dialog):
            nonlocal dialog_message
            msg = dialog.message
            print(f"  [안내 팝업] {msg}")
            try:
                await dialog.accept()
            except Exception:
                pass
            # 단순 확인용 팝업은 결과 판별에서 제외
            if '신청하시겠습니까' not in msg:
                dialog_message = msg

        page.on("dialog", handle_dialog)

        # 페이지 진입 및 확인 로직 (기존과 동일)
        await page.goto(REQUEST_URL, wait_until='networkidle')
        await page.wait_for_timeout(1000)

        # 페이지 진입 시 조기 차단 팝업(한도 초과 등)이 뜨는 경우 확인
        if dialog_message:
            if '신청권수는' in dialog_message or '초과' in dialog_message or '2권' in dialog_message:
                print(f"  ⚠ 이 계정의 월 신청 한도에 도달했습니다. ({dialog_message})")
                return 'limit_reached'
            elif '개인정보' in dialog_message or '동의' in dialog_message:
                print(f"  ⚠ 개인정보 동의 필요: {dialog_message}")
                return 'consent_required'
            else:
                pass

        # 제목 입력
        title_input = page.locator('input[name="book_title"], input[name="book_name"]')
        if await title_input.count() > 0:
            await title_input.first.fill(book['title'])
        else:
            print("  ⚠ 제목 입력 필드를 찾을 수 없습니다.")
            return 'error'

        # 저자 입력
        author_input = page.locator('input[name="book_author"], input[name="author"]')
        if await author_input.count() > 0 and book.get('author'):
            await author_input.first.fill(book['author'])

        # 출판사, 출판년도, 가격 입력
        pub_input = page.locator('input[name="publisher"]')
        if await pub_input.count() > 0:
            await pub_input.first.fill('기타')
        
        date_input = page.locator('input[name="publisher_date"]')
        if await date_input.count() > 0:
            await date_input.first.fill('2024')
            
        price_input = page.locator('input[name="price"]')
        if await price_input.count() > 0:
            await price_input.first.fill('15000')

        # ISBN 입력
        isbn_input = page.locator('input[name="isbn"]')
        if await isbn_input.count() > 0:
            await isbn_input.first.fill(book.get('isbn') or '0000000000000')
            
        # 신청도서관 선택 (송화도서관 우선)
        lib_select = page.locator('select[name="manage_code"]')
        if await lib_select.count() > 0:
            options = await lib_select.locator('option').all()
            selected = False
            for opt in options:
                text = await opt.inner_text()
                val = await opt.get_attribute('value')
                if val and '송화' in text:
                    await lib_select.select_option(value=val)
                    selected = True
                    break
            
            if not selected:
                for opt in options:
                    val = await opt.get_attribute('value')
                    if val:
                        await lib_select.select_option(value=val)
                        break

        if dry_run:
            print(f"  🔍 [DRY-RUN] 신청 폼 작성 완료 (실제 신청 안 함)")
            await page.screenshot(path=os.path.join(os.path.dirname(__file__), 'dry_run_screenshot.png'))
            return 'dry_run'

        # 개인정보 수집/이용 동의 체크박스 확인
        agree_checkbox = page.locator('input[type="checkbox"][name="agree"], input[type="checkbox"]#agree')
        if await agree_checkbox.count() > 0:
            if not await agree_checkbox.first.is_checked():
                await agree_checkbox.first.check()
                print("  📝 개인정보 수집/이용 동의 체크 완료")

        # 신청하기 버튼 클릭
        submit_btn = page.locator('button:has-text("신청"), input[type="submit"][value*="신청"], a:has-text("신청하기")')
        if await submit_btn.count() > 0:
            await submit_btn.first.click()
            await page.wait_for_timeout(2000)

            # 팝업 메시지가 있으면 팝업 내용으로 판별
            if dialog_message:
                if '제한' in dialog_message or '초과' in dialog_message or '2권' in dialog_message or '신청권수는' in dialog_message:
                    print(f"  ⚠ 이 계정의 월 신청 한도에 도달했습니다.")
                    return 'limit_reached'
                elif '소장' in dialog_message:
                    print("  ⚠ 이미 도서관에 소장 중인 도서입니다.")
                    return 'already_owned'
                elif '이미 신청' in dialog_message:
                    print("  ⚠ 이미 누군가 희망도서로 신청하여 처리 중인 도서입니다.")
                    return 'already_requested'
                elif '개인정보' in dialog_message or '동의' in dialog_message:
                    print("  ⚠ 도서관 홈페이지 로그인 후 개인정보 수집/이용 동의가 필요합니다.")
                    return 'consent_required'
                elif '완료' in dialog_message or '접수' in dialog_message or '성공' in dialog_message or '신청되었습니다' in dialog_message:
                    return 'success'
                else:
                    print(f"  ⚠ 기타 팝업 메시지 수신: {dialog_message}")
                    return 'error'

            # 팝업이 안 떴다면 페이지 내용물로 확인
            body_text = await page.inner_text('body')

            if '신청이 완료' in body_text or '정상적으로 접수' in body_text:
                return 'success'

        print("  ⚠ 신청 버튼을 찾을 수 없거나 결과를 알 수 없습니다.")
        return 'error'

    except Exception as e:
        print(f"  ❌ 신청 중 오류: {e}")
        return 'error'
        
    finally:
        # 이벤트 리스너 제거 (다중 호출 시 중복 등록 방지)
        try:
            page.remove_listener("dialog", handle_dialog)
        except Exception:
            pass


async def run_requests(books, accounts, max_books=None, dry_run=False):
    """메인 신청 루프"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: playwright가 설치되지 않았습니다.")
        print("  pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)

    if not accounts:
        print("ERROR: 도서관 계정이 설정되지 않았습니다.")
        print(".env 파일에 LIBRARY_ACCOUNT_1_ID, LIBRARY_ACCOUNT_1_PW를 추가해주세요.")
        sys.exit(1)

    if max_books:
        books = books[:max_books]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        account_idx = 0
        requested = 0
        account_request_count = 0

        # 첫 번째 계정으로 로그인
        print(f"\n🔑 계정 {account_idx + 1} ({accounts[account_idx]['id']}) 로그인 중...")
        if not await login(page, accounts[account_idx]):
            print(f"  ❌ 로그인 실패: {accounts[account_idx]['id']}")
            await browser.close()
            return

        print(f"  ✅ 로그인 성공")

        for book in books:
            label = book['title']
            if book.get('author'):
                label += f" / {book['author']}"
            print(f"\n📖 [{label}]")

            result = await request_book(page, book, dry_run=dry_run)

            if result == 'success':
                requested += 1
                account_request_count += 1
                print(f"  ✅ 신청 완료 ({account_request_count}/2)")
                # 노션 태그 및 현황 업데이트
                update_notion_tag(book['page_id'], '신청완료')
                update_notion_status(book['page_id'], '송화도서관 신청')

            elif result == 'limit_reached':
                # 다음 계정으로 전환
                account_idx += 1
                if account_idx >= len(accounts):
                    print(f"\n⚠ 모든 계정의 신청 한도에 도달했습니다.")
                    break

                account_request_count = 0
                print(f"\n🔄 계정 전환: {accounts[account_idx]['id']}")

                # 로그아웃 후 재로그인
                await page.goto("https://library.gyeongju.go.kr/?page_id=account_logout",
                                wait_until='networkidle')
                if not await login(page, accounts[account_idx]):
                    print(f"  ❌ 로그인 실패: {accounts[account_idx]['id']}")
                    break
                print(f"  ✅ 로그인 성공")

                # 현재 책 다시 신청 시도
                result = await request_book(page, book, dry_run=dry_run)
                if result == 'success':
                    requested += 1
                    account_request_count += 1
                    print(f"  ✅ 신청 완료 ({account_request_count}/2)")
                    update_notion_tag(book['page_id'], '신청완료')
                    update_notion_status(book['page_id'], '송화도서관 신청')

            elif result == 'dry_run':
                requested += 1

            elif result == 'error':
                print(f"  ⚠ 건너뜀")

            time.sleep(1)

        await browser.close()

    print(f"\n{'=' * 55}")
    mode_str = "[DRY-RUN] " if dry_run else ""
    print(f"✅ {mode_str}총 {requested}권 처리 완료")


# =====================================================
# CLI 엔트리포인트
# =====================================================
def main():
    parser = argparse.ArgumentParser(
        description='경주시립도서관 희망도서 신청 자동화'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='실제 신청 없이 폼 확인만 수행')
    parser.add_argument('--max-books', type=int, default=None,
                        help='한 번 실행에 최대 신청 권수')
    parser.add_argument('--title', type=str, default=None,
                        help='특정 제목이 포함된 도서만 신청')
    args = parser.parse_args()

    if not NOTION_TOKEN:
        print("ERROR: NOTION_TOKEN이 설정되지 않았습니다.")
        sys.exit(1)

    # 도서관 계정 로드
    accounts = load_library_accounts()
    print(f"📚 도서관 계정 {len(accounts)}개 로드됨")

    # 미소장 도서 목록 가져오기 (특정 도서 지정 시 해당 도서만)
    print("▶ 노션 DB에서 도서 조회 중...")
    books = get_books_to_request(title_filter=args.title)
    
    # 제목 필터 적용
    if args.title:
        books = [b for b in books if args.title.lower() in b['title'].lower()]
        print(f"  제목 '{args.title}' 필터 적용됨")
    
    print(f"  {len(books)}권 발견")

    if not books:
        print("신청할 도서가 없습니다.")
        return

    if args.dry_run:
        print("\n⚠ DRY-RUN 모드: 실제 신청을 하지 않습니다.")

    import asyncio
    asyncio.run(run_requests(
        books,
        accounts,
        max_books=args.max_books,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()
