"""Export saver: 분석 결과를 서버 파일시스템의 results/ 폴더에 자동 저장.

저장 구조:
    results/
      {ticker}_{company_name}/
        {YYYY-MM-DD}/
          valuation.json
          valuation.md
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from valuation_app.export_builder import build_export_json, build_export_markdown

RESULTS_ROOT = Path(__file__).resolve().parents[1] / "results"


def _sanitize_dirname(name: str) -> str:
    """파일시스템에 안전한 디렉토리명으로 변환."""
    # 공백 → 언더스코어, 특수문자 제거
    name = name.replace(" ", "_")
    name = re.sub(r"[^\w가-힣_-]", "", name)
    return name


def save_analysis(
    market: dict[str, Any],
    inputs: dict[str, Any],
    session: dict[str, Any],
) -> Path:
    """분석 결과를 results/ 폴더에 저장하고, 저장된 디렉토리 경로를 반환.

    Returns
    -------
    Path
        저장된 타임스탬프 디렉토리의 절대 경로.
    """
    ticker = market.get("ticker", "unknown")
    company = _sanitize_dirname(market.get("company_name", "company"))
    timestamp = datetime.now().strftime("%Y-%m-%d")

    save_dir = RESULTS_ROOT / f"{ticker}_{company}" / timestamp
    save_dir.mkdir(parents=True, exist_ok=True)

    # JSON 저장
    json_str = build_export_json(market, inputs)
    (save_dir / "valuation.json").write_text(json_str, encoding="utf-8")

    # Markdown 저장
    md_str = build_export_markdown(market, inputs, session)
    (save_dir / "valuation.md").write_text(md_str, encoding="utf-8")

    return save_dir


def get_save_history(market: dict[str, Any]) -> list[str]:
    """해당 종목의 과거 저장 이력(타임스탬프 폴더명 리스트)을 반환.

    Returns
    -------
    list[str]
        최신순 정렬된 타임스탬프 문자열 리스트. 저장 이력이 없으면 빈 리스트.
    """
    ticker = market.get("ticker", "unknown")
    company = _sanitize_dirname(market.get("company_name", "company"))
    company_dir = RESULTS_ROOT / f"{ticker}_{company}"

    if not company_dir.exists():
        return []

    timestamps = sorted(
        [d.name for d in company_dir.iterdir() if d.is_dir()],
        reverse=True,
    )
    return timestamps
