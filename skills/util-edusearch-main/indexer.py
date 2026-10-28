"""
indexer.py - SQLite DB → Whoosh 검색 인덱스 생성
사용법: python indexer.py
"""

import sqlite3
import os
import shutil
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID, STORED, DATETIME
from whoosh.analysis import StandardAnalyzer
import json

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"db_path": "data.db"}


def build_index(db_path="data.db", index_dir="index_dir"):
    # 인덱스 디렉토리 재생성 (항상 최신 상태 유지)
    if os.path.exists(index_dir):
        shutil.rmtree(index_dir)
    os.makedirs(index_dir)

    # Whoosh 스키마 정의
    # TEXT: 토큰화되어 검색 가능 / ID: 그대로 저장 / STORED: 저장만
    schema = Schema(
        id=ID(stored=True),
        title=TEXT(stored=True, analyzer=StandardAnalyzer(), field_boost=2.0),  # 제목 가중치 2배
        url=ID(stored=True),
        keywords=TEXT(stored=True, field_boost=1.5),   # 키워드 가중치 1.5배
        content=TEXT(stored=False),                     # 본문 (저장 안 함, 검색만)
        site=STORED(),
        scraped_at=STORED(),
    )

    ix = create_in(index_dir, schema)
    writer = ix.writer()

    # DB에서 데이터 읽기
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, title, url, keywords, summary, site, scraped_at FROM pages")
    rows = c.fetchall()
    conn.close()

    if not rows:
        print("[WARN] DB에 데이터가 없습니다. 먼저 scraper.py를 실행하세요.")
        return 0

    indexed = 0
    for row in rows:
        id_, title, url, keywords, summary, site, scraped_at = row
        writer.add_document(
            id=str(id_),
            title=title or "",
            url=url or "",
            keywords=keywords or "",
            content=(title or "") + " " + (keywords or "") + " " + (summary or ""),
            site=site or "",
            scraped_at=scraped_at or "",
        )
        indexed += 1

    writer.commit()
    print(f"[OK] {indexed}개 문서 인덱싱 완료 → '{index_dir}/' 폴더")
    return indexed


def show_stats(db_path="data.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT site, COUNT(*) as cnt FROM pages GROUP BY site ORDER BY cnt DESC")
    rows = c.fetchall()
    conn.close()

    if rows:
        print("\n📊 수집 현황:")
        for site, cnt in rows:
            print(f"  {site}: {cnt}개")


if __name__ == "__main__":
    config = load_config()
    db_path = config.get("db_path", "data.db")

    show_stats(db_path)
    count = build_index(db_path)

    if count > 0:
        print("\n다음 단계: python search_app.py 실행 후 http://localhost:5000 접속")
