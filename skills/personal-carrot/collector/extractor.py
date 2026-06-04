"""
extractor.py
────────────
수집된 Product 리스트를 pandas DataFrame으로 변환하고
JSON / CSV 등 다양한 형식으로 내보내는 유틸리티.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from .models import Product


def products_to_dataframe(products: list[Product]) -> pd.DataFrame:
    """Product 리스트를 pandas DataFrame으로 변환한다."""
    if not products:
        return pd.DataFrame(columns=Product.sheet_header())

    rows = [p.to_dict() for p in products]
    df = pd.DataFrame(rows)

    # 컬럼 순서 정리
    col_order = [
        "collected_at", "keyword", "title", "price",
        "price_text", "location", "time_text", "url", "status",
    ]
    existing = [c for c in col_order if c in df.columns]
    df = df[existing]

    return df


def save_to_json(
    products: list[Product],
    output_dir: str = "data",
    keyword: str | None = None,
) -> Path:
    """
    Product 리스트를 JSON 파일로 저장한다.

    파일명: data/daangn_레고스파이크_20260601_221500.json
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    kw_slug = (keyword or "all").replace(" ", "")
    filename = f"daangn_{kw_slug}_{timestamp}.json"
    filepath = out_path / filename

    data = [p.to_dict() for p in products]

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  💾 JSON 저장: {filepath} ({len(data)}건)")
    return filepath


def save_to_csv(
    products: list[Product],
    output_dir: str = "data",
    keyword: str | None = None,
) -> Path:
    """Product 리스트를 CSV 파일로 저장한다."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    kw_slug = (keyword or "all").replace(" ", "")
    filename = f"daangn_{kw_slug}_{timestamp}.csv"
    filepath = out_path / filename

    df = products_to_dataframe(products)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")

    print(f"  💾 CSV 저장: {filepath} ({len(products)}건)")
    return filepath


def merge_json_files(json_dir: str = "data") -> list[dict]:
    """data/ 폴더의 모든 JSON 파일을 합쳐서 반환한다."""
    all_items = []
    json_path = Path(json_dir)

    if not json_path.exists():
        return all_items

    for fp in sorted(json_path.glob("daangn_*.json")):
        with open(fp, encoding="utf-8") as f:
            items = json.load(f)
            all_items.extend(items)

    # URL 기반 중복 제거 (URL이 없으면 제목+가격으로)
    seen = set()
    deduped = []
    for item in all_items:
        key = item.get("url") or f"{item['title']}_{item['price']}"
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped


def print_summary(products: list[Product]) -> None:
    """수집 결과 요약을 출력한다."""
    if not products:
        print("\n📊 수집 결과: 0건")
        return

    df = products_to_dataframe(products)
    print(f"\n{'='*60}")
    print(f"📊 수집 결과 요약")
    print(f"{'='*60}")
    print(f"  총 매물 수: {len(df)}건")

    if "keyword" in df.columns:
        print(f"\n  키워드별:")
        for kw, group in df.groupby("keyword"):
            avg_price = group[group["price"] > 0]["price"].mean()
            print(f"    [{kw}] {len(group)}건, 평균 {avg_price:,.0f}원" if avg_price > 0 else f"    [{kw}] {len(group)}건")

    if "price" in df.columns:
        valid = df[df["price"] > 0]
        if len(valid) > 0:
            print(f"\n  가격 범위: {valid['price'].min():,}원 ~ {valid['price'].max():,}원")
            print(f"  평균 가격: {valid['price'].mean():,.0f}원")

    print(f"{'='*60}")
