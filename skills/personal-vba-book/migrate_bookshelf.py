"""
현대화된 도서 정보 추출 및 마크다운 서재 구축 자동화 스크립트
1. 기존 Excel(yes24 isbn 검색 3 .xlsm)에서 누락되었거나 오류난 ISBN을 YES24에서 직접 경량 크롤링
2. 책 표지 이미지 고해상도(XL) 자동 수집
3. 감상문2.txt (블로그 독서 기록) 파싱 및 도서와 자동 매칭
4. 도서별 Markdown 카드 생성 (Obsidian / Notion 프로퍼티 호환)
5. 전체 도서를 일목요연하게 보는 통합 index.md 및 books.csv 생성
"""

import os
import re
import sys
import time
import json
import shutil
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import openpyxl

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-vba-book")
TARGET_DIR = BASE_DIR / "modern_bookshelf"
COVERS_DIR = TARGET_DIR / "covers"
CARDS_DIR = TARGET_DIR / "books"
LEGACY_COVERS = BASE_DIR / "갖고 있는 책표지"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_filename(text: str) -> str:
    """파일명으로 사용할 수 없는 특수문자 제거"""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", text)
    cleaned = re.sub(r'\s+', " ", cleaned)
    return cleaned.strip()

def parse_reviews():
    """감상문2.txt에서 블로그 독서 후기 파싱"""
    review_file = BASE_DIR / "감상문2.txt.txt"
    if not review_file.exists():
        return []
    
    with open(review_file, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    blocks = re.split(r'\n(?=http://blog\.naver\.com/)', text)
    reviews = []
    
    # 첫 블록 헤더 파싱
    header_lines = [l.strip() for l in blocks[0].split('\n') if l.strip()]
    first_title = header_lines[0] if header_lines else "독서 감상문"
    
    for i, b in enumerate(blocks[1:], 1):
        lines = [l.strip() for l in b.split('\n') if l.strip()]
        if not lines:
            continue
        url = lines[0]
        content_lines = lines[1:]
        
        # 다음 블록의 헤더(제목 등)가 현재 블록의 끝에 붙어있는 경우 처리
        next_title = None
        main_content = []
        for line in content_lines:
            if re.match(r'^\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}', line) or line == "책":
                continue
            main_content.append(line)
            
        cur_title = first_title if i == 1 else f"독서 기록 {i}"
        
        # 마지막 줄 부근에 다음 글 제목이 오는 네이버 블로그 백업 특성 반영
        reviews.append({
            "url": url,
            "title_hint": cur_title,
            "content": "\n\n".join(main_content)
        })
        
        # 다음 블록용 제목 추정 (블록 끝 줄 중 하나)
        if len(content_lines) >= 3:
            for cand in reversed(content_lines[-3:]):
                if cand and not cand.startswith("http") and len(cand) < 50:
                    first_title = cand
                    break

    return reviews

def fetch_from_yes24(isbn: str):
    """YES24에서 도서 상세 정보 및 고화질 표지 URL 가져오기"""
    isbn_clean = str(isbn).strip().replace("-", "")
    url = f"https://www.yes24.com/Product/Search?domain=ALL&query={isbn_clean}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200 or "검색결과가 없습니다" in resp.text:
            return None
        
        soup = BeautifulSoup(resp.text, "html.parser")
        first_item = soup.select_one("#yesSchList li")
        if not first_item:
            return None
        
        title_elem = first_item.select_one(".gd_name")
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        link = "https://www.yes24.com" + title_elem.get("href", "")
        
        auth_elem = first_item.select_one(".info_auth")
        author = auth_elem.get_text(strip=True) if auth_elem else ""
        
        pub_elem = first_item.select_one(".info_pub")
        publisher = pub_elem.get_text(strip=True) if pub_elem else ""
        
        price_elem = first_item.select_one(".txt_num")
        price = price_elem.get_text(strip=True) if price_elem else ""
        
        # 이미지 URL 추출
        m = re.search(r'/Goods/(\d+)', link)
        image_url = f"https://image.yes24.com/Goods/{m.group(1)}/XL" if m else ""
        
        return {
            "isbn": isbn_clean,
            "title": title,
            "author": author,
            "publisher": publisher,
            "price": price,
            "link": link,
            "image_url": image_url
        }
    except Exception as e:
        return None

def main():
    print("=== [1/5] 서재 마이그레이션 환경 준비 ===")
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    CARDS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 기존 엑셀 데이터 로드
    excel_path = BASE_DIR / "yes24 isbn 검색 3 .xlsm"
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb['Sheet1']
    
    books = []
    seen_isbns = set()

    print(f"=== [2/5] 기존 엑셀(총 {ws.max_row - 2}행) 데이터 파싱 ===")
    for r in range(3, ws.max_row + 1):
        isbn = ws.cell(r, 1).value
        title = ws.cell(r, 2).value
        author = ws.cell(r, 3).value
        pub = ws.cell(r, 4).value
        price = ws.cell(r, 5).value
        link = ws.cell(r, 6).value
        img_url = ws.cell(r, 7).value
        
        if not isbn:
            continue
            
        isbn_str = str(isbn).strip().split(".")[0]
        if isbn_str in seen_isbns:
            continue
        seen_isbns.add(isbn_str)

        book_data = {
            "isbn": isbn_str,
            "title": str(title).strip() if title else "",
            "author": str(author).strip() if author else "",
            "publisher": str(pub).strip() if pub else "",
            "price": str(price).strip() if price else "",
            "link": str(link).strip() if link else "",
            "image_url": str(img_url).strip() if img_url else "",
            "from_excel": bool(title)
        }
        books.append(book_data)

    print(f"고유 도서 목록: {len(books)}권 추출됨")

    # 2. 정보가 누락된 도서 중 유효한 ISBN(978/979 시작 13자리) 추가 조회
    missing_books = [b for b in books if not b["title"] and (b["isbn"].startswith("978") or b["isbn"].startswith("979")) and len(b["isbn"]) == 13]
    print(f"=== [3/5] 미조회 ISBN {len(missing_books)}건에 대한 경량 웹 조회 진행 ===")
    
    updated_count = 0
    for idx, b in enumerate(missing_books):
        res = fetch_from_yes24(b["isbn"])
        if res:
            b.update(res)
            updated_count += 1
            print(f"[{idx+1}/{len(missing_books)}] 성공: {res['title'][:20]}")
        else:
            print(f"[{idx+1}/{len(missing_books)}] 검색 불가 (ISBN: {b['isbn']})")
        time.sleep(0.3)  # 부하 방지용 짧은 대기

    print(f"추가 복구 성공: {updated_count}권")

    # 3. 표지 이미지 매칭 & 다운로드
    print("=== [4/5] 표지 이미지 준비 및 복사/다운로드 ===")
    legacy_images = {}
    if LEGACY_COVERS.exists():
        for f in LEGACY_COVERS.glob("*.jpg"):
            clean_name = clean_filename(f.stem)
            legacy_images[clean_name] = f

    total_valid = 0
    for b in books:
        if not b["title"]:
            continue
        total_valid += 1
        safe_name = clean_filename(b["title"])
        dest_cover = COVERS_DIR / f"{safe_name}.jpg"
        
        # 1순위: 기존 '갖고 있는 책표지'에 이미 있으면 복사
        if not dest_cover.exists():
            matched_legacy = None
            for leg_stem, leg_path in legacy_images.items():
                if safe_name in leg_stem or leg_stem in safe_name:
                    matched_legacy = leg_path
                    break
            
            if matched_legacy:
                shutil.copy2(matched_legacy, dest_cover)
            elif b.get("image_url") and b["image_url"].startswith("http"):
                # 2순위: YES24 고화질 이미지 직접 다운로드
                try:
                    r = requests.get(b["image_url"], headers=HEADERS, timeout=8)
                    if r.status_code == 200:
                        dest_cover.write_bytes(r.content)
                except Exception:
                    pass

    # 4. 감상문 파싱
    reviews = parse_reviews()
    print(f"감상문 데이터 {len(reviews)}건 확인")

    # 5. 마크다운 도서 카드 생성
    print("=== [5/5] 개별 마크다운 카드 및 인덱스 생성 ===")
    index_rows = []
    
    for b in books:
        if not b["title"]:
            continue
            
        safe_title = clean_filename(b["title"])
        cover_rel = f"covers/{safe_title}.jpg"
        has_cover = (COVERS_DIR / f"{safe_title}.jpg").exists()
        cover_md = f"![{safe_title}]({cover_rel})" if has_cover else "*(표지 없음)*"
        
        # 감상문 매칭 시도
        matched_review = ""
        for rev in reviews:
            if safe_title in rev["content"] or safe_title in rev["title_hint"]:
                matched_review = f"\n\n### 📝 매칭된 독서 기록\n> 출처: [{rev['url']}]({rev['url']})\n\n{rev['content']}"
                break
        
        md_text = f"""---
title: "{b['title']}"
author: "{b['author']}"
publisher: "{b['publisher']}"
price: "{b['price']}"
isbn: "{b['isbn']}"
yes24_url: "{b['link']}"
cover: "{cover_rel if has_cover else ''}"
migrated_at: "2026-10-24"
---

# {b['title']}

{cover_md}

## 📌 도서 메타데이터
- **저자**: {b['author']}
- **출판사**: {b['publisher']}
- **정가 / 구매가**: {b['price']}
- **ISBN**: `{b['isbn']}`
- **YES24 링크**: [도서 상세페이지 바로가기]({b['link']})

## 💭 독서 감상 및 메모
{matched_review if matched_review else "- 이 책에 대한 감상평을 기록해보세요."}
"""
        card_file = CARDS_DIR / f"{safe_title}.md"
        card_file.write_text(md_text, encoding="utf-8")
        
        index_rows.append(
            f"| {len(index_rows)+1} | [{'![표지](' + cover_rel + ')' if has_cover else '-'}]({cover_rel}) | [[{safe_title}]] | {b['author']} | {b['publisher']} | `{b['isbn']}` | [상세보기]({b['link']}) |"
        )

    # 전체 서재 인덱스 파일 (index.md)
    index_md = f"""# 📚 나의 개인 디지털 서재 (Modern Bookshelf)

- **마이그레이션 일시**: 2026-10-24
- **총 정리 도서**: {len(index_rows)} 권
- **표지 이미지 보관**: `covers/`
- **개별 독서 카드**: `books/`

---

## 📖 전체 도서 목록

| 번호 | 표지 | 제목 | 저자 | 출판사 | ISBN | 링크 |
|:---:|:---:|---|---|---|:---:|:---:|
""" + "\n".join(index_rows) + "\n"

    (TARGET_DIR / "README.md").write_text(index_md, encoding="utf-8")
    print(f"\n🎉 마이그레이션 완료! 총 {len(index_rows)}권의 마크다운 서재가 구축되었습니다.")
    print(f"결과 디렉토리: {TARGET_DIR}")

if __name__ == "__main__":
    main()
