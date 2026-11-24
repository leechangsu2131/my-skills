"""NotebookLM 에 올릴 지도서 소스 만들기 (규칙 변환, LLM 없음).

    py -3.13 notebook_sources.py               # 남은 수업이 있는 단원만, 모든 과목
    py -3.13 notebook_sources.py 수학 국어     # 이 과목만
    py -3.13 notebook_sources.py --all --open  # 진도표의 모든 단원, 끝나면 폴더 열기

만드는 것 (데이터 폴더 notebooklm/<과목>/):
- <대단원>.md : 단원 하나 = 소스 하나. 지도서 글자만 뽑고 차시마다 표시를 심는다.
      ## [수학 6단원] 4차시 그림그래프로 나타내는 방법 (지도서 p.25~28)
  → NotebookLM 에 "[수학 6단원] 4차시" 로 물으면 그 부분을 찾는다. 차시 번호·제목은 진도표 그대로.
- <대단원>_그림.pdf : 글자가 거의 없는 쪽(그림·악보·스캔)을 흑백으로 줄인 PDF.
  음악·미술(config notebooklm_image_subjects)은 단원 전체를 넣는다. 쪽마다 위 표시를 글자로 적어 둔다.

차시 나누기 규칙
- 분할본(pdf_splits)·차시별 파일: 진도표 행의 파일 하나 = 한 구간. 같은 파일을 쓰는 차시는 묶는다(예: 1~3차시).
- 단원 한 권(국어): 쪽 머리의 '3~4차시 / 14차시' 표시로 차시 시작 쪽을 찾는다. 첫 차시 앞쪽은 '단원 개관'.
- 시작·끝페이지가 적힌 통짜 지도서: 그 쪽만.
- 수학처럼 분할 결과에 '단원 개관'(plan) 묶음이 있으면 맨 앞에 넣는다.

업로드는 교사가 학기에 한 번 직접 한다(NotebookLM 공개 API 없음). 과목별 노트북 1개.
노트북 주소를 config subjects.<과목>.notebooklm 에 적으면 수업 비서의 NotebookLM 단추가 그 노트북을 연다.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys
import time

import build_units as bu  # schedule·fitz·assistant_server 를 함께 불러온다
from build_units import app, fitz, schedule

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "util-notebooklm"))
import nlm  # noqa: E402  (공용: 글자 뽑기·흑백 그림 PDF·소스 쓰기)

IMAGE_SUBJECTS_DEFAULT = ["음악", "미술"]
KOREAN_LESSON = re.compile(r"(\d{1,2})(?:\s*[~∼]\s*(\d{1,2}))?\s*차시\s*/\s*\d{1,2}\s*차시")
STAGE = re.compile(r"이 차시는\s*[‘'\"“]([^’'\"”]{1,12})[’'\"”]\s*학습")


# ──────────────────────────── 진도표 → 차시 묶음 ────────────────────────────

def page_range(row: dict) -> tuple[int, int] | None:
    try:
        a = int(str(row.get("시작페이지", "")).strip())
        b = int(str(row.get("끝페이지", "")).strip() or a)
    except ValueError:
        return None
    return (a, b) if 1 <= a <= b else None


def pdf_of(row: dict) -> str:
    return schedule.resolve_pdf_path(row.get("pdf파일", ""))


def lesson_groups(rows: list[dict]) -> list[dict]:
    """같은 수업내용·같은 PDF 가 이어지는 행을 한 차시 묶음으로."""
    out: list[dict] = []
    for r, n in zip(rows, bu.infer_lesson_numbers(rows)):
        if n is None:
            continue
        title, pdf, pages = str(r.get("수업내용", "")).strip(), pdf_of(r), page_range(r)
        last = out[-1] if out else None
        if last and last["title"] == title and last["pdf"] == pdf and n in (last["to"], last["to"] + 1):
            last["to"] = n
        else:
            out.append({"from": n, "to": n, "title": title, "pdf": pdf, "pages": pages})
    return out


def heading(tag: str, groups: list[dict], where: str) -> str:
    titles = list(dict.fromkeys(g["title"] for g in groups if g["title"]))
    rng = app.lesson_range(groups[0]["from"], groups[-1]["to"])
    return f"## {tag} {rng} {' / '.join(titles)}".rstrip() + (f" ({where})" if where else "")


def is_split(pdf: str) -> bool:
    return "pdf_splits" in [p.casefold() for p in pathlib.Path(pdf).parts]


# ──────────────────────────── 구간 만들기 ────────────────────────────
# 구간 = {"heading", "pdf", "pages": [(파일 쪽 0부터, 표시 쪽 번호)], "note"}

def sections_for(tag: str, unit: str, groups: list[dict]) -> list[dict]:
    secs: list[dict] = []
    first_pdf = next((g["pdf"] for g in groups if g["pdf"]), "")
    lesson_pdfs = {os.path.normcase(g["pdf"]) for g in groups}
    if first_pdf and pathlib.Path(first_pdf).is_file():
        plan = bu.plan_split(pathlib.Path(first_pdf), unit)
        if plan and os.path.normcase(str(plan)) not in lesson_pdfs:
            secs.append(whole(f"## {tag} 단원 개관", str(plan), book_start(plan)))
    buckets: list[list[dict]] = []
    for g in groups:
        if buckets and buckets[-1][0]["pdf"] == g["pdf"]:
            buckets[-1].append(g)
        else:
            buckets.append([g])
    for b in buckets:
        pdf = b[0]["pdf"]
        if not pdf or not pathlib.Path(pdf).is_file():
            name = pathlib.Path(pdf).name if pdf else "진도표에 경로 없음"
            secs.append({"heading": heading(tag, b, ""), "pdf": "", "pages": [],
                         "note": f"(이 PC에 지도서 PDF가 없어 글자를 넣지 못함: {name})"})
            continue
        split = is_split(pdf)
        if not split and all(g["pages"] for g in b):
            for g in b:
                a, z = g["pages"]
                secs.append(slice_sec(heading(tag, [g], f"지도서 p.{a}~{z}"), pdf, a - 1, z - 1, a))
        elif not split and len(b) > 1:
            secs.extend(by_korean_markers(tag, b, pdf))
        else:
            start = b[0]["pages"][0] if split and b[0]["pages"] else None
            secs.append(whole(heading(tag, b, where_text(pdf, b)), pdf, start))
    return secs


def book_start(pdf: pathlib.Path) -> int | None:
    m = re.search(r"_p(\d+)-\d+\.pdf$", pdf.name)
    return int(m.group(1)) if m else None


def where_text(pdf: str, b: list[dict]) -> str:
    if is_split(pdf) and b[0]["pages"]:
        a, z = b[0]["pages"][0], b[-1]["pages"][1]
        return f"지도서 p.{a}~{z}"
    return f"지도서 {pathlib.Path(pdf).name}"


def page_count(pdf: str) -> int:
    with fitz.open(pdf) as doc:
        return doc.page_count


def whole(head: str, pdf: str, start: int | None) -> dict:
    return nlm.whole_section(head, pdf, start)


def slice_sec(head: str, pdf: str, a: int, z: int, label_start: int) -> dict:
    n = page_count(pdf)
    a, z = max(0, a), min(n - 1, z)
    return {"heading": head, "pdf": pdf, "note": "",
            "pages": [(i, label_start + (i - a)) for i in range(a, z + 1)]}


def by_korean_markers(tag: str, b: list[dict], pdf: str) -> list[dict]:
    """단원 한 권 PDF: '3~4차시 / 14차시' 가 처음 나오는 쪽을 그 차시 시작으로."""
    starts: dict[int, int] = {}
    with fitz.open(pdf) as doc:
        n = doc.page_count
        for i in range(n):
            m = KOREAN_LESSON.search(bu.head(doc, i))
            if m and int(m.group(1)) not in starts:
                starts[int(m.group(1))] = i
    found = [(starts[g["from"]], g) for g in b if g["from"] in starts]
    found.sort(key=lambda x: x[0])
    if not found:
        found = by_stage_markers(pdf, b)
        starts = {g["from"]: p for p, g in found}
    if not found:
        return [whole(heading(tag, b, f"지도서 {pathlib.Path(pdf).name}, 차시 표시 못 찾음"), pdf, None)]
    secs = []
    if found[0][0] > 0:
        secs.append(slice_sec(f"## {tag} 단원 개관 (지도서 파일 p.1~{found[0][0]})", pdf, 0, found[0][0] - 1, 1))
    missing = [g for g in b if g["from"] not in starts]
    for k, (page, g) in enumerate(found):
        end = found[k + 1][0] - 1 if k + 1 < len(found) else n - 1
        # 표시를 못 찾은 차시는 바로 앞 차시 구간에 함께 넣는다
        extra = [m for m in missing if g["from"] < m["from"] < (found[k + 1][1]["from"] if k + 1 < len(found) else 999)]
        secs.append(slice_sec(heading(tag, [g] + extra, f"지도서 파일 p.{page + 1}~{end + 1}"), pdf, page, end, page + 1))
    return secs


def by_stage_markers(pdf: str, b: list[dict]) -> list[tuple[int, dict]]:
    """국어 매체 단원처럼 차시 번호 대신 "이 차시는 '다가가기' 학습으로" 로 나뉜 경우.
    단계가 바뀌는 쪽 수가 차시 묶음 수와 같을 때만 차례대로 짝짓는다."""
    pages: list[int] = []
    last = None
    with fitz.open(pdf) as doc:
        for i in range(doc.page_count):
            m = STAGE.search(" ".join(bu.CTL.sub(" ", doc[i].get_text()).split()))
            if m and m.group(1) != last:
                pages.append(i)
                last = m.group(1)
    return list(zip(pages, b)) if len(pages) == len(b) else []


# ──────────────────────────── 소스 쓰기 (util-notebooklm) ────────────────────────────

def build_unit(subject: str, unit: str, rows: list[dict], cfg: dict, image_subjects: list[str]) -> str:
    tag = app.lesson_tag(subject, unit)
    groups = lesson_groups(rows)
    secs = sections_for(tag, unit, groups)
    all_pages = subject in image_subjects
    folder = app.NOTEBOOKLM / app.safe_name(subject)
    md_path = folder / f"{app.safe_name(unit)}.md"
    img_path = folder / f"{app.safe_name(unit)}_그림.pdf"
    info = cfg.get("subjects", {}).get(subject, {})
    header = [f"# {tag} {unit}", "",
              f"과목: {subject} · 출판사: {info.get('publisher', '')} · 학년·학기: {cfg.get('grade_term', '')} · 만든 날: {time.strftime('%Y-%m-%d')}",
              "", f"교사용 지도서의 글자를 차시별로 나눈 자료입니다. 각 차시는 \"## {tag} N차시\" 제목으로 시작하고,",
              "〔p.N〕은 지도서 쪽 번호입니다.", "", "차시 목록:"]
    header += [f"- {app.lesson_range(g['from'], g['to'])} {g['title']}" for g in groups]
    r = nlm.write_source(md_path, img_path, header, secs, "all" if all_pages else "auto")
    warn = f" ⚠ {r['words']:,}단어 — NotebookLM 한도(50만) 가까움" if r["too_big"] else ""
    extra = f", 그림 쪽 {r['low_pages']}" if r["low_pages"] and not all_pages else ""
    img = f" + {img_path.name}({r['gray_pages']}쪽)" if r["gray_pages"] else ""
    return (f"[{subject}] {unit}: 구간 {len(secs)}개, {r['words']:,}단어{extra}{img}"
            + (f", PDF 없음 {r['missing']}" if r["missing"] else "") + warn)


# ──────────────────────────── 실행 ────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="NotebookLM 소스(단원별 md) 만들기")
    ap.add_argument("subjects", nargs="*", help="과목 (없으면 전부)")
    ap.add_argument("--all", action="store_true", help="끝난 단원도 만들기")
    ap.add_argument("--open", action="store_true", help="끝나면 폴더 열기")
    args = ap.parse_args()
    cfg = app.load_config()
    image_subjects = cfg.get("notebooklm_image_subjects", IMAGE_SUBJECTS_DEFAULT)
    records = bu.load_progress_records()
    units: dict[tuple[str, str], list[dict]] = {}
    for r in sorted(records, key=lambda r: r.get("_row", 0)):
        subject, unit = str(r.get("과목", "")).strip(), str(r.get("대단원", "")).strip()
        if subject and unit and (not args.subjects or subject in args.subjects):
            units.setdefault((subject, unit), []).append(r)
    report = []
    for (subject, unit), rows in units.items():
        if not args.all and all(schedule._is_done(r) for r in rows):
            continue
        try:
            report.append(build_unit(subject, unit, rows, cfg, image_subjects))
        except Exception as exc:  # 한 단원이 실패해도 나머지는 만든다
            report.append(f"[{subject}] {unit}: 실패 — {exc}")
    for line in report:
        print(line)
    guide = ["NotebookLM 업로드 안내 (학기에 한 번)",
             "1. 과목마다 노트북을 하나 만들고, 그 과목 폴더의 .md 와 _그림.pdf 를 소스로 올린다.",
             "2. 노트북 주소를 config.json 의 subjects.<과목>.notebooklm 에 적는다.",
             "3. 수업 비서의 NotebookLM 단추가 그 노트북을 열고 '[과목 N단원] N차시' 질문을 복사한다.",
             "4. 답을 북마클릿으로 md 로 받았으면: py -3.13 split_notes.py <받은.md> → 차시별 노트로 나뉘어 'AI와 수업 준비' 폴더에 함께 들어간다.",
             "", f"만든 때: {time.strftime('%Y-%m-%d %H:%M')}", *report]
    app.NOTEBOOKLM.mkdir(parents=True, exist_ok=True)
    (app.NOTEBOOKLM / "목록.txt").write_text("\n".join(guide) + "\n", encoding="utf-8")
    if args.open:
        subprocess.Popen(["explorer", str(app.NOTEBOOKLM)])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
