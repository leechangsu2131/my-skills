import requests
import urllib.parse
from bs4 import BeautifulSoup
import re
import os
import sys
import time

# =====================================================
# .env 파일에서 환경변수 로드 (같은 폴더의 .env 파일)
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
# =====================================================

# 노션 DB의 컬럼(속성) 이름
COL_TITLE = "제목"
COL_AUTHOR = "저자"
COL_LIBRARY = "도서관"
COL_ISBN = "ISBN"
COL_BOOKSTORE_URL = "서점URL"

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


def fetch_all_pages():
    """노션 DB의 모든 페이지를 페이지네이션으로 가져옵니다."""
    all_results = []
    payload = {"page_size": 100}
    while True:
        response = call_notion_api('POST', f"databases/{DATABASE_ID}/query", payload)
        if not response:
            break
        all_results.extend(response.get('results', []))
        if not response.get('has_more'):
            break
        payload['start_cursor'] = response['next_cursor']
    return all_results


# =====================================================
# 서점 검색 (교보문고 — 구조화된 데이터에서 ISBN + 상품URL 추출)
# =====================================================
def _normalize(text):
    """비교를 위해 텍스트를 정규화합니다 (공백/특수문자 제거, 소문자)."""
    return re.sub(r'[\s\-·:,.\[\]()]+', '', text).lower()


def _title_score(search_title, result_title):
    """두 제목의 유사도 점수를 계산합니다 (0.0 ~ 1.0)."""
    a = _normalize(search_title)
    b = _normalize(result_title)
    if not a or not b:
        return 0.0
    # 정확히 일치
    if a == b:
        return 1.0
    # 한쪽이 다른 쪽을 포함
    if a in b or b in a:
        return 0.8
    # 공통 글자 비율
    common = sum(1 for c in a if c in b)
    return common / max(len(a), len(b))


def search_bookstore(title, author):
    """
    교보문고에서 제목+저자로 검색하여 ISBN-13과 상품 페이지 URL을 추출합니다.

    매칭 전략:
    1. 검색 결과의 input.result_checkbox에서 data-bid(ISBN), data-name(제목),
       data-pid(상품ID) 구조화된 데이터를 추출합니다.
    2. 전자책(ebook)은 제외하고 종이책만 대상으로 합니다.
    3. 제목 유사도 + 저자 매칭으로 가장 정확한 결과를 선택합니다.

    Returns:
        tuple: (isbn, product_url) 또는 (None, None)
    """
    keyword = f"{title} {author}".strip()
    url = f"https://search.kyobobook.co.kr/search?keyword={urllib.parse.quote(keyword)}"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')

        # 구조화된 검색 결과 추출
        checkboxes = soup.select('input.result_checkbox')
        if not checkboxes:
            # 폴백: 기존 regex 방식
            isbns = re.findall(r'(97[89]\d{10})', r.text)
            isbn = isbns[0] if isbns else None
            pids = re.findall(r'https://product\.kyobobook\.co\.kr/detail/(\w+)', r.text)
            purl = f"https://product.kyobobook.co.kr/detail/{pids[0]}" if pids else None
            return isbn, purl

        candidates = []
        for cb in checkboxes:
            isbn = cb.get('data-bid', '')
            name = cb.get('data-name', '')
            pid = cb.get('data-pid', '')

            # ISBN-13만 (97x로 시작하는 13자리) → 전자책 ISBN(480x)은 제외
            if not isbn.startswith(('978', '979')):
                continue
            # ebook 상품 ID는 E로 시작 → 제외
            if pid.startswith('E'):
                continue

            prod_url = f"https://product.kyobobook.co.kr/detail/{pid}"

            # 제목 유사도 점수
            score = _title_score(title, name)

            # 해당 항목(li.prod_item) 내에서 저자 텍스트 확인
            parent_item = cb.find_parent('li', class_='prod_item')
            author_text = ''
            if parent_item:
                author_el = parent_item.select_one('.author')
                if author_el:
                    author_text = author_el.get_text(strip=True)

            # 저자가 지정되었고 검색 결과에 저자가 포함되어 있으면 보너스
            if author and author_text and _normalize(author) in _normalize(author_text):
                score += 0.3

            candidates.append({
                'isbn': isbn,
                'name': name,
                'url': prod_url,
                'author': author_text,
                'score': score,
            })

        if not candidates:
            return None, None

        # 점수 기준 정렬 (동점이면 검색 결과 순서대로 — 교보 기본 정렬)
        candidates.sort(key=lambda x: x['score'], reverse=True)

        best = candidates[0]

        # 디버그: 비슷한 점수의 후보가 여러 개면 경고
        if len(candidates) > 1 and candidates[1]['score'] >= 0.8:
            close_matches = [c for c in candidates if c['score'] >= 0.8]
            if len(close_matches) > 1:
                print(f"  ⚠ 유사 결과 {len(close_matches)}개 발견:")
                for c in close_matches[:3]:
                    print(f"    [{c['name']}] ISBN:{c['isbn']} 저자:{c['author']} (점수:{c['score']:.1f})")
                print(f"    → 최상위 선택: [{best['name']}]")

        return best['isbn'], best['url']

    except Exception as e:
        print(f"  서점 통신 오류: {e}")
        return None, None


