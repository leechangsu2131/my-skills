#!/usr/bin/env python3
"""
초등 교사용 지도서 PDF를 '단원의 지도 계획' 표 기준으로 소단원(좌측 큰 항목)별로 자르는 스크립트.

원래 teacher_guide_app의 split 로직을 의존성(teacher_guide_app/extractor.py) 없이
Skill 내부에서 바로 동작하도록 재구성했습니다.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Optional

from pypdf import PdfReader, PdfWriter


def normalize_space(text: str) -> str:
    return " ".join((text or "").split())


def sanitize_filename_part(value: str) -> str:
    cleaned = normalize_space(value)
    cleaned = re.sub(r'[<>:"/\\\\|?*]', "_", cleaned)
    cleaned = cleaned.replace("\n", " ").replace("\r", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._")
    return cleaned


def parse_page_ranges(cell_text: str) -> list[tuple[int, int]]:
    """
    '6-11', '16~23', '6 - 11' 같은 형태를 읽어 (start,end) 목록으로 반환.
    숫자가 하나만 있으면 (n,n).
    """
    t = normalize_space(cell_text or "")
    if not t:
        return []

    range_re = re.compile(r"(\d{1,3})\s*[-~–—]\s*(\d{1,3})")
    ranges = [(int(a), int(b)) for a, b in range_re.findall(t)]

    if not ranges:
        nums = [int(x) for x in re.findall(r"\b\d{1,3}\b", t)]
        if not nums:
            return []
        return [(min(nums), max(nums))]

    normalized: list[tuple[int, int]] = []
    for s, e in ranges:
        if e < s:
            s, e = e, s
        normalized.append((s, e))
    return normalized


def extract_pdf_range(pdf_path: Path, start_page_1based: int, end_page_1based: int, output_path: Path) -> Path:
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)

    s = max(1, int(start_page_1based))
    e = min(total, int(end_page_1based))
    if e < s:
        s, e = e, s

    writer = PdfWriter()
    # pypdf uses 0-based page indices
    for i in range(s - 1, e):
        writer.add_page(reader.pages[i])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path


def score_table_for_plan(table: list[list[Optional[str]]]) -> int:
    """
    추출된 테이블들 중 '단원의 지도 계획' 표 가능성을 간단 점수화합니다.
    """
    if not table:
        return -1
    flat: list[str] = []
    for row in table:
        flat.extend([c for c in row if c is not None])
    combined = " ".join(normalize_space(str(x)) for x in flat if str(x).strip()).lower()

    page_range_pat = re.compile(r"\d{1,3}\s*[-~–—]\s*\d{1,3}|\b\d{1,3}\b")
    page_score = len(page_range_pat.findall(combined))
    hit_z = 2 if re.search(r"\b지\b", combined) else 0
    hit_cols = 2 if ("교" in combined and "지" in combined) else 0
    hit_title = 4 if ("차시" in combined and ("단원" in combined or "지도" in combined)) else 0
    return hit_cols + hit_z + hit_title + page_score // 2


def detect_guide_z_column(table: list[list[Optional[str]]]) -> Optional[int]:
    """
    표에서 '지' 컬럼 인덱스를 추정합니다.
    """
    if not table:
        return None
    max_cols = max((len(r) for r in table), default=0)
    if max_cols == 0:
        return None

    z_patterns = ("지", "지도서")
    col_scores: dict[int, int] = defaultdict(int)

    for row in table[:10]:
        for idx in range(len(row)):
            cell = normalize_space(row[idx] or "")
            if not cell:
                continue
            if cell in z_patterns:
                col_scores[idx] += 4
            elif any(p in cell for p in z_patterns) and len(cell) <= 10:
                col_scores[idx] += 2

    if not col_scores:
        return None
    return max(col_scores.items(), key=lambda x: x[1])[0]


def find_plan_table_pages(pdfplumber_doc, scan_pages: int, title_keywords: Iterable[str]) -> list[int]:
    keywords = [k.lower() for k in title_keywords]
    total = len(pdfplumber_doc.pages)
    scan = min(scan_pages, total)

    candidates: list[int] = []
    for i in range(scan):
        try:
            text = pdfplumber_doc.pages[i].extract_text() or ""
            t = text.lower()
            if any(kw in t for kw in keywords):
                candidates.append(i)
        except Exception:
            continue

    return candidates


def extract_tables_from_page(page) -> list[list[list[Optional[str]]]]:
    tables: list[list[list[Optional[str]]]] = []
    try:
        found = page.find_tables()
        for t in found[:5]:
            try:
                extracted = t.extract()
                if extracted:
                    tables.append(extracted)
            except Exception:
                continue
    except Exception:
        pass

    if not tables:
        try:
            extracted_all = page.extract_tables() or []
            for t in extracted_all[:5]:
                if t:
                    tables.append(t)
        except Exception:
            pass

    return tables


def build_groups_from_tables(
    tables: list[list[list[Optional[str]]]] ,
    guide_z_col_override: Optional[int],
) -> list[dict]:
    """
    테이블 목록을 순회하며 '큰 항목(좌측)'별 '지'쪽 페이지 범위를 합쳐 그룹을 만듭니다.
    """
    groups: dict[str, dict] = {}
    current_group_key: Optional[str] = None

    for table in tables:
        if not table:
            continue

        z_col = guide_z_col_override
        if z_col is None:
            z_col = detect_guide_z_column(table)
        if z_col is None:
            z_col = max((len(r) for r in table if r), default=0) - 1
            if z_col < 0:
                continue

        for row in table:
            if not row:
                continue
            left_cell = normalize_space(row[0] if len(row) > 0 and row[0] is not None else "")
            z_cell = normalize_space(row[z_col] if len(row) > z_col and row[z_col] is not None else "")

            if not left_cell and not z_cell:
                continue

            if left_cell in ("교", "지", "차시", "단원"):
                continue

            if left_cell:
                current_group_key = left_cell
            if not current_group_key:
                continue

            if not z_cell:
                continue

            page_ranges = parse_page_ranges(z_cell)
            if not page_ranges:
                continue

            if current_group_key not in groups:
                groups[current_group_key] = {
                    "title": current_group_key,
                    "page_ranges": [],
                    "row_evidence": 0,
                }

            groups[current_group_key]["page_ranges"].extend(page_ranges)
            groups[current_group_key]["row_evidence"] += 1

    out: list[dict] = []
    for key, g in groups.items():
        all_starts = [s for s, _e in g["page_ranges"]]
        all_ends = [e for _s, e in g["page_ranges"]]
        if not all_starts or not all_ends:
            continue
        out.append(
            {
                "title": key,
                "start_page": min(all_starts),
                "end_page": max(all_ends),
                "row_evidence": g["row_evidence"],
                "page_ranges": g["page_ranges"],
            }
        )

    out.sort(key=lambda x: (x["start_page"], x["title"]))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="지도서 '단원의 지도 계획' 표 기준 소단원 PDF 분할")
    parser.add_argument("--pdf", required=True, type=str, help="입력 PDF 경로")
    parser.add_argument("--out-dir", default="output", type=str, help="출력 폴더")
    parser.add_argument("--dry-run", action="store_true", help="분할 저장은 하지 않고 groups.json만 생성")
    parser.add_argument("--save", action="store_true", help="groups.json 기반으로 실제 PDF 저장")
    parser.add_argument("--scan-pages", default=60, type=int, help="앞쪽에서 표 후보 페이지를 찾는 스캔 범위")
    parser.add_argument("--page-offset", default=0, type=int, help="표의 '지' 숫자를 PDF로 변환할 오프셋")
    parser.add_argument("--z-col", default=None, type=int, help="표에서 '지' 컬럼 인덱스(0-based) 강제")
    args = parser.parse_args()

    split_subunits_from_plan_table(
        pdf_path=args.pdf,
        out_dir=args.out_dir,
        dry_run=args.dry_run,
        save=args.save,
        scan_pages=args.scan_pages,
        page_offset=args.page_offset,
        z_col=args.z_col,
    )

def split_subunits_from_plan_table(
    pdf_path: str | Path,
    out_dir: str | Path,
    *,
    dry_run: bool = True,
    save: bool = False,
    scan_pages: int = 60,
    page_offset: int = 0,
    z_col: Optional[int] = None,
) -> list[dict]:
    """
    다른 앱에서 import해서 재사용할 수 있도록 제공하는 API 함수입니다.

    - dry_run=True: groups.json만 생성
    - save=True: groups.json 생성 후 분할 PDF도 저장
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일이 없습니다: {pdf_path}")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not dry_run and not save:
        dry_run = True

    pdf_base = pdf_path.stem
    run_out_dir = out_dir / pdf_base
    run_out_dir.mkdir(parents=True, exist_ok=True)

    groups_path = run_out_dir / "groups.json"

    # 로컬 의존: pdfplumber는 동적 import으로 메시지를 조금 더 명확히 하기 위함
    try:
        import pdfplumber
    except ImportError:
        raise SystemExit("pdfplumber가 설치되어 있지 않습니다. `pip install pdfplumber` 후 다시 시도하세요.")

    title_keywords = ("단원의 지도 계획", "주제의 지도 계획")
    with pdfplumber.open(str(pdf_path)) as doc:
        candidates = find_plan_table_pages(doc, scan_pages=scan_pages, title_keywords=title_keywords)
        if not candidates:
            candidates = find_plan_table_pages(doc, scan_pages=len(doc.pages), title_keywords=title_keywords)

        if not candidates:
            raise SystemExit("키워드가 포함된 '단원의 지도 계획' 페이지를 찾지 못했습니다. --scan-pages 또는 --z-col을 조정해 보세요.")

        extracted_tables: list[list[list[Optional[str]]]] = []
        for page_idx in candidates:
            page = doc.pages[page_idx]
            tables = extract_tables_from_page(page)
            for t in tables:
                extracted_tables.append(t)

        if not extracted_tables:
            raise SystemExit("후보 페이지에서 테이블 추출에 실패했습니다.")

        scored = [(score_table_for_plan(t), t) for t in extracted_tables]
        scored.sort(key=lambda x: x[0], reverse=True)
        top_tables = [t for _s, t in scored[:5]]

        groups = build_groups_from_tables(top_tables, guide_z_col_override=z_col)

    if not groups:
        raise SystemExit("표 파싱 후 그룹을 만들지 못했습니다. 테이블 추출 품질/컬럼 추정(--z-col) 문제 가능성이 있습니다.")

    final_groups: list[dict] = []
    for idx, g in enumerate(groups, start=1):
        start = g["start_page"] + page_offset
        end = g["end_page"] + page_offset
        if end < start:
            start, end = end, start
        final_groups.append(
            {
                "index": idx,
                "title": g["title"],
                "start_page": start,
                "end_page": end,
                "row_evidence": g["row_evidence"],
                "page_ranges_raw": g.get("page_ranges", []),
            }
        )

    with open(groups_path, "w", encoding="utf-8") as f:
        json.dump({"pdf": pdf_path.name, "page_offset": page_offset, "groups": final_groups}, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] groups.json 생성: {groups_path}")
    print(f"  그룹 수: {len(final_groups)}")
    for g in final_groups:
        print(f"  - {g['index']:>2} {g['title']}  p.{g['start_page']}~{g['end_page']}  (근거행 {g['row_evidence']})")

    if dry_run:
        print("\n[DRY-RUN] PDF 분할은 실행하지 않습니다. save=True로 다시 실행하세요.")
        return final_groups

    if not save:
        return final_groups

    splits_dir = run_out_dir / "pdf_splits"
    splits_dir.mkdir(parents=True, exist_ok=True)

    print("\n[STEP] 소단원별 PDF를 분할 저장합니다...")
    for g in final_groups:
        title_part = sanitize_filename_part(g["title"]) or f"group_{g['index']:02d}"
        output_name = f"subunit_{g['index']:02d}_{title_part}_p{g['start_page']}-{g['end_page']}.pdf"
        out_path = splits_dir / output_name
        out_path = extract_pdf_range(pdf_path, g["start_page"], g["end_page"], out_path)
        print(f"  ✅ {g['title']} → {out_path}")

    return final_groups


if __name__ == "__main__":
    main()

