"""단원 개관 자동 만들기 (LLM 판단 없이 규칙으로).

    py -3.13 build_units.py            # 남은 수업이 있는 단원만
    py -3.13 build_units.py --all      # 진도표의 모든 단원
    py -3.13 build_units.py --if-older 12   # 마지막 실행이 12시간 안이면 건너뜀(실행.bat 용)

만드는 것 (데이터 폴더 units/):
- <과목>__<대단원>.json 의 "lessons": 진도표 행(차시·수업내용)을 그대로 묶어 만든다 → 화면의 단원 흐름, 지금 차시 표시.
- <과목>__<대단원>.pdf: 그 단원 1차시 지도서 PDF 에서 '첫 차시가 시작되는 쪽' 앞까지를 잘라 낸 단원 개관.
  · 수학처럼 분할 결과(groups.json)에 '단원 개관'(detected_level=plan) 묶음이 있으면 그 파일을 쓴다.
  · 차시 시작 표시: '1차시 / 14차시'(국어), '1 4 … 차시 목표'(도덕), '12차시 1'(수학), '2 2 차시 교과서'(사회).
  · 표시를 못 찾으면 12쪽 이하 파일은 통째로, 더 길면 앞 6쪽.
- 이미 있는 summary·goals·cautions·assessment(사람이나 AI가 쓴 것)는 지우지 않는다.

진도표는 Supabase에서 읽고, `schedule_backend`가 `google_sheets`일 때만 teacherlesson-schedule의 시트 연결을 쓴다.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "teacherlesson-schedule"))
import schedule  # noqa: E402
import fitz  # noqa: E402

import assistant_server as app  # noqa: E402  (data 폴더·safe_name 공유)

STAMP = app.UNITS / ".last_build"
CTL = re.compile(r"[\x00-\x08\x0b-\x1f\u200b-\u200d\ufeff]")
LESSON_START = [
    re.compile(r"\d{1,2}(?:\s*[~∼]\s*\d{1,2})?\s*차시\s*/\s*\d{1,2}\s*차시"),       # 국어: 1차시 / 14차시
    re.compile(r"^\d\s+\d\s.{0,150}차시\s*목표"),                                  # 도덕: 1 4 … 차시 목표
    re.compile(r"^\d{1,2}\s*차시\s+\d{1,2}(?![\d쪽~])"),                           # 수학: 12차시 1
    re.compile(r"^\d{1,2}\s+\d{1,2}\s*차시(?!\s*[/목])"),                          # 수학: 10 12차시
    re.compile(r"\d{1,2}(?:\s*~\s*\d{1,2})?\s+\d{1,2}(?:\s*~\s*\d{1,2})?\s*차시\s*교과서"),  # 사회: 2 2 차시 교과서
]


def head(doc, i: int, n: int = 240) -> str:
    return " ".join(CTL.sub(" ", doc[i].get_text()).split())[:n]


def lesson_no(value) -> int | None:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else None


def group_lessons(rows: list[dict]) -> list[dict]:
    """진도표 행을 같은 수업내용끼리 묶어 {from,to,title}."""
    out = []
    for r in rows:
        n = lesson_no(r.get("차시"))
        title = str(r.get("수업내용", "")).strip()
        if n is None:
            continue
        if out and out[-1]["title"] == title and n == out[-1]["to"] + 1:
            out[-1]["to"] = n
        else:
            out.append({"from": n, "to": n, "title": title})
    for x in out:
        if x["to"] == x["from"]:
            del x["to"]
    return out


def load_progress_records() -> list[dict]:
    """Read current progress from the selected backend (Supabase by default)."""
    if app.load_config().get("schedule_backend", "supabase") == "supabase":
        import supabase_schedule
        return supabase_schedule.records()
    ws = schedule.connect()
    return schedule.load_all(ws)


def plan_split(pdf: pathlib.Path, unit: str) -> pathlib.Path | None:
    """분할 결과 groups.json 에 이 단원의 '단원 개관'(plan) 묶음이 있으면 그 PDF."""
    for groups_path in (pdf.parent.parent / "groups.json", pdf.parent / "groups.json"):
        if not groups_path.is_file():
            continue
        try:
            data = json.loads(groups_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for g in data.get("groups", []):
            if g.get("detected_level") == "plan" and str(g.get("parent_unit_title", "")).strip() == unit:
                hits = sorted((groups_path.parent / "pdf_splits").glob(f"*subunit_{int(g['index']):02d}_*_p{g['start_page']}-{g['end_page']}.pdf"))
                if hits:
                    return hits[0]
    return None


def overview_pages(pdf: pathlib.Path) -> tuple[int, int]:
    doc = fitz.open(pdf)
    try:
        for i in range(1, min(doc.page_count, 40)):
            text = head(doc, i)
            if any(rx.search(text) for rx in LESSON_START):
                return 0, i - 1
        return (0, doc.page_count - 1) if doc.page_count <= 12 else (0, 5)
    finally:
        doc.close()


def build(only_open: bool) -> list[str]:
    records = load_progress_records()
    units: dict[tuple[str, str], list[dict]] = {}
    for r in sorted(records, key=lambda r: r.get("_row", 0)):
        subject, unit = str(r.get("과목", "")).strip(), str(r.get("대단원", "")).strip()
        if subject and unit:
            units.setdefault((subject, unit), []).append(r)
    report = []
    for (subject, unit), rows in units.items():
        if only_open and all(schedule._is_done(r) for r in rows):
            continue
        base = f"{app.safe_name(subject)}__{app.safe_name(unit)}"
        path = app.UNITS / f"{base}.json"
        data = app.read_json(path, {}) if path.is_file() else {}
        data.update({"subject": subject, "unit": unit, "lessons": group_lessons(rows), "auto": True})
        first_pdf = next((pathlib.Path(str(r.get("pdf파일", ""))) for r in rows if str(r.get("pdf파일", "")).strip()), None)
        note = ""
        if first_pdf and first_pdf.is_file():
            src = plan_split(first_pdf, unit)
            out_pdf = app.UNITS / f"{base}.pdf"
            if src:
                out_pdf.write_bytes(src.read_bytes())
                note = f"분할본 단원 개관 {src.name[-20:]}"
                data["source"] = data.get("source") or f"{src.name}"
            else:
                a, b = overview_pages(first_pdf)
                doc = fitz.open(first_pdf)
                part = fitz.open()
                part.insert_pdf(doc, from_page=a, to_page=b)
                part.save(out_pdf, garbage=3, deflate=True)
                part.close(); doc.close()
                note = f"{first_pdf.name} p{a + 1}-{b + 1}"
                data["source"] = data.get("source") or f"{first_pdf.name} p{a + 1}-{b + 1}"
            data["overview_pdf"] = out_pdf.name
        else:
            note = "지도서 PDF 없음(진도표 경로 확인)"
        app.write_json(path, data)
        report.append(f"[{subject}] {unit}: 차시 묶음 {len(data['lessons'])}개 · {note}")
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--if-older", type=float, default=0, help="마지막 실행 뒤 이 시간(시) 안이면 건너뜀")
    args = ap.parse_args()
    app.UNITS.mkdir(parents=True, exist_ok=True)
    if args.if_older and STAMP.is_file() and time.time() - STAMP.stat().st_mtime < args.if_older * 3600:
        print("단원 개관: 최근에 만들어 건너뜀")
        return
    for line in build(only_open=not args.all):
        print(line)
    STAMP.write_text(time.strftime("%Y-%m-%d %H:%M"), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
