"""
sqlite_db.py
────────────
SQLite 기반 로컬 저장소 — 중복 체크 및 수집 이력 관리.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from collector.models import Product


class DaangnDB:
    """SQLite 데이터베이스 관리자."""

    def __init__(self, db_path: str = "data/daangn.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """테이블을 생성한다."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA journal_mode=WAL")

        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                price       INTEGER,
                price_text  TEXT,
                location    TEXT,
                time_text   TEXT,
                url         TEXT,
                keyword     TEXT,
                status      TEXT DEFAULT '판매중',
                collected_at TEXT,
                dedup_key   TEXT UNIQUE
            );

            CREATE TABLE IF NOT EXISTS collection_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword     TEXT,
                count       INTEGER,
                timestamp   TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_dedup_key
                ON products(dedup_key);

            CREATE INDEX IF NOT EXISTS idx_keyword
                ON products(keyword);
        """)
        self.conn.commit()

    def insert_products(self, products: list[Product]) -> int:
        """
        상품 리스트를 삽입한다 (중복은 무시).
        삽입된 건수를 반환한다.
        """
        inserted = 0
        for p in products:
            dedup_key = p.url if p.url else f"{p.title}_{p.price}_{p.location}"
            try:
                self.conn.execute(
                    """INSERT INTO products
                       (title, price, price_text, location, time_text,
                        url, keyword, status, collected_at, dedup_key)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        p.title, p.price, p.price_text, p.location,
                        p.time_text, p.url, p.keyword, p.status,
                        p.collected_at, dedup_key,
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                # 중복 — 건너뛰기
                pass

        if inserted > 0:
            self.conn.commit()

        return inserted

    def log_collection(self, keyword: str, count: int) -> None:
        """수집 로그를 기록한다."""
        self.conn.execute(
            "INSERT INTO collection_logs (keyword, count, timestamp) VALUES (?, ?, ?)",
            (keyword, count, datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()

    def is_duplicate(self, product: Product) -> bool:
        """이미 수집된 상품인지 확인한다."""
        dedup_key = product.url if product.url else f"{product.title}_{product.price}_{product.location}"
        cursor = self.conn.execute(
            "SELECT 1 FROM products WHERE dedup_key = ? LIMIT 1",
            (dedup_key,),
        )
        return cursor.fetchone() is not None

    def filter_new(self, products: list[Product]) -> list[Product]:
        """중복을 제거하고 새 상품만 반환한다."""
        new_products = [p for p in products if not self.is_duplicate(p)]
        skipped = len(products) - len(new_products)
        if skipped > 0:
            print(f"  🔄 중복 제거: {skipped}건 스킵")
        return new_products

    def get_stats(self) -> dict:
        """DB 통계를 반환한다."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM products")
        total = cursor.fetchone()[0]

        cursor = self.conn.execute(
            "SELECT keyword, COUNT(*) FROM products GROUP BY keyword"
        )
        by_keyword = dict(cursor.fetchall())

        cursor = self.conn.execute(
            "SELECT MAX(collected_at) FROM products"
        )
        last = cursor.fetchone()[0]

        return {"total": total, "by_keyword": by_keyword, "last_collected": last}

    def cleanup_old(self, days: int = 30) -> int:
        """오래된 데이터를 삭제한다."""
        cursor = self.conn.execute(
            "DELETE FROM products WHERE collected_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        self.conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        """DB 연결을 닫는다."""
        if self.conn:
            self.conn.close()
