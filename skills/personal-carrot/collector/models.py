"""
models.py
─────────
수집 데이터 모델 정의
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Product:
    """당근마켓 매물 하나를 표현하는 모델."""

    title: str
    price: int                       # 숫자 가격 (원)
    price_text: str                  # 원본 텍스트 ("15만원", "나눔" 등)
    location: str                    # 지역 ("부산진구" 등)
    time_text: str                   # "3시간 전", "끌올 1일 전" 등
    url: str = ""                    # 상품 URL (있으면)
    keyword: str = ""                # 어떤 키워드로 검색했는지
    status: str = "판매중"            # 판매중 / 예약중 / 판매완료
    collected_at: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict:
        return asdict(self)

    def to_sheet_row(self) -> list:
        """구글시트 한 행으로 변환."""
        return [
            self.collected_at,
            self.keyword,
            self.title,
            self.price,
            self.price_text,
            self.location,
            self.time_text,
            self.url,
            self.status,
        ]

    @staticmethod
    def sheet_header() -> list[str]:
        return [
            "수집일시", "키워드", "제목", "가격",
            "가격원문", "지역", "등록시간", "URL", "상태",
        ]


def parse_price(text: str) -> int:
    """
    가격 텍스트를 숫자로 변환한다.

    Examples:
        "150,000원"  → 150000
        "15만원"     → 150000
        "1.5만원"    → 15000
        "나눔"       → 0
        "가격미정"   → -1
    """
    if not text:
        return -1

    cleaned = text.replace(",", "").replace(" ", "").strip()

    # 나눔 / 무료
    if "나눔" in cleaned or "무료" in cleaned:
        return 0

    # "15만원", "1.5만원"
    m = re.match(r"([\d.]+)\s*만\s*원?", cleaned)
    if m:
        return int(float(m.group(1)) * 10_000)

    # "150000원", "150000"
    digits = re.sub(r"[^\d]", "", cleaned)
    if digits:
        return int(digits)

    return -1  # 파싱 불가