# =====================================================
# 경주시립도서관 검색
# =====================================================
def check_gyeongju_library(isbn):
    """
    경주시립도서관에서 ISBN으로 검색 후 소장 지점을 파악합니다.
    각 결과 항목의 전체 텍스트에서 지점명 키워드를 직접 탐지합니다.

    판단 기준:
    - '전자책' (청구기호) + '[시립]홈페이지' (자료실) → 전자
    - '송화'  → 송화
    - '단석'  → 단석
    - '칠평'  → 칠평
    - 나머지 (본관, 시립 등) → 시립
    """
    url = f"https://library.gyeongju.go.kr/?page_id=search_booklist&mode=tBookList&search_txt={isbn}&display=50"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')

        items = soup.select('div.bif')
        if not items:
            return None

        found_tags = set()
        for item in items:
            full_text = item.get_text(separator=' ', strip=True)

            if '전자책' in full_text or '홈페이지' in full_text:
                found_tags.add('전자')
            elif '송화' in full_text:
                found_tags.add('송화')
            elif '단석' in full_text:
                found_tags.add('단석')
            elif '칠평' in full_text:
                found_tags.add('칠평')
            else:
                found_tags.add('시립')

        return [{'name': t} for t in found_tags] if found_tags else None

    except Exception as e:
        print(f"  도서관 통신 오류: {e}")
        return None


# =====================================================
# 노션 업데이트
# =====================================================
def update_page(page_id, valid_columns, library_tags=None, isbn=None, bookstore_url=None):
    """노션 페이지에 도서관 태그, ISBN, 서점URL을 업데이트합니다."""
    properties = {}

    if library_tags is not None and COL_LIBRARY in valid_columns:
        properties[COL_LIBRARY] = {"multi_select": library_tags}

    if isbn and COL_ISBN in valid_columns:
        properties[COL_ISBN] = {
            "rich_text": [{"text": {"content": isbn}}]
        }

    if bookstore_url and COL_BOOKSTORE_URL in valid_columns:
        properties[COL_BOOKSTORE_URL] = {
            "url": bookstore_url
        }

    if properties:
        call_notion_api('PATCH', f"pages/{page_id}", {"properties": properties})


def extract_text_from_property(prop):
    if not prop:
        return ""
    if prop['type'] == 'title':
        return "".join(t.get('plain_text', '') for t in prop.get('title', [])).strip()
    elif prop['type'] == 'rich_text':
        return "".join(t.get('plain_text', '') for t in prop.get('rich_text', [])).strip()
    elif prop['type'] == 'url':
        return prop.get('url', '') or ''
    return ""


