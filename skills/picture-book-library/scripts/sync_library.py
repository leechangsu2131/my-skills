"""
그림책과 서재 자동 동기화 스크립트 (sync_library.py)
--------------------------------------------------
`서재/books/*.md` 카드와 `그림책/` 폴더 내 수업 자료들을 스캔하여
- 그림책_목록.html
- 그림책_목록.csv
- 그림책_색인.md
를 자동으로 최신 상태로 동기화합니다.
"""

import os
import sys
import re
import json
import csv
import urllib.parse
from datetime import datetime

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = r"C:\Users\lee21\OneDrive - gyo6.net\8. 그림책과 서재"
BOOKS_DIR = os.path.join(ROOT_DIR, "서재", "books")
PICTURE_BOOKS_DIR = os.path.join(ROOT_DIR, "그림책")
HTML_PATH = os.path.join(ROOT_DIR, "그림책_목록.html")
CSV_PATH = os.path.join(ROOT_DIR, "그림책_목록.csv")
INDEX_PATH = os.path.join(ROOT_DIR, "그림책_색인.md")


def parse_frontmatter(content):
    """마크다운 파일에서 YAML Frontmatter 추출"""
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}, content
    
    meta = {}
    body = content[m.end():].strip()
    lines = m.group(1).splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            # 배열 파싱 [a, b, c]
            if val.startswith("[") and val.endswith("]"):
                items = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
                meta[key] = items
            elif val.startswith('"') and val.endswith('"'):
                meta[key] = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                meta[key] = val[1:-1]
            else:
                meta[key] = val
    return meta, body


def extract_note_from_body(body):
    """본문에서 첫 문단 또는 감상 추출"""
    lines = body.splitlines()
    text_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith("#"):
            if text_lines:
                break
            continue
        if line and not line.startswith("- 지은이") and not line.startswith("- 출판사"):
            text_lines.append(line)
            if len(text_lines) >= 2:
                break
    return " ".join(text_lines)[:120]


def collect_library_data():
    items = []
    
    # 1. 서재 books/*.md 스캔
    if os.path.exists(BOOKS_DIR):
        for fname in os.listdir(BOOKS_DIR):
            if not fname.endswith(".md") or fname.startswith("."):
                continue
            fpath = os.path.join(BOOKS_DIR, fname)
            try:
                with open(fpath, encoding="utf-8-sig") as f:
                    content = f.read()
            except Exception:
                with open(fpath, encoding="cp949", errors="ignore") as f:
                    content = f.read()
            
            meta, body = parse_frontmatter(content)
            title = meta.get("title") or os.path.splitext(fname)[0]
            if not title or "{{" in str(title):
                continue
            
            kind = meta.get("type", "그림책" if "그림책" in str(meta.get("type", "")) else "보유도서")
            topics = meta.get("topics", [])
            subjects = meta.get("subjects", [])
            author = meta.get("author", "")
            publisher = meta.get("publisher", "")
            by_str = f"{author} · \"{publisher}\"" if author and publisher else (author or publisher)
            note = extract_note_from_body(body)
            cover = meta.get("cover") or ""
            
            rel_path = f"서재/books/{fname}"
            href = urllib.parse.quote(rel_path)
            
            item = {
                "title": title,
                "folder": "서재/books",
                "slides": None,
                "mb": None,
                "date": "",
                "thumb": cover if cover else "",
                "first": "",
                "cloud": False,
                "kind": kind,
                "ext": "",
                "href": href,
                "path": rel_path,
                "topics": topics,
                "subjects": subjects,
                "note": note,
                "by": by_str,
                "owned": True if (meta.get("isbn") or cover or author) else False,
                "cover": cover,
                "card": href
            }
            items.append(item)
            
    return items


def sync():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 서재 동기화 시작...")
    
    # 기존 HTML 데이터 불러오기
    if not os.path.exists(HTML_PATH):
        print(f"오류: {HTML_PATH} 파일을 찾을 수 없습니다.")
        return
        
    with open(HTML_PATH, encoding="utf-8-sig") as f:
        html = f.read()
        
    m = re.search(r"const DATA = (\[.*?\]);", html, re.DOTALL)
    if not m:
        print("오류: HTML 내 DATA 배열을 찾을 수 없습니다.")
        return
        
    old_data = json.loads(m.group(1))
    
    # 도서 카드 데이터 수집
    card_items = collect_library_data()
    card_dict = {item["title"]: item for item in card_items}
    
    # 기존 데이터 중 그림책/수업자료는 유지하고, 서재 카드 항목은 갱신
    merged = []
    seen_titles = set()
    
    # 1. 기존 항목 중 유효한 것 유지/갱신
    for d in old_data:
        title = d.get("title", "")
        # 버그 헤더 제외
        if "그림책 목록" in title or "일반 도서 목록" in title:
            continue
            
        if title in card_dict:
            # 카드 정보로 최신화 (자료 속성 유지)
            updated = dict(card_dict[title])
            if d.get("slides") is not None:
                updated["slides"] = d["slides"]
            if d.get("mb") is not None:
                updated["mb"] = d["mb"]
            if d.get("ext"):
                updated["ext"] = d["ext"]
            merged.append(updated)
            seen_titles.add(title)
        else:
            merged.append(d)
            seen_titles.add(title)
            
    # 2. 새로 추가된 카드 추가
    for title, card in card_dict.items():
        if title not in seen_titles:
            merged.append(card)
            seen_titles.add(title)
            print(f"  + 새 도서 반영: {title}")
            
    print(f"  총 데이터 건수: {len(merged)}건")
    
    # HTML 저장
    new_json_str = json.dumps(merged, ensure_ascii=False)
    new_html = html[:m.start()] + f"const DATA = {new_json_str};" + html[m.end():]
    with open(HTML_PATH, "w", encoding="utf-8-sig") as f:
        f.write(new_html)
    print("  ✅ 그림책_목록.html 갱신 완료")
    
    # CSV 저장
    if merged:
        # 모든 항목에서 고유 키 집합 수집
        all_keys = []
        for d in merged:
            for k in d.keys():
                if k not in all_keys:
                    all_keys.append(k)
        keys = all_keys
        with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in merged:
                # 리스트는 쉼표 문자열로 변환
                r = dict(row)
                if isinstance(r.get("topics"), list):
                    r["topics"] = ", ".join(r["topics"])
                if isinstance(r.get("subjects"), list):
                    r["subjects"] = ", ".join(r["subjects"])
                writer.writerow(r)
        print("  ✅ 그림책_목록.csv 갱신 완료")
        
    print("모든 동기화가 성공적으로 완료되었습니다!")

if __name__ == "__main__":
    sync()
