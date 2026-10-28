"""
search_app.py - 개인용 로컬 검색 웹앱
사용법: python search_app.py
       → http://localhost:5000 접속
"""

import os
import json
import sqlite3
from flask import Flask, request, render_template_string, jsonify
from whoosh.index import open_dir, exists_in
from whoosh.qparser import MultifieldParser, FuzzyTermPlugin
from whoosh import scoring

app = Flask(__name__)
INDEX_DIR = "index_dir"
CONFIG_FILE = "config.json"

def get_db_stats():
    # 현재 파일(search_app.py)이 있는 폴더 기준
    base_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
    config_path = os.path.join(base_dir, CONFIG_FILE)
    
    db_path = "data.db"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            db_path = cfg.get("db_path", "data.db")
            
    db_full_path = os.path.join(base_dir, db_path)

    if not os.path.exists(db_full_path):
        return {"total": 0, "sites": []}
        
    conn = sqlite3.connect(db_full_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM pages")
    total = c.fetchone()[0]
    c.execute("SELECT site, COUNT(*) FROM pages GROUP BY site ORDER BY COUNT(*) DESC")
    sites = [{"name": r[0], "count": r[1]} for r in c.fetchall()]
    conn.close()
    return {"total": total, "sites": sites}

# ──────────────────────────────────────────
# HTML 템플릿 (단일 파일 내 인라인)
# ──────────────────────────────────────────
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🔍 내 자료 검색</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --surface2: #21262d;
    --border: #30363d;
    --accent: #58a6ff;
    --accent2: #3fb950;
    --text: #e6edf3;
    --text2: #8b949e;
    --red: #f85149;
    --yellow: #d29922;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Noto Sans KR', sans-serif;
    min-height: 100vh;
    padding: 0 20px 60px;
  }

  /* 헤더 */
  header {
    max-width: 860px;
    margin: 0 auto;
    padding: 48px 0 32px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: flex-end;
    gap: 16px;
  }
  header h1 {
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: var(--text);
  }
  header h1 span { color: var(--accent); }
  .badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text2);
    padding: 2px 8px;
    border-radius: 20px;
    margin-bottom: 4px;
  }

  /* 메인 */
  main { max-width: 860px; margin: 0 auto; }

  /* 검색창 */
  .search-box {
    display: flex;
    gap: 10px;
    margin: 32px 0 20px;
    position: relative;
  }
  .search-box input[type=text] {
    flex: 1;
    padding: 14px 20px;
    font-size: 1rem;
    font-family: 'Noto Sans KR', sans-serif;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    outline: none;
    transition: border-color 0.2s;
  }
  .search-box input:focus { border-color: var(--accent); }
  .search-box button {
    padding: 14px 24px;
    font-size: 0.9rem;
    font-family: 'Noto Sans KR', sans-serif;
    font-weight: 500;
    background: var(--accent);
    color: #0d1117;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  .search-box button:hover { opacity: 0.85; }

  /* 필터 */
  .filters {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 24px;
  }
  .filter-btn {
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 0.78rem;
    padding: 4px 12px;
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text2);
    border-radius: 20px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .filter-btn:hover, .filter-btn.active {
    border-color: var(--accent);
    color: var(--accent);
  }

  /* 통계 바 */
  .stats-bar {
    font-size: 0.78rem;
    color: var(--text2);
    margin-bottom: 20px;
    font-family: 'JetBrains Mono', monospace;
  }
  .stats-bar strong { color: var(--accent2); }

  /* 결과 카드 */
  .result-item {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 12px;
    transition: border-color 0.2s, transform 0.15s;
    position: relative;
  }
  .result-item:hover {
    border-color: var(--accent);
    transform: translateX(2px);
  }
  .result-rank {
    position: absolute;
    top: 16px; right: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--text2);
  }
  .result-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--accent);
    text-decoration: none;
    display: block;
    margin-bottom: 6px;
    line-height: 1.4;
  }
  .result-title:hover { text-decoration: underline; }
  .result-url {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: var(--accent2);
    margin-bottom: 10px;
    word-break: break-all;
  }
  .result-meta {
    font-size: 0.75rem;
    color: var(--text2);
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
  .kw-tag {
    background: var(--surface2);
    border: 1px solid var(--border);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    color: var(--yellow);
  }

  /* 빈 상태 */
  .empty-state {
    text-align: center;
    padding: 60px 20px;
    color: var(--text2);
  }
  .empty-state .icon { font-size: 3rem; margin-bottom: 16px; }
  .empty-state p { line-height: 1.8; font-size: 0.9rem; }
  .empty-state code {
    font-family: 'JetBrains Mono', monospace;
    background: var(--surface2);
    padding: 2px 8px;
    border-radius: 4px;
    color: var(--accent);
    font-size: 0.85rem;
  }

  /* 에러 */
  .error-box {
    background: #2d1f1f;
    border: 1px solid var(--red);
    border-radius: 8px;
    padding: 16px 20px;
    color: var(--red);
    font-size: 0.88rem;
    margin: 20px 0;
  }

  /* 사이트 현황 */
  .site-stats {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 8px;
  }
  .site-chip {
    font-size: 0.72rem;
    font-family: 'JetBrains Mono', monospace;
    background: var(--surface2);
    border: 1px solid var(--border);
    padding: 3px 10px;
    border-radius: 4px;
    color: var(--text2);
  }
  .site-chip span { color: var(--accent2); }
</style>
</head>
<body>

<header>
  <div>
    <h1>🔍 내 자료 <span>검색기</span></h1>
  </div>
  <div class="badge">PERSONAL USE ONLY</div>
</header>

<main>

  <!-- 검색창 -->
  <form method="POST" action="/">
    <div class="search-box">
      <input type="text" name="query" placeholder="검색어 입력... (예: 수업 자료, 프로젝트, 평가)" 
             value="{{ query or '' }}" autofocus autocomplete="off">
      <button type="submit">검색</button>
    </div>
  </form>

  <!-- DB 현황 -->
  {% if stats.total == 0 %}
  <div class="empty-state">
    <div class="icon">📂</div>
    <p>수집된 자료가 없습니다.<br>
    <code>python scraper.py --url https://example.com</code> 로 자료를 수집한 후<br>
    <code>python indexer.py</code> 로 인덱스를 만들어 주세요.</p>
  </div>
  {% else %}
  <div class="stats-bar">
    총 <strong>{{ stats.total }}개</strong> 문서 수집됨 ·
    <div class="site-stats" style="display:inline-flex;">
      {% for s in stats.sites %}
      <span class="site-chip">{{ s.name }} <span>{{ s.count }}</span></span>
      {% endfor %}
    </div>
  </div>

  <!-- 검색 결과 -->
  {% if error %}
  <div class="error-box">⚠️ {{ error }}</div>
  {% elif results is defined %}
    {% if results %}
    <div class="stats-bar" style="margin-bottom:16px;">
      "<strong style="color:var(--text)">{{ query }}</strong>" 검색 결과: <strong>{{ results|length }}</strong>개
    </div>
    {% for r in results %}
    <div class="result-item">
      <span class="result-rank">#{{ loop.index }}</span>
      <a class="result-title" href="{{ r.url }}" target="_blank" rel="noopener">
        {{ r.title or '제목 없음' }}
      </a>
      <div class="result-url">🔗 {{ r.url }}</div>
      <div class="result-meta">
        <span>📁 {{ r.site }}</span>
        <span>🕐 {{ r.scraped_at }}</span>
        {% if r.keywords %}
        <span>
          {% for kw in r.keywords.split(',')[:5] %}
          <span class="kw-tag">{{ kw.strip() }}</span>
          {% endfor %}
        </span>
        {% endif %}
      </div>
    </div>
    {% endfor %}
    {% else %}
    <div class="empty-state">
      <div class="icon">🔎</div>
      <p>"<strong style="color:var(--text)">{{ query }}</strong>"에 대한 결과가 없습니다.<br>
      다른 키워드로 시도해 보세요.<br>
      새 자료를 수집했다면 <code>python indexer.py</code>를 다시 실행하세요.</p>
    </div>
    {% endif %}
  {% endif %}
  {% endif %}

</main>
</body>
</html>'''


# ──────────────────────────────────────────
# 라우트
# ──────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    stats = get_db_stats()
    context = {"stats": stats, "query": None, "results": None, "error": None}

    if request.method == "POST":
        query_str = request.form.get("query", "").strip()
        context["query"] = query_str

        if not query_str:
            return render_template_string(HTML_TEMPLATE, **context)

        # index_dir 경로 절대화
        base_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
        full_index_dir = os.path.join(base_dir, INDEX_DIR)

        if not exists_in(full_index_dir):
            context["error"] = "인덱스가 없습니다. python indexer.py를 먼저 실행하세요."
            return render_template_string(HTML_TEMPLATE, **context)

        try:
            ix = open_dir(full_index_dir)
            with ix.searcher(weighting=scoring.BM25F()) as searcher:
                parser = MultifieldParser(["title", "keywords", "content"], ix.schema)
                parser.add_plugin(FuzzyTermPlugin())

                # 한국어 부분어 검색: 각 단어 뒤에 * 자동 추가
                # "감각" → "감각*" 으로 처리하여 "감각적", "감각표현" 등 매칭
                # (이미 * 또는 "가 들어있으면 그대로 사용)
                if "*" not in query_str and '"' not in query_str:
                    expanded = " ".join(
                        term + "*" if not term.upper() in ("AND", "OR", "NOT") else term
                        for term in query_str.split()
                    )
                else:
                    expanded = query_str

                query = parser.parse(expanded)
                hits = searcher.search(query, limit=30)


                results = []
                for hit in hits:
                    results.append({
                        "title": hit.get("title", ""),
                        "url": hit.get("url", "#"),
                        "keywords": hit.get("keywords", ""),
                        "site": hit.get("site", ""),
                        "scraped_at": hit.get("scraped_at", ""),
                    })

            context["results"] = results

        except Exception as e:
            context["error"] = f"검색 오류: {e}"

    return render_template_string(HTML_TEMPLATE, **context)


@app.route("/api/stats")
def api_stats():
    return jsonify(get_db_stats())


# ──────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  🔍 개인용 검색앱 시작")
    print("  → http://localhost:5000 에서 접속")
    print("=" * 50)
    app.run(debug=False, port=5000)
