import requests
import urllib.parse
from bs4 import BeautifulSoup
import re
import os
import sys

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

## =====================================================
## [수동 등록용] 신규 책 목록 - 책 등록은 노션에서 직접 수행
## 아래 목록을 사용하려면 main()의 '신규 책 등록' 블록 주석을 해제하세요
##
## NEW_BOOKS = [
##     ("가장 사업처럼 하는 투자", ""),
##     ("주주 행동주의", ""),
##     ("할말하는 주주", ""),
##     ("수레바퀴 아래서", "헤르만 헤세"),
##     ("한반도 슈퍼사이클", ""),
##     ("나의 조용한 전쟁", ""),
##     ("아틀라스", ""),
##     ("생각하라 그리고 부자가 되어라", "나폴레온 힐"),
##     ("Fluent Forever", "Gabriel Wyner"),
##     ("부자는 자본주의를 어떻게 읽고 있는가", ""),
##     ("물질의 세계", ""),
##     ("사할린 섬", "안톤 체호프"),
##     ("세컨드 브레인 전쟁", ""),
##     ("투자의 새로운 규칙", ""),
## ]
## =====================================================

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

## =====================================================
## [수동 등록용 함수들] - 아래 함수들은 책 등록 시에만 사용됩니다.
##
## def create_notion_page(title, author):
##     """노션 DB에 새 책 페이지 생성"""
##     payload = {
##         "parent": {"database_id": DATABASE_ID},
##         "properties": {
##             COL_TITLE: {"title": [{"text": {"content": title}}]}
##         }
##     }
##     if author:
##         payload["properties"][COL_AUTHOR] = {
##             "rich_text": [{"text": {"content": author}}]
##         }
##     result = call_notion_api('POST', "pages", payload)
##     return result['id'] if result else None
##
## def get_existing_titles():
##     """이미 DB에 등록된 책 제목 목록 가져오기"""
##     payload = {"page_size": 100}
##     response = call_notion_api('POST', f"databases/{DATABASE_ID}/query", payload)
##     if not response:
##         return set()
##     titles = set()
##     for page in response.get('results', []):
##         prop = page.get('properties', {}).get(COL_TITLE)
##         if prop and prop.get('title'):
##             t = "".join(x.get('plain_text', '') for x in prop['title']).strip()
##             if t:
##                 titles.add(t)
##     return titles
## =====================================================

def search_kyobo(title, author):
    keyword = f"{title} {author}".strip()
    url = f"https://search.kyobobook.co.kr/search?keyword={urllib.parse.quote(keyword)}"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        isbns = re.findall(r'(97[89]\d{10})', r.text)
        return isbns[0] if isbns else None
    except Exception as e:
        print(f"  교보 통신 오류: {e}")
        return None

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
            # 각 항목의 전체 텍스트를 하나로 합쳐서 키워드 탐지
            full_text = item.get_text(separator=' ', strip=True)

            # 전자책 판별: '전자책' 키워드 또는 '홈페이지' 자료실
            if '전자책' in full_text or '홈페이지' in full_text:
                found_tags.add('전자')
            # 지점별 키워드 직접 매칭
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

def update_library_tags(page_id, tags):
    payload = {"properties": {COL_LIBRARY: {"multi_select": tags}}}
    call_notion_api('PATCH', f"pages/{page_id}", payload)

def extract_text_from_property(prop):
    if not prop: return ""
    if prop['type'] == 'title':
        return "".join(t.get('plain_text', '') for t in prop.get('title', [])).strip()
    elif prop['type'] == 'rich_text':
        return "".join(t.get('plain_text', '') for t in prop.get('rich_text', [])).strip()
    return ""

def main():
    if not NOTION_TOKEN:
        print("ERROR: NOTION_TOKEN이 설정되지 않았습니다.")
        print(".env 파일에 NOTION_TOKEN=secret_... 형태로 추가해주세요.")
        sys.exit(1)

    # 노션 DB의 모든 책 목록 가져오기
    print("▶ 노션 DB에서 책 목록 조회 중...")
    payload = {"page_size": 100}
    response = call_notion_api('POST', f"databases/{DATABASE_ID}/query", payload)

    if not response:
        print("API 호출 실패로 종료합니다.")
        return

    results = response.get('results', [])
    print(f"  총 {len(results)}권 발견\n")
    print("=" * 50)
    print("▶ 도서관 검색 시작...")
    print("=" * 50)

    ## =====================================================
    ## [신규 책 등록 블록] - 직접 등록 시에만 주석 해제
    ##
    ## print("▶ 신규 책 등록 중...")
    ## existing = get_existing_titles()
    ## for title, author in NEW_BOOKS:
    ##     if title in existing:
    ##         print(f"[SKIP] '{title}' 이미 등록됨")
    ##         continue
    ##     pid = create_notion_page(title, author)
    ##     print(f"[등록] '{title}' -> {'완료' if pid else '실패'}")
    ## =====================================================

    for page in results:
        props = page.get('properties', {})
        page_id = page['id']

        if COL_TITLE not in props:
            continue

        title = extract_text_from_property(props[COL_TITLE])
        author = extract_text_from_property(props.get(COL_AUTHOR, {}))

        if not title:
            continue

        print(f"\n[검색] {title}" + (f" / {author}" if author else ""))

        isbn = search_kyobo(title, author)
        if not isbn:
            print("  -> ISBN 파싱 실패")
            continue
        print(f"  -> ISBN: {isbn}")

        tags = check_gyeongju_library(isbn)
        if tags:
            names = [t['name'] for t in tags]
            print(f"  -> 소장처: {names}")
            update_library_tags(page_id, tags)
        else:
            print("  -> 경주시립도서관 미소장")

    print("\n✅ 모든 작업 완료!")

if __name__ == "__main__":
    main()
