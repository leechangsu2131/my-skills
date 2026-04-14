#!/usr/bin/env python3
"""
지도서의 '단원의 지도 계획' 표에서 소단원(큰 항목)별 '지'쪽 페이지 범위를 읽어
해당 범위를 별도 PDF로 잘라 저장합니다.

예)
  python split_subunits_from_plan_table.py --pdf "지도서.pdf" --dry-run
  python split_subunits_from_plan_table.py --pdf "지도서.pdf" --save --page-offset 0
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Optional


APP_DIR = Path(__file__).parent
sys.path.insert(0, str(APP_DIR))


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
    범위가 여러 개 섞여 있어도 모두 수집합니다.
    """
    t = normalize_space(cell_text or "")
    if not t:
        return []

    # 범위(대시/틸데/물결/하이픈/대거)
    range_re = re.compile(r"(\d{1,3})\s*[-~–—]\s*(\d{1,3})")
    ranges = [(int(a), int(b)) for a, b in range_re.findall(t)]

    # 단일 숫자(범위가 없을 때/추가로 섞여 있을 때)
    if not ranges:
        nums = [int(x) for x in re.findall(r"\b\d{1,3}\b", t)]
        if not nums:
            return []
        return [(min(nums), max(nums))]

    # 만약 범위만 잡혔고 start>end가 뒤집혀 있는 경우 보정
    normalized: list[tuple[int, int]] = []
    for s, e in ranges:
        if e < s:
            s, e = e, s
        normalized.append((s, e))
    return normalized


def parse_int_like(text: str) -> Optional[int]:
    t = normalize_space(text or "")
    if not t:
        return None
    m = re.search(r"\b(\d{1,4})\b", t)
    return int(m.group(1)) if m else None


def score_table_for_plan(table: list[list[Optional[str]]]) -> int:
    """
    추출된 테이블들 중 '단원의 지도 계획' 표일 가능성을 점수화합니다.
    """
    if not table:
        return -1
    flat = []
    for row in table:
        flat.extend([c for c in row if c is not None])
    combined = " ".join(normalize_space(str(x)) for x in flat if str(x).strip())
    combined_norm = combined.lower()

    # '지' 페이지 범위 패턴과 함께 '교/지' 컬럼 키워드가 있으면 가산점
    page_range_pat = re.compile(r"\d{1,3}\s*[-~–—]\s*\d{1,3}|\b\d{1,3}\b")
    page_score = len(page_range_pat.findall(combined_norm))
    hit_z = 2 if re.search(r"\b지\b", combined_norm) else 0
    hit_cols = 2 if ("교" in combined_norm and "지" in combined_norm) else 0

    # 행 제목 힌트(차시/단원 등)
    hit_title = 4 if ("차시" in combined_norm and ("단원" in combined_norm or "지도" in combined_norm)) else 0
    return hit_cols + hit_z + hit_title + page_score // 2


def detect_guide_z_column(table: list[list[Optional[str]]]) -> Optional[int]:
    """
    표에서 '지' 컬럼 인덱스를 추정합니다.
    header가 깨져 있어도 일부 셀에 '지'가 포함되면 카운팅하여 가장 가능성 높은 컬럼을 고릅니다.
    """
    if not table:
        return None
    max_cols = max((len(r) for r in table), default=0)
    if max_cols == 0:
        return None

    z_patterns = ("지", "지도서")
    col_scores = defaultdict(int)

    for row in table[:8]:  # 상단에 헤더가 있을 가능성이 높음
        for idx in range(len(row)):
            cell = normalize_space(row[idx] or "")
            if not cell:
                continue
            # '지' 하나만 있는 셀이 가장 유력
            if cell in z_patterns:
                col_scores[idx] += 4
            elif any(p in cell for p in z_patterns) and len(cell) <= 6:
                col_scores[idx] += 2

    if not col_scores:
        return None
    return max(col_scores.items(), key=lambda x: x[1])[0]


