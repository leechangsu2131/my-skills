#!/usr/bin/env python3
"""Notion API 진도표 업로더.

teacher-guide-subunit-splitter가 생성한 groups.json 파일을 읽어
Notion 데이터베이스(진도표)를 자동 생성합니다.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from notion_client import Client


# ---------------------------------------------------------------------------
# 1. groups.json 파싱
# ---------------------------------------------------------------------------

def parse_groups_json(path: str | Path) -> dict[str, Any]:
    """groups.json 파일을 파싱하여 진도표에 필요한 데이터를 반환합니다.

    Returns:
        {
            "pdf": str,
            "split_level": str,
            "entries": [
                {
                    "index": int,
                    "title": str,
                    "unit": str,          # 상위 단원 이름
                    "start_page": int,
                    "end_page": int,
                    "page_range": str,    # "p.1-8" 형식
                    "level": str,         # "unit" | "detail" | "section"
                },
                ...
            ]
        }
    """
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    pdf_name = raw.get("pdf", path.stem)
    split_level = raw.get("split_level", "unknown")

    # detected_groups 가 더 세부적인 항목을 담고 있으므로 우선 사용
    groups_list = raw.get("detected_groups") or raw.get("groups") or []

    entries: list[dict[str, Any]] = []
    for g in groups_list:
        # 상위 단원 결정: parent_unit_title > context[0] > ""
        unit = g.get("parent_unit_title", "")
        if not unit:
            ctx = g.get("context", [])
            unit = ctx[0] if ctx else ""

        start_page = g.get("start_page", 0)
        end_page = g.get("end_page", 0)

        entries.append(
            {
                "index": g.get("index", 0),
                "title": g.get("title", "(제목 없음)"),
                "unit": unit,
                "start_page": start_page,
                "end_page": end_page,
                "page_range": f"p.{start_page}-{end_page}",
                "level": g.get("detected_level", ""),
            }
        )

    return {
        "pdf": pdf_name,
        "split_level": split_level,
        "entries": entries,
    }


# ---------------------------------------------------------------------------
# 2. Notion 페이지 ID 유틸
# ---------------------------------------------------------------------------

def extract_page_id(url_or_id: str) -> str:
    """Notion 페이지 URL 또는 raw ID에서 32자리 페이지 ID를 추출합니다."""
    text = url_or_id.strip().rstrip("/")

    # URL 형식: https://www.notion.so/xxxxx-<32hex> 또는 https://www.notion.so/<32hex>
    if "/" in text:
        last_segment = text.rsplit("/", 1)[-1]
        # 쿼리스트링 제거
        last_segment = last_segment.split("?")[0]
        # 하이픈으로 끝나는 UUID 포함 slug 처리
        if "-" in last_segment and len(last_segment) > 32:
            last_segment = last_segment.rsplit("-", 1)[-1]
        text = last_segment

    # 하이픈 제거 후 32자리 hex인지 확인
    clean = text.replace("-", "")
    if len(clean) == 32:
        # 표준 UUID 형식으로 변환 (8-4-4-4-12)
        return (
            f"{clean[:8]}-{clean[8:12]}-{clean[12:16]}"
            f"-{clean[16:20]}-{clean[20:]}"
        )

    raise ValueError(
        f"유효한 Notion 페이지 ID를 추출할 수 없습니다: {url_or_id!r}"
    )


# ---------------------------------------------------------------------------
# 3. Notion DB 생성 및 데이터 삽입
# ---------------------------------------------------------------------------

# 수업 상태에 사용할 옵션
STATUS_OPTIONS = {
    "시작 전": {"name": "시작 전", "color": "default"},
    "진행 중": {"name": "진행 중", "color": "blue"},
    "완료": {"name": "완료", "color": "green"},
}


def _build_database_properties() -> dict[str, Any]:
    """진도표 DB의 properties 스키마를 반환합니다."""
    return {
        "차시/주제": {"title": {}},
        "순서": {"number": {"format": "number"}},
        "단원": {
            "select": {
                "options": [],  # 자동 생성됨
            },
        },
        "지도서 쪽수": {"rich_text": {}},
        "수업 상태": {
            "status": {
                "options": [
                    STATUS_OPTIONS["시작 전"],
                    STATUS_OPTIONS["진행 중"],
                    STATUS_OPTIONS["완료"],
                ],
                "groups": [
                    {
                        "name": "할 일",
                        "color": "gray",
                        "option_ids": [],
                    },
                    {
                        "name": "진행 중",
                        "color": "blue",
                        "option_ids": [],
                    },
                    {
                        "name": "완료",
                        "color": "green",
                        "option_ids": [],
                    },
                ],
            },
        },
        "수업 일자": {"date": {}},
        "출처 PDF": {"rich_text": {}},
    }


def _build_page_properties(entry: dict[str, Any], pdf_name: str) -> dict[str, Any]:
    """단일 차시 항목에 대한 Notion 페이지 properties를 생성합니다."""
    props: dict[str, Any] = {
        "차시/주제": {
            "title": [{"text": {"content": entry["title"]}}],
        },
        "순서": {"number": entry["index"]},
        "지도서 쪽수": {
            "rich_text": [{"text": {"content": entry["page_range"]}}],
        },
        "수업 상태": {
            "status": {"name": "시작 전"},
        },
        "출처 PDF": {
            "rich_text": [{"text": {"content": pdf_name}}],
        },
    }

    if entry["unit"]:
        props["단원"] = {"select": {"name": entry["unit"]}}

    return props


def create_tracker_database(
    notion_token: str,
    page_id: str,
    db_title: str,
    groups_data: dict[str, Any],
    *,
    on_progress: Any | None = None,
) -> str:
    """Notion 진도표 데이터베이스를 생성하고 항목을 삽입합니다.

    Args:
        notion_token: Notion Integration 시크릿 키
        page_id: 부모 페이지 ID (UUID 형식)
        db_title: 생성할 데이터베이스 제목
        groups_data: parse_groups_json()의 반환값
        on_progress: 진행률 콜백 fn(current, total, message)

    Returns:
        생성된 데이터베이스의 URL
    """
    notion = Client(auth=notion_token)

    entries = groups_data["entries"]
    pdf_name = groups_data["pdf"]
    total = len(entries)

    if on_progress:
        on_progress(0, total, "데이터베이스를 생성하는 중...")

    # 1) DB 생성
    new_db = notion.databases.create(
        parent={"type": "page_id", "page_id": page_id},
        title=[{"text": {"content": db_title}}],
        properties=_build_database_properties(),
    )

    db_id = new_db["id"]
    db_url = new_db.get("url", f"https://www.notion.so/{db_id.replace('-', '')}")

    # 2) 각 항목을 페이지로 삽입 (순서대로)
    for i, entry in enumerate(entries, 1):
        if on_progress:
            on_progress(i, total, f"항목 삽입 중... ({i}/{total}) {entry['title']}")

        notion.pages.create(
            parent={"database_id": db_id},
            properties=_build_page_properties(entry, pdf_name),
        )

        # Notion API rate limit 회피 (3 requests/sec 권장)
        if i < total:
            time.sleep(0.35)

    if on_progress:
        on_progress(total, total, "업로드 완료!")

    return db_url
