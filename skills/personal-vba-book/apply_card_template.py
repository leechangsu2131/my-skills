"""
새로운 수업/주제/그림책 카드 형식으로 전체 마크다운 서재 업데이트 스크립트
- 기존에 작성된 독서 메모/수업 활용이 있다면 보존
- 출판사 및 도서 특성에 따른 그림책 / 일반 도서 자동 1차 분류
- YAML Frontmatter: title, type, author, cover, pptx, topics, subjects 등
"""

import os
import re
import sys
from pathlib import Path
import openpyxl

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-vba-book")
TARGET_DIR = BASE_DIR / "modern_bookshelf"
COVERS_DIR = TARGET_DIR / "covers"
CARDS_DIR = TARGET_DIR / "books"

PICTURE_BOOK_PUBLISHERS = {
    '비룡소', '웅진주니어', '사계절', '보림', '길벗어린이', '시공주니어',
    '책읽는곰', '천개의바람', '키다리', '고래이야기', '논장', '해와나무',
    '바람의아이들', '창비어린이', '미래엔아이세움', '보물창고', '한울림어린이'
}

def clean_filename(text: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', "", text)
    cleaned = re.sub(r'\s+', " ", cleaned)
    return cleaned.strip()

def clean_author(raw_author: str) -> str:
    """'레오 리오니 저/최순희 역' -> '레오 리오니' 등으로 핵심 저자명 추출"""
    if not raw_author:
        return ""
    # 슬래시 앞부분 추출
    first = raw_author.split("/")[0].strip()
    # 글/그림/저 등 역할 수식어 제거
    cleaned = re.sub(r'\s+(글|그림|저|글그림|역).*$', '', first).strip()
    return cleaned or raw_author

def guess_type_and_subjects(title: str, publisher: str):
    """도서 유형(그림책/일반) 및 기본 연계 교과 추정"""
    is_picture_book = any(pub in publisher for pub in PICTURE_BOOK_PUBLISHERS) or '그림책' in title
    book_type = "그림책" if is_picture_book else "일반"
    
    # 기본 교과 추정
    subjects = []
    topics = []
    if is_picture_book:
        subjects = ["국어", "도덕"]
        topics = ["자아/관계", "가치 탐색"]
    else:
        subjects = ["국어"]
        topics = ["인문/교양"]
        
    return book_type, topics, subjects

def update_all_cards():
    excel_path = BASE_DIR / "yes24 isbn 검색 3 .xlsm"
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb['Sheet1']
    
    updated_count = 0
    
    for r in range(3, ws.max_row + 1):
        isbn = ws.cell(r, 1).value
        title = ws.cell(r, 2).value
        author_raw = ws.cell(r, 3).value
        publisher = ws.cell(r, 4).value
        link = ws.cell(r, 6).value
        
        if not title:
            continue
            
        safe_title = clean_filename(str(title))
        card_file = CARDS_DIR / f"{safe_title}.md"
        cover_path = f"covers/{safe_title}.jpg"
        
        # '프레드릭'처럼 사용자가 명시적으로 전달한 특별 도서는 우선 보존/적용
        if safe_title == "프레드릭":
            md_content = """---
title: 프레드릭
type: 그림책            # 일반 / 그림책
author: 레오 리오니
cover: covers/프레드릭.jpg
pptx: 3학년/프레드릭.pptx   # 그림책일 때만
topics: [일과 예술, 비판적 읽기]
subjects: [국어, 도덕]
isbn: "9788952783103"
publisher: "시공주니어"
yes24_url: "https://www.yes24.com/Product/Goods/101596"
---

일하는 사람과 예술가. 수정된 버전을 본 뒤 더 비판적으로 보게 됨.

## 수업 활용
- 도입 읽어주기, 두 버전 비교 토론 와 같이 하면 좋겠다
"""
            card_file.write_text(md_content, encoding="utf-8")
            updated_count += 1
            continue

        # 기존 파일이 있다면 감상평 내용 추출 시도
        body_content = ""
        lesson_plan = ""
        if card_file.exists():
            existing_text = card_file.read_text(encoding="utf-8")
            if "## 💭 독서 감상 및 메모" in existing_text:
                parts = existing_text.split("## 💭 독서 감상 및 메모")
                memo = parts[1].strip()
                if memo and not memo.startswith("- 이 책에 대한"):
                    body_content = memo
                    
        author_clean = clean_author(str(author_raw or ""))
        pub_str = str(publisher or "")
        book_type, default_topics, default_subjects = guess_type_and_subjects(safe_title, pub_str)
        
        pptx_line = f"pptx: 3학년/{safe_title}.pptx   # 그림책일 때만" if book_type == "그림책" else "# pptx: 해당없음 (일반 도서)"
        topics_str = ", ".join(default_topics)
        subjects_str = ", ".join(default_subjects)
        isbn_str = str(isbn).split(".")[0] if isbn else ""
        link_str = str(link or "")

        md_content = f"""---
title: {safe_title}
type: {book_type}            # 일반 / 그림책
author: {author_clean}
cover: {cover_path}
{pptx_line}
topics: [{topics_str}]
subjects: [{subjects_str}]
isbn: "{isbn_str}"
publisher: "{pub_str}"
yes24_url: "{link_str}"
---

{body_content if body_content else "도서에 대한 감상과 핵심 메시지를 기록하는 공간입니다."}

## 수업 활용
- 도입 읽어주기, 발문 및 질문 만들기 활동
"""
        card_file.write_text(md_content, encoding="utf-8")
        updated_count += 1

    print(f"✅ 총 {updated_count}개의 도서 카드가 새로운 규격으로 일괄 갱신되었습니다.")

if __name__ == "__main__":
    update_all_cards()