def find_plan_table_pages(pdfplumber_doc, scan_pages: int, title_keywords: Iterable[str]) -> list[int]:
    """
    pdfplumber 문서에서 '단원의 지도 계획'과 같은 키워드가 등장한 페이지 인덱스(0-based)를 반환합니다.
    """
    keywords = [k.lower() for k in title_keywords]
    candidates: list[int] = []
    total = len(pdfplumber_doc.pages)
    scan = min(scan_pages, total)

    for i in range(scan):
        try:
            text = pdfplumber_doc.pages[i].extract_text() or ""
            t = text.lower()
            if any(kw in t for kw in keywords):
                candidates.append(i)
        except Exception:
            continue

    # 앞부분에 없으면(다른 책 구조) 뒤까지 완전 스캔(기본은 scan-pages로 충분하길 기대)
    return candidates


def extract_tables_from_page(page) -> list[list[list[Optional[str]]]]:
    """
    특정 페이지에서 테이블들을 최대한 뽑아냅니다.
    """
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
        # find_tables가 실패하면 extract_tables()로 fallback
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


def build_groups_from_tables(tables: list[list[list[Optional[str]]]] , guide_z_col_override: Optional[int]) -> list[dict]:
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
            # 컬럼 추정이 실패하면, 마지막 컬럼을 지쪽으로 가정(대부분의 표가 '지' 페이지 범위가 끝에 있음)
            z_col = max((len(r) for r in table if r), default=0) - 1
            if z_col < 0:
                continue

        # row loop
        for row in table:
            if not row:
                continue
            # row 길이가 들쭉날쭉한 경우가 있어 안전 처리
            left_cell = normalize_space(row[0] if len(row) > 0 and row[0] is not None else "")
            z_cell = normalize_space(row[z_col] if len(row) > z_col and row[z_col] is not None else "")

            # 헤더/잡음 제거
            if not left_cell and not z_cell:
                continue
            if left_cell in ("교", "지", "차시", "단원"):
                continue

            # 좌측 큰 항목 갱신(셀 병합으로 인해 다음 row부터 left_cell이 비어있을 수 있음)
            if left_cell:
                current_group_key = left_cell

            if not current_group_key:
                # 아직 그룹이 정해지지 않았는데 z만 나오는 경우는 스킵
                continue

            if not z_cell:
                continue

            page_ranges = parse_page_ranges(z_cell)
            if not page_ranges:
                continue

            # 그룹 초기화
            if current_group_key not in groups:
                groups[current_group_key] = {
                    "title": current_group_key,
                    "page_ranges": [],  # raw ranges
                    "row_evidence": 0,  # 페이지 범위를 실제로 파싱한 행 수(근거량)
                }

            groups[current_group_key]["page_ranges"].extend(page_ranges)
            groups[current_group_key]["row_evidence"] += 1

    # 그룹을 start/end로 정리
    out: list[dict] = []
    for key, g in groups.items():
        all_starts = [s for s, _e in g["page_ranges"]]
        all_ends = [e for _s, e in g["page_ranges"]]
        if not all_starts or not all_ends:
            continue
        out.append({
            "title": key,
            "start_page": min(all_starts),
            "end_page": max(all_ends),
            "row_evidence": g["row_evidence"],
            "page_ranges": g["page_ranges"],
        })

    # 시작 페이지 기준 정렬(일반적으로 위에서 아래로 진행)
    out.sort(key=lambda x: (x["start_page"], x["title"]))
    return out


