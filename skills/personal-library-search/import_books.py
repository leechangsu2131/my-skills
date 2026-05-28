import os
import sys
import argparse
import re
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
old_request = requests.Session.request
def new_request(*args, **kwargs):
    kwargs['verify'] = False
    return old_request(*args, **kwargs)
requests.Session.request = new_request

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

def add_book_to_notion(title, author, url=""):
    """새로운 책을 노션 데이터베이스에 추가합니다."""
    if not NOTION_TOKEN or not DATABASE_ID:
        print("⚠ NOTION_TOKEN 또는 NOTION_DATABASE_ID가 없어 노션에 추가할 수 없습니다.")
        return False
        
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "제목": {
                "title": [
                    {"text": {"content": title}}
                ]
            }
        }
    }
    
    if author:
        payload["properties"]["저자"] = {
            "rich_text": [
                {"text": {"content": author}}
            ]
        }
        
    if url:
        payload["properties"]["서점URL"] = {
            "url": url if url.startswith('http') else f"https://{url}"
        }
        
    response = call_notion_api('POST', 'pages', payload)
    if response:
        print(f"✅ 노션에 추가됨: {title}")
        return True
    return False

def parse_text_file(filepath):
    """텍스트 파일을 읽어 도서 정보와 쿠팡 URL을 추출합니다."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # URL 찾기
    url_pattern = re.compile(r'(https?://[^\s]+|link\.coupang\.com[^\s]+)')
    
    # 텍스트를 줄 단위로 분리하고 정리
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    books = []
    current_title_author = ""
    
    for line in lines:
        match = url_pattern.search(line)
        if match:
            url = match.group(1)
            # URL을 찾으면 그 이전까지 수집한 텍스트를 제목/저자로 사용 (재고 한정 같은 불필요한 단어 제거)
            text_info = current_title_author.replace("재고 한정", "").strip()
            
            # 저자 분리 시도 (단순 휴리스틱: 마지막 공백 이후 단어를 저자나 출판사로 취급)
            parts = text_info.rsplit(' ', 1)
            title = text_info
            author = ""
            if len(parts) == 2:
                # 마지막 단어가 이형수, 지베르니 등일 가능성 높음. 정확도를 위해 통으로 처리하거나 나눔
                # 여기서는 전체를 제목+저자 문자열로 처리하고, 검색기가 알아서 찾게 함
                title = text_info
            
            books.append({
                "raw_text": text_info,
                "title": title,
                "author": "", # 저자는 raw_text에 포함됨
                "url": url
            })
            current_title_author = "" # 초기화
        else:
            if current_title_author:
                current_title_author += " " + line
            else:
                current_title_author = line
                
    return books

def main():
    parser = argparse.ArgumentParser(description="텍스트 파일에서 도서 정보 및 쿠팡 URL을 추출하여 노션에 추가")
    parser.add_argument('input_file', help="텍스트 파일 경로")
    parser.add_argument('--dry-run', action='store_true', help="노션에 추가하지 않고 파싱 결과만 출력")
    args = parser.parse_args()
    
    books = parse_text_file(args.input_file)
    print(f"총 {len(books)}권의 책 정보를 추출했습니다.\n")
    
    for idx, book in enumerate(books, 1):
        print(f"[{idx}] 텍스트: {book['raw_text']}")
        print(f"    URL: {book['url']}")
        
        if not args.dry_run:
            add_book_to_notion(book['title'], book['author'], book['url'])
            
if __name__ == "__main__":
    main()
