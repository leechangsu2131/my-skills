import requests
import urllib.parse
from bs4 import BeautifulSoup
import re
import os
import sys

# === [사용자 설정 영역] ===
# 환경변수에서 로드 (없는 경우 아래 기본값 또는 .env 파일 활용)
NOTION_TOKEN = os.getenv('NOTION_TOKEN', 'YOUR_NOTION_INTEGRATION_TOKEN_HERE')
DATABASE_ID = os.getenv('NOTION_DATABASE_ID', '313ddde1e1df80e9b161e2c5888f80d6')

# 노션 테이블의 속성(Column) 이름 세팅 (제공해주신 스크린샷 기준)
COL_TITLE = "제목"       # 읽을 책 제목 (Title 유형)
COL_AUTHOR = "저자"       # 읽을 책 저자 (텍스트 유형)
COL_LIBRARY = "도서관"   # 기록할 소장처 (다중선택/Multi-select 유형)
# ========================

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
        
    if r.status_code != 200:
        print(f"[노션 API 오류] {r.status_code}: {r.text}")
        return None
    return r.json()

def search_kyobo(title, author):
    keyword = f"{title} {author}".strip()
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://search.kyobobook.co.kr/search?keyword={encoded_keyword}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        isbns = re.findall(r'(97[89]\d{10})', r.text)
        if isbns:
            return isbns[0]
    except Exception as e:
        print(f"교보문고 서버 통신 오류: {e}")
        
    return None

def extract_library_tags(lib_names):
    """
    도서관 풀네임을 노션의 '도서관' 다중선택 태그 이름('시립', '전자', '송화', '단석')으로 매핑합니다.
    """
    tags = []
    for name in lib_names:
        if '단석' in name:
            tags.append({'name': '단석'})
        elif '송화' in name:
            tags.append({'name': '송화'})
        elif '전자' in name or '오디오북' in name or '웹진' in name:
            tags.append({'name': '전자'})
        else:
            # 기본적으로 본관이나 기타 시립 지점은 '시립'으로 묶습니다.
            tags.append({'name': '시립'})
            
    # 중복되는 태그 이름 제거
    unique_tags = []
    seen = set()
    for t in tags:
        if t['name'] not in seen:
            unique_tags.append(t)
            seen.add(t['name'])
    return unique_tags

def check_gyeongju_library(isbn):
    url = f"https://library.gyeongju.go.kr/?page_id=search_booklist&mode=tBookList&search_txt={isbn}&display=10"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        items = soup.select('div.bif')
        if not items:
            return None

        branch_names = []
        for item in items:
            infos = item.select('p.book-status-info')
            for info in infos:
                text = info.text.strip()
                if '도서관' in text:
                    branch_names.append(text.split(':')[-1].strip())
                    
        return extract_library_tags(branch_names)
    except Exception as e:
        print(f"경주시립도서관 서버 통신 오류: {e}")
        return None

def extract_text_from_property(prop):
    text = ""
    if not prop: return text
    if prop['type'] == 'title':
        for t in prop.get('title', []):
            text += t.get('plain_text', '')
    elif prop['type'] == 'rich_text':
        for t in prop.get('rich_text', []):
            text += t.get('plain_text', '')
    return text.strip()

def update_notion_multi_select(page_id, tags):
    if not tags: return
    payload = {
        "properties": {
            COL_LIBRARY: {
                "multi_select": tags
            }
        }
    }
    call_notion_api('PATCH', f"pages/{page_id}", payload)

def main():
    if NOTION_TOKEN.startswith('YOUR'):
        print("ERROR: 환경변수 또는 스크립트 상단의 NOTION_TOKEN을 실제 토큰 값으로 설정해주세요.")
        sys.exit(1)
        
    print("노션 데이터베이스에서 책 목록을 불러옵니다...")
    payload = {"page_size": 100}
    response = call_notion_api('POST', f"databases/{DATABASE_ID}/query", payload)
    
    if not response:
        print("API 호출 실패로 종료합니다.")
        return
        
    results = response.get('results', [])
    print(f"총 {len(results)}건의 도서(페이지)를 발견했습니다.\n")
    
    for page in results:
        props = page.get('properties', {})
        page_id = page['id']
        
        if COL_TITLE not in props:
            continue
            
        title = extract_text_from_property(props[COL_TITLE])
        author = extract_text_from_property(props.get(COL_AUTHOR))
        
        if not title:
            continue
            
        print(f"▶ 검색 시작: [{title}] (저자: {author})")
        
        # 1. 서점 ISBN 검색
        isbn = search_kyobo(title, author)
        if not isbn:
            print("  --> (실패) 서점 검색 결과에서 ISBN 파싱 불가")
            continue
            
        # 2. 도서관 지점 탐색
        tags = check_gyeongju_library(isbn)
        
        if tags:
            tag_names = [t['name'] for t in tags]
            print(f"  --> (업데이트 완료) 발견된 도서관: {tag_names}")
            update_notion_multi_select(page_id, tags)
        else:
            print("  --> (소장안함) 시립도서관 소장 정보 없음")

    print("\n모든 처리가 완료되었습니다.")

if __name__ == "__main__":
    main()