def main():
    parser = argparse.ArgumentParser(description="지도서의 '단원의 지도 계획' 표로 소단원 PDF 분할")
    parser.add_argument("--pdf", required=True, type=str, help="입력 PDF 경로")
    parser.add_argument("--out-dir", default=str(Path(__file__).parent / "output"), type=str, help="출력 폴더")
    parser.add_argument("--dry-run", action="store_true", help="분할 저장은 하지 않고 groups.json만 생성")
    parser.add_argument("--save", action="store_true", help="groups.json 기반으로 PDF를 실제로 잘라 저장")
    parser.add_argument("--scan-pages", default=60, type=int, help="앞쪽에서 표 페이지 키워드 스캔할 페이지 수")
    parser.add_argument("--page-offset", default=0, type=int, help="표의 '지' 페이지 번호를 PDF 페이지로 변환하기 위한 오프셋")
    parser.add_argument("--z-col", default=None, type=int, help="표에서 '지' 컬럼 인덱스를 강제로 지정(0-based, 선택)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"PDF 파일이 없습니다: {pdf_path}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 저장 모드
    if not args.dry_run and not args.save:
        # 아무 것도 없으면 안전하게 dry-run 기본
        args.dry_run = True

    # 출력 폴더/파일 베이스명
    pdf_base = pdf_path.stem
    run_out_dir = out_dir / pdf_base
    run_out_dir.mkdir(parents=True, exist_ok=True)

    groups_path = run_out_dir / "groups.json"

    import pdfplumber
    from extractor import PDFExtractor

    title_keywords = ("단원의 지도 계획", "주제의 지도 계획")
    with pdfplumber.open(str(pdf_path)) as doc:
        candidates = find_plan_table_pages(doc, scan_pages=args.scan_pages, title_keywords=title_keywords)
        # 후보가 없으면 전 문서 스캔(마지막 수단)
        if not candidates:
            total = len(doc.pages)
            candidates = find_plan_table_pages(doc, scan_pages=total, title_keywords=title_keywords)

        if not candidates:
            raise SystemExit("키워드가 포함된 '단원의 지도 계획' 페이지를 찾지 못했습니다. --scan-pages 또는 --z-col을 조정해 보세요.")

        # 후보 페이지에서 테이블을 추출하고 점수화
        extracted_tables = []
        for page_idx in candidates:
            page = doc.pages[page_idx]
            tables = extract_tables_from_page(page)
            for t in tables:
                extracted_tables.append(t)

        if not extracted_tables:
            raise SystemExit("후보 페이지에서 테이블 추출에 실패했습니다.")

        # 점수 상위 테이블만 사용(잡음 줄이기)
        scored = [(score_table_for_plan(t), t) for t in extracted_tables]
        scored.sort(key=lambda x: x[0], reverse=True)
        top_tables = [t for _s, t in scored[:5]]

        groups = build_groups_from_tables(top_tables, guide_z_col_override=args.z_col)

    # 오프셋 적용 + PDF 분할 전 최종 정리
    final_groups: list[dict] = []
    total_groups = len(groups)
    if total_groups == 0:
        raise SystemExit("표 파싱 후 그룹을 만들지 못했습니다. (테이블 추출 실패 또는 컬럼 인덱스 추정 실패 가능)")

    for idx, g in enumerate(groups, start=1):
        start = g["start_page"] + args.page_offset
        end = g["end_page"] + args.page_offset
        if end < start:
            start, end = end, start
        final_groups.append({
            "index": idx,
            "title": g["title"],
            "start_page": start,
            "end_page": end,
            "row_evidence": g["row_evidence"],
            "page_ranges_raw": g.get("page_ranges", []),
        })

    with open(groups_path, "w", encoding="utf-8") as f:
        json.dump({"pdf": pdf_path.name, "page_offset": args.page_offset, "groups": final_groups}, f, ensure_ascii=False, indent=2)

    # 콘솔 요약
    print(f"\n[OK] groups.json 생성: {groups_path}")
    print(f"  그룹 수: {len(final_groups)}")
    for g in final_groups:
        print(f"  - {g['index']:>2} {g['title']}  p.{g['start_page']}~{g['end_page']}  (근거행 {g['row_evidence']})")

    if args.dry_run:
        print("\n[DRY-RUN] PDF 분할은 실행하지 않습니다. --save로 실제 저장을 진행하세요.")
        return

    # 실제 분할 저장
    extractor = PDFExtractor(output_dir=str(run_out_dir / "pdf_splits"))
    splits_dir = run_out_dir / "pdf_splits"
    splits_dir.mkdir(parents=True, exist_ok=True)

    print("\n[STEP] 소단원별 PDF를 분할 저장합니다...")
    for g in final_groups:
        title_part = sanitize_filename_part(g["title"]) or f"group_{g['index']:02d}"
        output_name = f"subunit_{g['index']:02d}_{title_part}_p{g['start_page']}-{g['end_page']}"
        out_path = extractor.extract(str(pdf_path), [g["start_page"], g["end_page"]], output_name)
        print(f"  ✅ {g['title']} → {out_path}")


if __name__ == "__main__":
    main()