# =====================================================
# 메인 실행
# =====================================================
def main():
    if not NOTION_TOKEN:
        print("ERROR: NOTION_TOKEN이 설정되지 않았습니다.")
        print(".env 파일에 NOTION_TOKEN=secret_... 형태로 추가해주세요.")
        sys.exit(1)

    # 노션 DB 구조 확인 (컬럼 유무 확인)
    print("▶ 노션 DB 컬럼 조회 중...")
    db_info = call_notion_api('GET', f"databases/{DATABASE_ID}")
    valid_columns = list(db_info.get('properties', {}).keys()) if db_info else []
    if not valid_columns:
        print("API 호출 실패로 DB 정보를 가져오지 못했습니다. 종료합니다.")
        return
    
    if COL_BOOKSTORE_URL not in valid_columns:
        print(f"  ⚠ '{COL_BOOKSTORE_URL}' 속성이 노션에 존재하지 않습니다. 저장을 건너뜁니다.")

    # 노션 DB의 모든 책 목록 가져오기 (페이지네이션 지원)
    print("▶ 노션 DB에서 책 목록 조회 중...")
    results = fetch_all_pages()

    if not results:
        print("API 호출 실패 또는 데이터 없음. 종료합니다.")
        return

    print(f"  총 {len(results)}권 발견\n")
    print("=" * 55)
    print("▶ 도서관 검색 시작...")
    print("=" * 55)

    # 미소장 도서 추적
    not_in_library = []
    updated_count = 0
    skipped_count = 0

    for page in results:
        props = page.get('properties', {})
        page_id = page['id']

        if COL_TITLE not in props:
            continue

        title = extract_text_from_property(props[COL_TITLE])
        author = extract_text_from_property(props.get(COL_AUTHOR, {}))

        if not title:
            continue

        # 이미 ISBN이 입력된 책은 서점 검색 건너뛰기 (도서관 검색은 재수행)
        existing_isbn = extract_text_from_property(props.get(COL_ISBN, {}))
        existing_url = extract_text_from_property(props.get(COL_BOOKSTORE_URL, {}))

        print(f"\n[검색] {title}" + (f" / {author}" if author else ""))

        # 1. 서점에서 ISBN + URL 검색
        if existing_isbn:
            isbn = existing_isbn
            bookstore_url = existing_url
            print(f"  -> ISBN 기존값 사용: {isbn}")
        else:
            isbn, bookstore_url = search_bookstore(title, author)
            if not isbn:
                print("  -> ISBN 파싱 실패")
                skipped_count += 1
                continue
            print(f"  -> ISBN: {isbn}")
            if bookstore_url:
                print(f"  -> 서점: {bookstore_url}")
            time.sleep(0.5)  # 서점 서버 부담 완화

        # 2. 도서관 소장 확인
        tags = check_gyeongju_library(isbn)

        if tags:
            names = [t['name'] for t in tags]
            print(f"  -> 소장처: {names}")
            update_page(page_id, valid_columns, library_tags=tags, isbn=isbn, bookstore_url=bookstore_url)
        else:
            print("  -> 경주시립도서관 미소장")
            # 미소장 태그 추가
            not_found_tag = [{'name': '미소장'}]
            update_page(page_id, valid_columns, library_tags=not_found_tag, isbn=isbn, bookstore_url=bookstore_url)
            not_in_library.append({
                'title': title,
                'author': author,
                'isbn': isbn,
                'bookstore_url': bookstore_url,
                'page_id': page_id,
            })

        updated_count += 1
        time.sleep(0.3)  # 도서관 서버 부담 완화

    # 최종 요약
    print("\n" + "=" * 55)
    print("✅ 모든 작업 완료!")
    print(f"  처리: {updated_count}권 | 스킵(ISBN 실패): {skipped_count}권")

    if not_in_library:
        print(f"\n📋 미소장 도서 목록 ({len(not_in_library)}권):")
        print("-" * 55)
        for book in not_in_library:
            label = book['title']
            if book['author']:
                label += f" / {book['author']}"
            print(f"  • {label}")
            if book['isbn']:
                print(f"    ISBN: {book['isbn']}")
            if book['bookstore_url']:
                print(f"    서점: {book['bookstore_url']}")
        print("-" * 55)
        print(f"  → 희망도서 신청이 필요한 도서: {len(not_in_library)}권")
        print(f"  → request_books.py 로 신청할 수 있습니다.")


if __name__ == "__main__":
    main()
