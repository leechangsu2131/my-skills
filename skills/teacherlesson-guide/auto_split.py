"""Extract clean, page-aware lesson sources from a teacher-guide PDF.

The source PDF stays in place. This tool sends a compact page-header index to
Gemini (not the full PDF), validates the proposed lesson boundaries, and can
write per-lesson Markdown that teacherlesson-assistant can retrieve directly.

Examples:
  python auto_split.py "D:\\지도서\\guide.pdf" --subject 수학 --unit "1단원" --inspect-only
  python auto_split.py "D:\\지도서\\guide.pdf" --subject 수학 --unit "1단원" --expected-lessons 9
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import unicodedata

import fitz

HERE = pathlib.Path(__file__).resolve().parent
ASSISTANT_DIR = HERE.parent / "teacherlesson-assistant"
sys.path.insert(0, str(ASSISTANT_DIR))
sys.path.insert(0, str(HERE.parent / "util-notebooklm"))
import assistant_server as assistant  # noqa: E402
import nlm  # noqa: E402

CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\u200b-\u200d\ufeff]")
TITLE_WORD = re.compile(r"[가-힣]{2,}|[A-Za-z0-9]{2,}")

PROMPT = """@{file}
이 파일은 교사용 지도서 PDF의 페이지별 앞부분을 뽑은 색인입니다.
각 페이지에 실제로 적힌 차시 시작 표시를 근거로 JSON만 반환하세요.

스키마:
{{"overview":{{"start_page":1,"end_page":3}},
 "lessons":[{{"start_page":4,"source_title":"쪽에 적힌 제목"}}]}}

