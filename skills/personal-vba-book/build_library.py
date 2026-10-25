"""
서재 빌더 스크립트:
1. 서재/books/*.md 카드를 순회하며 메타데이터 파싱
2. 서재/README.md 갤러리 인덱스 생성
3. 서재/목록.html 인터랙티브 검색/필터 웹 화면 생성
   - 제목, 저자, 출판사, 키워드 검색
   - 유형(그림책/일반), 교과목(국어/도덕 등), 주제 태그 실시간 필터링
   - 카드형 갤러리 뷰 + 테이블 뷰 전환
"""

import os
import re
import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

LIBRARY_DIR = Path(r"C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-vba-book\서재")
BOOKS_DIR = LIBRARY_DIR / "books"
COVERS_DIR = LIBRARY_DIR / "covers"

def parse_yaml_frontmatter(md_text: str):
    """간단하고 견고한 YAML Frontmatter 파서"""
    if not md_text.startswith("---"):
        return {}, md_text
    
    parts = md_text.split("---", 2)
    if len(parts) < 3:
        return {}, md_text
        
    yaml_part = parts[1]
    body = parts[2].strip()
    
    meta = {}
    for line in yaml_part.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 주석 제거 (단, url 안의 # 제외)
        if "   #" in line:
            line = line.split("   #")[0].strip()
            
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            # 배열 파싱 [a, b]
            if val.startswith("[") and val.endswith("]"):
                items = [item.strip().strip("'\"") for item in val[1:-1].split(",") if item.strip()]
                meta[key] = items
            else:
                meta[key] = val.strip("'\"")
                
    return meta, body

def build_library():
    print("=== [서재 빌더] 도서 카드 분석 시작 ===")
    book_cards = list(BOOKS_DIR.glob("*.md"))
    books_data = []

    for card in book_cards:
        if card.name.startswith("_"):
            continue
        text = card.read_text(encoding="utf-8")
        meta, body = parse_yaml_frontmatter(text)
        
        title = meta.get("title", card.stem)
        book_type = meta.get("type", "일반").split("#")[0].strip()
        author = meta.get("author", "")
        cover = meta.get("cover", f"covers/{card.stem}.jpg")
        pptx = meta.get("pptx", "")
        topics = meta.get("topics", [])
        subjects = meta.get("subjects", [])
        isbn = meta.get("isbn", "")
        publisher = meta.get("publisher", "")
        yes24_url = meta.get("yes24_url", "")
        
        # 표지 파일 실존 여부
        has_cover = (LIBRARY_DIR / cover).exists()
        
        # 수업 활용 섹션 파싱
        lesson_plan = ""
        if "## 수업 활용" in body:
            lesson_plan = body.split("## 수업 활용")[1].strip()

        # 도서 리뷰/감상 파싱
        memo = body.split("## 수업 활용")[0].strip() if "## 수업 활용" in body else body
        if memo.startswith("#"):
            memo_lines = [l for l in memo.splitlines() if not l.startswith("#") and not l.startswith("![")]
            memo = "\n".join(memo_lines).strip()

        books_data.append({
            "title": title,
            "type": book_type,
            "author": author,
            "cover": cover if has_cover else "",
            "pptx": pptx,
            "topics": topics if isinstance(topics, list) else [topics],
            "subjects": subjects if isinstance(subjects, list) else [subjects],
            "isbn": isbn,
            "publisher": publisher,
            "yes24_url": yes24_url,
            "memo": memo,
            "lesson_plan": lesson_plan,
            "card_file": f"books/{card.name}"
        })

    # 가나다순 정렬
    books_data.sort(key=lambda x: x["title"])
    print(f"총 {len(books_data)}권 도서 파싱 완료")

    # 1. README.md (갤러리 테이블 생성)
    pic_books = [b for b in books_data if b["type"] == "그림책"]
    gen_books = [b for b in books_data if b["type"] != "그림책"]

    def make_table(book_list):
        rows = []
        for idx, b in enumerate(book_list, 1):
            cover_md = f"[![표지]({b['cover']})]({b['cover']})" if b['cover'] else "*(표지 없음)*"
            title_md = f"[{b['title']}]({b['card_file']})"
            subjects_str = ", ".join(b['subjects']) if b['subjects'] else "-"
            topics_str = ", ".join(b['topics']) if b['topics'] else "-"
            pptx_str = f"`{b['pptx']}`" if b['pptx'] else "-"
            rows.append(f"| {idx} | {cover_md} | **{title_md}**<br><sub>{b['author']} · {b['publisher']}</sub> | {subjects_str} | {topics_str} | {pptx_str} |")
        return "\n".join(rows)

    readme_content = f"""# 📚 우리 서재 & 수업 도서 갤러리

> **구조**: `books/` (도서 카드) · `covers/` (표지 이미지) · `Inbox.md` (빠른 감상 메모) · `목록.html` (검색·필터 화면)  
> **총 보유 도서**: {len(books_data)}권 (🎨 그림책: {len(pic_books)}권 / 📖 일반 도서: {len(gen_books)}권)

👉 **[🔍 대화형 검색 및 필터 웹 화면 열기 (목록.html)](목록.html)**

---

## 🎨 그림책 목록 ({len(pic_books)}권)
| 번호 | 표지 | 서명 / 정보 | 연계 교과 | 주요 주제 | 수업 PPTX |
|:---:|:---:|---|:---:|---|:---:|
{make_table(pic_books)}

---

## 📖 일반 도서 목록 ({len(gen_books)}권)
| 번호 | 표지 | 서명 / 정보 | 연계 교과 | 주요 주제 | 비고 |
|:---:|:---:|---|:---:|---|:---:|
{make_table(gen_books)}
"""
    (LIBRARY_DIR / "README.md").write_text(readme_content, encoding="utf-8")
    print("✅ 서재/README.md 갤러리 생성 완료")

    # 2. 목록.html (대화형 검색/필터 뷰)
    books_json = json.dumps(books_data, ensure_ascii=False)

    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📚 나의 서재 — 도서 검색 및 수업 큐레이션</title>
<style>
  :root {{
    --primary: #2563eb;
    --primary-light: #eff6ff;
    --bg: #f8fafc;
    --card-bg: #ffffff;
    --text: #1e293b;
    --text-muted: #64748b;
    --border: #e2e8f0;
    --tag-bg: #f1f5f9;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Pretendard", sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 24px;
    line-height: 1.5;
  }}
  header {{
    max-width: 1300px;
    margin: 0 auto 24px auto;
  }}
  h1 {{ font-size: 26px; font-weight: 700; color: #0f172a; margin-bottom: 8px; }}
  .desc {{ color: var(--text-muted); font-size: 14px; margin-bottom: 20px; }}
  
  .controls {{
    background: var(--card-bg);
    padding: 20px;
    border-radius: 12px;
    border: 1px solid var(--border);
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    align-items: center;
    margin-bottom: 24px;
  }}
  .search-box {{
    flex: 1 1 300px;
    position: relative;
  }}
  .search-box input {{
    width: 100%;
    padding: 10px 14px;
    border-radius: 8px;
    border: 1px solid var(--border);
    font-size: 15px;
    outline: none;
    transition: border 0.2s;
  }}
  .search-box input:focus {{ border-color: var(--primary); }}
  
  .filter-group {{
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }}
  .filter-btn {{
    padding: 8px 14px;
    border-radius: 20px;
    border: 1px solid var(--border);
    background: var(--card-bg);
    font-size: 13px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.2s;
  }}
  .filter-btn:hover {{ background: var(--tag-bg); }}
  .filter-btn.active {{
    background: var(--primary);
    color: #fff;
    border-color: var(--primary);
  }}
  
  .stats-bar {{
    max-width: 1300px;
    margin: 0 auto 16px auto;
    font-size: 14px;
    color: var(--text-muted);
    display: flex;
    justify-content: space-between;
  }}

  /* 카드 그리드 */
  .grid {{
    max-width: 1300px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 20px;
  }}
  .book-card {{
    background: var(--card-bg);
    border-radius: 12px;
    border: 1px solid var(--border);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: transform 0.2s, box-shadow 0.2s;
  }}
  .book-card:hover {{
    transform: translateY(-4px);
    box-shadow: 0 10px 15px -3px rgba(0,0,0,0.08);
  }}
  .cover-wrap {{
    width: 100%;
    height: 280px;
    background: #f1f5f9;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    position: relative;
  }}
  .cover-wrap img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
  }}
  .badge-type {{
    position: absolute;
    top: 10px;
    left: 10px;
    background: rgba(15, 23, 42, 0.75);
    color: #fff;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 6px;
    backdrop-filter: blur(4px);
  }}
  .badge-type.pic {{ background: rgba(37, 99, 235, 0.85); }}
  
  .card-body {{
    padding: 16px;
    flex: 1;
    display: flex;
    flex-direction: column;
  }}
  .book-title {{
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 4px;
    color: #0f172a;
    line-height: 1.3;
  }}
  .book-author {{
    font-size: 13px;
    color: var(--text-muted);
    margin-bottom: 8px;
  }}
  .tag-list {{
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 12px;
  }}
  .tag {{
    background: var(--tag-bg);
    color: #475569;
    font-size: 11px;
    padding: 2px 7px;
    border-radius: 4px;
  }}
  .tag.subject {{
    background: #e0e7ff;
    color: #3730a3;
  }}
  .memo-box {{
    background: #fafafa;
    border-left: 3px solid var(--primary);
    padding: 8px 10px;
    font-size: 12px;
    color: #334155;
    margin-top: auto;
    border-radius: 0 4px 4px 0;
  }}
  .actions {{
    display: flex;
    gap: 8px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #f1f5f9;
  }}
  .action-link {{
    font-size: 12px;
    color: var(--primary);
    text-decoration: none;
    font-weight: 600;
  }}
  .action-link:hover {{ text-decoration: underline; }}
</style>
</head>
<body>

<header>
  <h1>📚 우리 서재 & 수업 도서 큐레이션</h1>
  <p class="desc">보유 도서 및 그림책을 검색하고, 연계 교과와 수업 활용 아이디어를 손쉽게 필터링하세요.</p>
  
  <div class="controls">
    <div class="search-box">
      <input type="text" id="searchInput" placeholder="도서명, 저자, 출판사, 키워드 검색...">
    </div>
    
    <div class="filter-group" id="typeFilters">
      <span style="font-size: 13px; font-weight:600; color:var(--text-muted)">유형:</span>
      <button class="filter-btn active" data-type="all">전체</button>
      <button class="filter-btn" data-type="그림책">🎨 그림책</button>
      <button class="filter-btn" data-type="일반">📖 일반 도서</button>
    </div>

    <div class="filter-group" id="subjectFilters">
      <span style="font-size: 13px; font-weight:600; color:var(--text-muted)">교과:</span>
      <button class="filter-btn active" data-subject="all">전체</button>
      <button class="filter-btn" data-subject="국어">국어</button>
      <button class="filter-btn" data-subject="도덕">도덕</button>
    </div>
  </div>
</header>

<div class="stats-bar">
  <span>검색 결과: <strong id="resultCount">0</strong>권</span>
  <span>📂 서재 폴더: <code>서재/books/</code></span>
</div>

<div class="grid" id="bookGrid"></div>

<script>
const books = {books_json};

let currentType = "all";
let currentSubject = "all";
let searchKeyword = "";

function renderBooks() {{
  const grid = document.getElementById("bookGrid");
  grid.innerHTML = "";
  
  const filtered = books.filter(b => {{
    // 1. 유형 필터
    if (currentType !== "all" && b.type !== currentType) return false;
    
    // 2. 교과 필터
    if (currentSubject !== "all") {{
      if (!b.subjects || !b.subjects.includes(currentSubject)) return false;
    }}
    
    // 3. 키워드 검색
    if (searchKeyword) {{
      const q = searchKeyword.toLowerCase();
      const matchTitle = b.title.toLowerCase().includes(q);
      const matchAuthor = b.author.toLowerCase().includes(q);
      const matchPub = b.publisher.toLowerCase().includes(q);
      const matchTopic = (b.topics || []).some(t => t.toLowerCase().includes(q));
      const matchMemo = (b.memo || "").toLowerCase().includes(q);
      if (!matchTitle && !matchAuthor && !matchPub && !matchTopic && !matchMemo) return false;
    }}
    return true;
  }});

  document.getElementById("resultCount").innerText = filtered.length;

  filtered.forEach(b => {{
    const card = document.createElement("div");
    card.className = "book-card";
    
    const isPic = b.type === "그림책";
    const typeBadge = `<span class="badge-type ${{isPic ? 'pic' : ''}}">${{b.type}}</span>`;
    
    const coverHtml = b.cover 
      ? `<img src="${{b.cover}}" alt="${{b.title}}" loading="lazy">` 
      : `<span style="color:#94a3b8; font-size:13px;">표지 없음</span>`;
      
    const subjectTags = (b.subjects || []).map(s => `<span class="tag subject">${{s}}</span>`).join("");
    const topicTags = (b.topics || []).map(t => `<span class="tag">${{t}}</span>`).join("");
    
    const memoHtml = b.memo ? `<div class="memo-box">💭 ${{b.memo.substring(0, 70)}}${{b.memo.length > 70 ? '...' : ''}}</div>` : '';
    
    card.innerHTML = `
      <div class="cover-wrap">
        ${{typeBadge}}
        ${{coverHtml}}
      </div>
      <div class="card-body">
        <div class="book-title">${{b.title}}</div>
        <div class="book-author">${{b.author || '-'}} · ${{b.publisher || '-'}}</div>
        <div class="tag-list">
          ${{subjectTags}}
          ${{topicTags}}
        </div>
        ${{memoHtml}}
        <div class="actions">
          <a class="action-link" href="${{b.card_file}}" target="_blank">📄 카드 열기</a>
          ${{b.yes24_url ? `<a class="action-link" href="${{b.yes24_url}}" target="_blank">🛒 YES24</a>` : ''}}
        </div>
      </div>
    `;
    grid.appendChild(card);
  }});
}}

// 이벤트 리스너
document.getElementById("searchInput").addEventListener("input", (e) => {{
  searchKeyword = e.target.value.trim();
  renderBooks();
}});

document.querySelectorAll("#typeFilters .filter-btn").forEach(btn => {{
  btn.addEventListener("click", () => {{
    document.querySelectorAll("#typeFilters .filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentType = btn.dataset.type;
    renderBooks();
  }});
}});

document.querySelectorAll("#subjectFilters .filter-btn").forEach(btn => {{
  btn.addEventListener("click", () => {{
    document.querySelectorAll("#subjectFilters .filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentSubject = btn.dataset.subject;
    renderBooks();
  }});
}});

renderBooks();
</script>
</body>
</html>
"""
    (LIBRARY_DIR / "목록.html").write_text(html_template, encoding="utf-8")
    print("✅ 서재/목록.html 검색/필터 웹 화면 생성 완료")

if __name__ == "__main__":
    build_library()
