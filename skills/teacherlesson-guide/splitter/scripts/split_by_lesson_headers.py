"""쪽 머리에 '12차시 3'(전체 12차시 중 3차시)처럼 차시 표시가 있는 지도서를 차시별로 나눈다.

아이스크림 수학처럼 단원별 PDF 여러 개를 한 번에 처리해 guide-mapper 가 읽는 형식
(<폴더>/groups.json + <폴더>/pdf_splits/*_subunit_NN_<제목>_pS-E.pdf)으로 저장한다.

    python split_by_lesson_headers.py --dir "D:\\지도서\\수학 3-2" --glob "*지도서_*단원.pdf" \\
        --units "곱셈,나눗셈,원,분수,들이와 무게,그림그래프,창의 프로젝트" --dry-run

- 차시 제목은 단원 앞쪽의 '차시 및 관련 쪽수' 계획 표에서 읽는다(없으면 'N차시').
- 단원 앞쪽(개관·계획 표)은 1차시에 붙이지 않고 '단원 개관'(detected_level=plan)으로 따로 둔다.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz  # PyMuPDF

HEADER_RES = [  # (정규식, 쪽 앞 몇 글자 안에서 찾을지)
    (re.compile(r"^(?P<n>\d{1,2})\s*[~∼]\s*(?P<n2>\d{1,2})\s+(?P<total>\d{1,2})\s*차시"), 30),  # 2~3 9차시
    (re.compile(r"^(?P<total>\d{1,2})\s*차시\s+(?P<n>\d{1,2})(?!\d)"), 30),                     # 12차시 3
    (re.compile(r"^(?P<n>\d{1,2})\s+(?P<total>\d{1,2})\s*차시"), 30),                            # 10 12차시
    (re.compile(r"(?<![\d~∼])(?P<total>\d{1,2})차시\s+(?P<n>\d{1,2})(?!\s*[\d쪽~∼])"), 60),     # 프로젝트: '… 4차시 1 도입'
]
PLAN_ROW_RES = [
    re.compile(r"(?P<n>\d{1,2})(?:\s*[~∼]\s*\d{1,2})?차시\s+수\s*[\d~∼\-]+쪽(?:\s+익\s*[\d~∼\-]+쪽)?\s+(?P<title>.+?)(?=\s•|\s\d{1,2}(?:[~∼]\d{1,2})?차시\s+수|$)"),
    re.compile(r"•\s*(?P<n>\d{1,2})차시\s+(?P<title>[^•『]+?)(?=\s•|\s『|$)"),
]
CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f​-‍﻿]")


def page_text(doc, i: int) -> str:
    return " ".join(CONTROL_RE.sub(" ", doc[i].get_text()).split())


def lesson_starts(doc) -> tuple[int, dict[int, tuple[int, int]]]:
    """{첫 차시: (시작 쪽 0-based, 차시 수)} 와 전체 차시 수."""
    starts, totals, covered = {}, {}, set()
    for i in range(doc.page_count):
        text = page_text(doc, i)
        for rx, width in HEADER_RES:
            m = rx.search(text[:width]) if width > 30 else rx.match(text[:width])
            if not m:
                continue
            n, total = int(m["n"]), int(m["total"])
            n2 = int(m["n2"]) if "n2" in m.groupdict() and m["n2"] else n
            if 1 <= n <= n2 <= total and n not in covered:
                starts[n] = (i, n2 - n + 1)
                covered.update(range(n, n2 + 1))
                totals[total] = totals.get(total, 0) + 1
            break
    total = max(totals, key=totals.get) if totals else 0
    return total, {n: v for n, v in starts.items() if n <= total}


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    title = title.replace("Ö", "÷").replace("_", "×")
    # 줄바꿈 때문에 생긴 띄어쓰기 정리: '볼 까요', '확인 해요', '쓰인 다고', '자 리 수', '몇십 몇'
    title = re.sub(r"(?<=[가-힣])\s+(?=(?:까요|해요|다고|요)(?:\b|$))", "", title)
    title = title.replace("자 리", "자리").replace("몇십 몇", "몇십몇")
    return title[:60]


def plan_titles(doc, first_lesson_page: int) -> dict[int, str]:
    text = " ".join(page_text(doc, i) for i in range(min(first_lesson_page, doc.page_count)))
    titles = {}
    for rx in PLAN_ROW_RES:
        for m in rx.finditer(text):
            n = int(m["n"])
            if n not in titles and m["title"].strip():
                titles[n] = clean_title(m["title"])
        if titles:
            break
    return titles


def safe(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", text).strip()[:50]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="단원별 지도서 PDF 가 있는 폴더 (결과도 여기에)")
    ap.add_argument("--glob", default="*.pdf")
    ap.add_argument("--units", default="", help="단원 이름을 쉼표로 (파일 순서대로)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    folder = Path(args.dir)
    pdfs = sorted(folder.glob(args.glob), key=lambda p: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", p.name)])
    unit_names = [u.strip() for u in args.units.split(",") if u.strip()]
    out_dir = folder / "pdf_splits"
    groups, index = [], 0

    for unit_no, pdf in enumerate(pdfs, 1):
        doc = fitz.open(pdf)
        total, starts = lesson_starts(doc)
        unit_title = f"{unit_no}. {unit_names[unit_no - 1]}" if unit_no <= len(unit_names) else pdf.stem
        if not starts:
            print(f"[건너뜀] {pdf.name}: 차시 머리 표시를 못 찾음")
            continue
        first = min(p for p, _ in starts.values())
        titles = plan_titles(doc, first)
        covered = {n + k for n, (_, span) in starts.items() for k in range(span)}
        missing = [n for n in range(1, total + 1) if n not in covered]
        print(f"[{unit_title}] {pdf.name}: {total}차시" + (f", 빠짐 {missing}" if missing else " 모두 찾음"))

        spans = []  # (title, start, end, level, lesson_no, span)
        if first > 0:
            spans.append(("단원 개관", 0, first - 1, "plan", None, 0))
        ordered = sorted(starts.items(), key=lambda kv: kv[1][0])
        for k, (n, (s, span)) in enumerate(ordered):
            e = ordered[k + 1][1][0] - 1 if k + 1 < len(ordered) else doc.page_count - 1
            spans.append((titles.get(n, f"{n}차시"), s, e, "lesson", n, span))

        for title, s, e, level, n, span in spans:
            index += 1
            name = f"[{safe(folder.name)}]_subunit_{index:02d}_{safe(unit_title)}_{safe(title)}_p{s + 1}-{e + 1}.pdf"
            groups.append({
                "index": index, "title": title, "parent_unit_title": unit_title,
                "start_page": s + 1, "end_page": e + 1, "source_pdf": pdf.name,
                "lesson_no": n, "lesson_span": span or None, "detected_level": level,
                "context": [], "method": "lesson_header",
            })
            label = "" if n is None else (f"{n}~{n + span - 1}차시 " if span > 1 else f"{n}차시 ")
            print(f"   {index:02d} {label}{title[:40]} (p.{s + 1}-{e + 1})")
            if not args.dry_run:
                out_dir.mkdir(exist_ok=True)
                part = fitz.open()
                part.insert_pdf(doc, from_page=s, to_page=e)
                part.save(out_dir / name)
                part.close()
        doc.close()

    if not args.dry_run:
        (folder / "groups.json").write_text(json.dumps({
            "pdf": f"{folder.name} 지도서", "strategy": "lesson_header", "split_level": "detail",
            "groups": groups,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[저장] {folder / 'groups.json'} · {out_dir}")
    else:
        print("[미리보기] --dry-run 을 빼면 저장합니다.")


if __name__ == "__main__":
    main()