규칙:
- 모든 쪽 번호는 색인에 적힌 PDF 물리 쪽 번호(1부터)입니다.
- 차시가 시작되는 쪽만 start_page에 넣습니다. 목차의 쪽 번호가 아니라 현재 PDF의 쪽 번호입니다.
- 여러 차시가 한 덩어리로 표시되면 from/to 범위로 묶습니다.
- overview는 첫 차시 시작 전의 단원 개관 구간입니다. 없으면 start_page와 end_page를 모두 null로 둡니다.
- lessons는 PDF에 나타나는 순서로 적습니다. 차시 표시가 없는 페이지를 추측해 추가하지 않습니다.
- source_title은 시작 쪽에 적힌 지도서 제목을 짧게 옮깁니다. 확신이 없으면 빈 문자열로 둡니다.
- JSON 외의 설명, 마크다운 코드 펜스는 쓰지 않습니다.
"""


def clean_page(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = CONTROL.sub(" ", text)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_pages(pdf: pathlib.Path) -> list[str]:
    with fitz.open(pdf) as doc:
        return [clean_page(page.get_text("text", sort=True)) for page in doc]


def page_index(pages: list[str], page_offset: int = 0, limit: int = 180) -> str:
    rows = ["# 지도서 페이지 색인", f"총 {len(pages)}쪽", ""]
    for i, text in enumerate(pages, 1):
        prefix = text[:limit]
        markers = [line for line in text.splitlines()
                   if "차시" in line and "이 차시에서" not in line and "차시 정리" not in line]
        extra = " / ".join(dict.fromkeys(markers))[:260]
        suffix = f"\n  차시표시: {extra}" if extra and extra not in prefix else ""
        rows.append(f"[p.{i + page_offset}] {prefix}{suffix}")
    return "\n".join(rows) + "\n"


def json_object(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Gemini 응답에서 JSON을 찾지 못했습니다.")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, dict) or not isinstance(data.get("lessons"), list):
        raise ValueError("응답에 lessons 목록이 없습니다.")
    return data


def merge_lesson_map(data: dict, lesson_map: list[dict] | None) -> None:
    """Use schedule numbers and names as truth; Gemini only locates pages/titles."""
    if lesson_map is None or len(data.get("lessons", [])) != len(lesson_map):
        return
    for detected, expected in zip(data["lessons"], lesson_map):
        detected["source_title"] = str(detected.get("source_title", detected.get("title", ""))).strip()
        detected["from"] = int(expected["from"])
        detected["to"] = int(expected.get("to", expected["from"]))
        detected["title"] = str(expected.get("title", "")).strip()


def unit_lesson_map(subject: str, unit: str, explicit: pathlib.Path | None) -> list[dict] | None:
    if explicit:
        path = explicit
    else:
        path = assistant.UNITS / f"{assistant.safe_name(subject)}__{assistant.safe_name(unit)}.json"
        if not path.is_file():
            return None
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    lessons = data.get("lessons")
    if not isinstance(lessons, list) or not lessons:
        raise ValueError(f"차시 목록이 비어 있습니다: {path}")
    cleaned = []
    for row in lessons:
        first = int(row.get("from"))
        last = int(row.get("to", first))
        if first < 1 or last < first:
            raise ValueError(f"차시 번호 범위가 올바르지 않습니다: {row}")
        cleaned.append({"from": first, "to": last, "title": str(row.get("title", "")).strip()})
    return cleaned


def title_matches(title: str, page_text: str) -> bool:
    words = list(dict.fromkeys(w.casefold() for w in TITLE_WORD.findall(
        unicodedata.normalize("NFKC", title)) if len(w) >= 2))
    if not words:
        return False
    normalized = unicodedata.normalize("NFKC", page_text).casefold()
    hits = sum(word in normalized for word in words)
    return hits >= max(1, (len(words) + 1) // 2)


def source_page_text(text: str) -> str:
    if not text.strip():
        return "[글자 없음: 그림/OCR 확인 필요]"
    if len(re.sub(r"\s+", "", text)) < 40:
        return text + "\n[추출 글자가 적음: 그림/OCR 확인 필요]"
    return text


def validate(data: dict, pages: list[str], expected: int | None, page_offset: int = 0,
             lesson_map: list[dict] | None = None) -> list[str]:
    issues: list[str] = []
    lessons = data["lessons"]
    first_allowed, last_allowed = page_offset + 1, page_offset + len(pages)
    if lesson_map is None:
        issues.append("진도표 차시 목록과 대조하지 않아 차시 번호가 미검증입니다. --lesson-list-json을 지정하세요.")
    elif len(lessons) != len(lesson_map):
        issues.append(f"진도표 차시 {len(lesson_map)}개와 감지한 구간 {len(lessons)}개가 다릅니다.")
    if not lessons:
        return ["차시 시작 쪽을 찾지 못했습니다."]
    previous_page = 0
    previous_to = 0
    for i, lesson in enumerate(lessons, 1):
        try:
            start = int(lesson["start_page"])
            first = int(lesson["from"])
            last = int(lesson.get("to", first))
        except (KeyError, TypeError, ValueError):
            issues.append(f"{i}번째 차시의 쪽 번호 또는 차시 번호가 숫자가 아닙니다.")
            continue
        if not (first_allowed <= start <= last_allowed):
            issues.append(f"{i}번째 차시 시작 쪽 {start}가 선택한 PDF 범위를 벗어납니다.")
        if start <= previous_page:
            issues.append(f"{i}번째 차시 시작 쪽이 앞 차시보다 앞서거나 중복됩니다.")
        if first < 1 or last < first or first <= previous_to:
            issues.append(f"{i}번째 차시 번호 범위가 앞 차시와 겹치거나 역순입니다.")
        page_idx = start - first_allowed
        if lesson_map and i <= len(lesson_map):
            expected_row = lesson_map[i - 1]
            try:
                expected_from = int(expected_row["from"])
                expected_to = int(expected_row.get("to", expected_from))
            except (KeyError, TypeError, ValueError):
                issues.append(f"진도표 차시 목록 {i}번째 행에 from/to 번호가 없습니다.")
            else:
                if (first, last) != (expected_from, expected_to):
                    issues.append(f"{i}번째 차시 번호가 진도표와 다릅니다: 감지 {first}~{last}, "
                                  f"진도표 {expected_from}~{expected_to}")
            expected_title = str(expected_row.get("title", "")).strip()
            if 0 <= page_idx < len(pages) and expected_title \
                    and not title_matches(expected_title, pages[page_idx][:700]):
                issues.append(f"{i}번째 진도표 제목의 주요 단어가 시작 쪽에서 확인되지 않습니다: {expected_title}")
        else:
            title = str(lesson.get("source_title", lesson.get("title", ""))).strip()
            if 0 <= page_idx < len(pages) and title and not title_matches(title, pages[page_idx][:700]):
                issues.append(f"{i}번째 제목이 시작 쪽 글에서 확인되지 않습니다: {title}")
        previous_page, previous_to = start, last
    overview = data.get("overview") or {}
    if lesson_map and any("단원 도입" in row["title"] for row in lesson_map):
        if isinstance(overview, dict) and overview.get("start_page") is not None:
            issues.append("진도표에 '단원 도입' 차시가 있어 별도 단원 개관 구간과 겹칩니다.")
    try:
        first_start = int(lessons[0].get("start_page", 1))
    except (AttributeError, TypeError, ValueError):
        first_start = 1
    if isinstance(overview, dict):
        a, b = overview.get("start_page"), overview.get("end_page")
        if (a is None) != (b is None):
            issues.append("단원 개관 쪽은 시작·끝을 함께 지정해야 합니다.")
        elif a is not None:
            try:
                if int(a) != first_allowed or int(b) < first_allowed or int(b) >= first_start or int(b) > last_allowed:
                    issues.append("단원 개관 쪽 범위가 첫 차시 시작 쪽과 맞지 않습니다.")
            except (TypeError, ValueError):
                issues.append("단원 개관 쪽 번호가 숫자가 아닙니다.")
    if expected is not None and len(lessons) != expected:
        issues.append(f"예상 차시 구간 {expected}개와 감지한 {len(lessons)}개가 다릅니다.")
    return issues


def make_markdown(subject: str, unit: str, data: dict, pages: list[str], page_offset: int = 0) -> str:
    rows: list[str] = [f"# [{subject} {unit}] 지도서 소스", ""]
    overview = data.get("overview") or {}
    if overview.get("start_page") is not None and overview.get("end_page") is not None:
        a, b = int(overview["start_page"]), int(overview["end_page"])
        rows += [f"## [{subject} {unit}] 단원 개관 (지도서 p.{a}~{b})", ""]
        rows.extend(f"〔p.{p}〕\n{source_page_text(pages[p - page_offset - 1])}\n" for p in range(a, b + 1))
    lessons = data["lessons"]
    for i, lesson in enumerate(lessons):
        a = int(lesson["start_page"])
        b = int(lessons[i + 1]["start_page"]) - 1 if i + 1 < len(lessons) else page_offset + len(pages)
        first, last = int(lesson["from"]), int(lesson.get("to", lesson["from"]))
        lesson_label = f"{first}~{last}차시" if first != last else f"{first}차시"
        title = str(lesson.get("title", "")).strip()
        suffix = f" {title}" if title else ""
        rows += [f"## [{subject} {unit}] {lesson_label}{suffix} (지도서 p.{a}~{b})", ""]
        rows.extend(f"〔p.{p}〕\n{source_page_text(pages[p - page_offset - 1])}\n" for p in range(a, b + 1))
    return "\n".join(rows).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="지도서 PDF에서 차시별 수업 비서 Markdown을 만듭니다.")
    ap.add_argument("pdf", type=pathlib.Path, help="원본 지도서 PDF")
    ap.add_argument("--subject", required=True, help="과목명")
    ap.add_argument("--unit", required=True, help="단원명")
    ap.add_argument("--expected-lessons", type=int, help="예상하는 차시 구간 수")
    ap.add_argument("--lesson-list-json", type=pathlib.Path,
                    help='진도표 차시 목록 JSON (예: {"lessons":[{"from":1,"to":1,"title":"..."}]})')
    ap.add_argument("--from-page", type=int, default=1, help="분석 시작 쪽 (PDF 쪽 번호, 1부터)")
    ap.add_argument("--to-page", type=int, help="분석 끝 쪽 (PDF 쪽 번호, 포함)")
    ap.add_argument("--out-dir", type=pathlib.Path, help="결과 폴더 (기본: 원본 옆 auto_split/<파일명>)")
    ap.add_argument("--publish-to-assistant", action="store_true",
                    help="검증 통과한 Markdown을 수업 비서 notebooklm/<과목>/<단원>.md에도 저장")
    ap.add_argument("--inspect-only", action="store_true", help="쪽별 색인만 만들고 Gemini 호출은 건너뜁니다.")
    ap.add_argument("--reuse-analysis", action="store_true", help="기존 analysis.json을 다시 검증해 Gemini 재호출을 피합니다.")
    ap.add_argument("--model", default=nlm.DEFAULT_MODEL, help="Gemini 모델")
    ap.add_argument("--timeout", type=int, default=300, help="Gemini 제한 시간(초)")
    a = ap.parse_args()
    pdf = a.pdf.expanduser().resolve()
    if not pdf.is_file():
        ap.error(f"PDF를 찾을 수 없습니다: {pdf}")
    out = a.out_dir or pdf.parent / "auto_split" / pdf.stem
    out.mkdir(parents=True, exist_ok=True)
    all_pages = extract_pages(pdf)
    end_page = a.to_page or len(all_pages)
    if a.from_page < 1 or end_page < a.from_page or end_page > len(all_pages):
        ap.error(f"쪽 범위가 PDF를 벗어납니다 (총 {len(all_pages)}쪽)")
    page_offset = a.from_page - 1
    pages = all_pages[page_offset:end_page]
    index = page_index(pages, page_offset)
    index_path = out / "page_heads.md"
    index_path.write_text(index, encoding="utf-8")
    text_pages = sum(bool(p.strip()) for p in pages)
    print(f"PDF {len(pages)}쪽 · 글자 있는 쪽 {text_pages}/{len(pages)} · 색인 {index_path}")
    if a.inspect_only:
        return 0
    try:
        lesson_map = unit_lesson_map(a.subject, a.unit, a.lesson_list_json)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        ap.error(f"진도표 차시 목록을 읽을 수 없습니다: {exc}")
    if lesson_map is None and not a.inspect_only:
        ap.error("진도표 차시 목록이 없어 Gemini 분석을 시작하지 않습니다. units/<과목>__<단원>.json을 만들거나 "
                 "--lesson-list-json을 지정하세요.")
    prompt = PROMPT
    if lesson_map is not None:
        prompt += "\n\n아래는 진도표의 정확한 차시 목록입니다. 각 항목에 해당하는 시작 쪽(start_page)과 " \
                  "그 쪽에 실제 적힌 제목(source_title)만 찾아 같은 순서로 반환하세요. 목록에 없는 차시를 만들지 마세요.\n" \
                  + json.dumps({"lessons": lesson_map}, ensure_ascii=False)
        if any("단원 도입" in row["title"] for row in lesson_map):
            prompt += "\n목록에 '단원 도입' 차시가 있으므로 그 쪽은 첫 lesson으로 처리하고 overview는 null로 두세요."
        if a.expected_lessons is not None and a.expected_lessons != len(lesson_map):
            ap.error("--expected-lessons 값과 --lesson-list-json의 행 수가 다릅니다.")
    report_path = out / "analysis.json"
    if a.reuse_analysis:
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))["analysis"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            ap.error(f"기존 analysis.json을 읽을 수 없습니다: {exc}")
    else:
        answer, gemini_model = nlm.gemini_ask(index_path, prompt, model=a.model, timeout=a.timeout,
                                              model_timeout=45, work=out / "gemini_work")
        data = json_object(answer)
    merge_lesson_map(data, lesson_map)
    expected_count = len(lesson_map) if lesson_map is not None else a.expected_lessons
    issues = validate(data, pages, expected_count, page_offset, lesson_map)
    report = {"source_pdf": str(pdf), "subject": a.subject, "unit": a.unit,
              "page_range": [a.from_page, end_page],
              "page_count": len(pages), "text_page_count": text_pages,
              "analysis": data, "validation_issues": issues, "gemini_model": gemini_model}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"분석 결과: {report_path}")
    if issues:
        for issue in issues:
            print(f"검토 필요: {issue}")
        print("검증에 걸려 수업 비서 소스는 만들지 않았습니다. page_heads.md와 analysis.json을 확인하세요.")
        return 2
    source = out / f"{assistant.safe_name(a.unit)}.md"
    source.write_text(make_markdown(a.subject, a.unit, data, pages, page_offset), encoding="utf-8")
    print(f"차시 소스 {len(data['lessons'])}개 생성: {source}")
    if a.publish_to_assistant:
        target_dir = assistant.NOTEBOOKLM / assistant.safe_name(a.subject)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{assistant.safe_name(a.unit)}.md"
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"수업 비서 연결 소스 저장: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
