#!/usr/bin/env python3
"""
answer_key_parser.py - 답안지(정답지) PDF를 파싱하여 정답 데이터를 추출합니다.

텍스트 추출이 가능한 PDF는 로컬에서 직접 파싱하고, 이미지형 PDF만 Gemini CLI를
예비 경로로 사용합니다.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

import fitz

from ocr_extractor import load_config, load_prompt, run_gemini_ocr

SKILL_DIR = Path(__file__).parent
ANSWER_KEY_PROMPT = SKILL_DIR / "prompts" / "ocr_answer_key.txt"
QUESTION_NUMBER_RE = re.compile(r"^\d{1,3}$")
RUBRIC_BLOCK_RE = re.compile(r"(?ms)^\s*(\d{1,3})\.\s*(.*?)(?=^\s*\d{1,3}\.\s|\Z)")
PRIVATE_USE_RE = re.compile(r"[\ue000-\uf8ff]")
MULTIPLE_CHOICE_CHARS = "①②③④⑤⑥⑦⑧⑨⑩㉠㉡㉢㉣㉤"


def parse_answer_key_pdf(pdf_path: str, prompt_path: Optional[str] = None) -> dict:
    """답안지 PDF에서 정답 데이터를 추출합니다.

    Args:
        pdf_path: 답안지 PDF 경로
        prompt_path: 커스텀 프롬프트 경로

    Returns:
        정답 딕셔너리 (answer_key schema)
    """
    direct_parse = _parse_text_answer_key_pdf(Path(pdf_path))
    if direct_parse is not None:
        return direct_parse

    config = load_config()
    prompt = load_prompt(Path(prompt_path) if prompt_path else ANSWER_KEY_PROMPT)
    result = run_gemini_ocr(pdf_path, prompt, config)
    return _finalize_answer_key(result, default_exam_title=Path(pdf_path).stem)


def _parse_text_answer_key_pdf(pdf_path: Path) -> dict | None:
    page_texts = _extract_pdf_text_pages(pdf_path)
    if not _looks_like_text_answer_key(page_texts):
        return None

    question_rows = _extract_question_rows(page_texts[0])
    if not question_rows:
        return None

    rubrics = _extract_rubric_blocks(page_texts)
    default_points = _infer_default_points(len(question_rows))
    questions = []
    for row in question_rows:
        rubric = rubrics.get(row["q_num"])
        answer, alt_answers, q_type = _normalize_parsed_answer(row["answer"], rubric)
        questions.append(
            {
                "q_num": row["q_num"],
                "type": q_type,
                "answer": answer,
                "alt_answers": alt_answers,
                "points": default_points,
                "rubric": rubric,
            }
        )

    return _finalize_answer_key(
        {
            "exam_title": pdf_path.stem,
            "questions": questions,
        },
        default_exam_title=pdf_path.stem,
    )


def _extract_pdf_text_pages(pdf_path: Path) -> list[str]:
    document = fitz.open(pdf_path)
    try:
        return [page.get_text("text") for page in document]
    finally:
        document.close()


def _looks_like_text_answer_key(page_texts: list[str]) -> bool:
    if not page_texts:
        return False
    first_page = page_texts[0]
    return (
        "번호" in first_page
        and "정답" in first_page
        and ("배점" in first_page or "채점 기준" in first_page)
    )


def _clean_lines(text: str) -> list[str]:
    return [" ".join(raw.split()) for raw in text.splitlines() if " ".join(raw.split())]


def _extract_question_rows(first_page_text: str) -> list[dict[str, str | int]]:
    lines = _clean_lines(first_page_text)
    try:
        current_index = next(index for index, line in enumerate(lines) if line == "1")
    except StopIteration:
        return []

    rows: list[dict[str, str | int]] = []
    while current_index < len(lines):
        line = lines[current_index]
        if _is_table_boundary(line):
            break
        if not QUESTION_NUMBER_RE.fullmatch(line):
            current_index += 1
            continue

        q_num = int(line)
        if rows and q_num != rows[-1]["q_num"] + 1:
            break
        if current_index + 1 >= len(lines):
            break

        rows.append({"q_num": q_num, "answer": lines[current_index + 1]})
        next_index = _find_next_question_index(lines, current_index + 2, q_num + 1)
        if next_index is None:
            break
        current_index = next_index

    return rows


def _find_next_question_index(lines: list[str], start_index: int, next_q_num: int) -> int | None:
    marker = str(next_q_num)
    for index in range(start_index, len(lines)):
        line = lines[index]
        if _is_table_boundary(line):
            return None
        if line == marker:
            return index
    return None


def _is_table_boundary(line: str) -> bool:
    return (
        line.startswith("수학(")
        or bool(re.fullmatch(r"기본\s*\d+회", line))
        or bool(re.match(r"^\d+\.\s*", line))
    )


def _extract_rubric_blocks(page_texts: list[str]) -> dict[int, str]:
    rubrics: dict[int, str] = {}
    joined = "\n".join(page_texts)
    for match in RUBRIC_BLOCK_RE.finditer(joined):
        q_num = int(match.group(1))
        block = re.sub(r"\s+", " ", match.group(2)).strip()
        if "채점 기준" not in block and "배점" not in block:
            continue
        rubrics[q_num] = block
    return rubrics


def _normalize_parsed_answer(raw_answer: str, rubric: str | None) -> tuple[str, list[str], str]:
    answer = " ".join(raw_answer.split()).strip(" ,")
    alt_answers: list[str] = []

    if "해설 참조" in answer:
        alt_answers.append(answer)
        trailing = re.split(r"[,，:]", answer)[-1].strip()
        if trailing and trailing != answer:
            answer = trailing

    numeric_with_unit = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([a-zA-Z가-힣]+)", answer)
    if numeric_with_unit is not None:
        alt_answers.append(numeric_with_unit.group(1))

    q_type = _infer_question_type(raw_answer, rubric)
    deduped_alt_answers = []
    for item in alt_answers:
        cleaned = item.strip()
        if cleaned and cleaned != answer and cleaned not in deduped_alt_answers:
            deduped_alt_answers.append(cleaned)

    return answer or raw_answer.strip(), deduped_alt_answers, q_type


def _infer_question_type(raw_answer: str, rubric: str | None) -> str:
    if rubric or "해설 참조" in raw_answer or PRIVATE_USE_RE.search(raw_answer):
        return "descriptive"
    if any(char in raw_answer for char in MULTIPLE_CHOICE_CHARS):
        return "multiple_choice"
    return "short_answer"


def _infer_default_points(question_count: int) -> float:
    if question_count > 0 and 100 % question_count == 0:
        return float(100 // question_count)
    return 1.0


def _finalize_answer_key(data: dict, *, default_exam_title: str | None = None) -> dict:
    data.setdefault("exam_title", default_exam_title)

    total_points = 0.0
    for question in data.get("questions", []):
        question.setdefault("type", "short_answer")
        question.setdefault("alt_answers", [])
        question.setdefault("rubric", None)
        question.setdefault("points", 0)
        total_points += float(question.get("points", 0) or 0)

    if "total_points" not in data:
        data["total_points"] = int(total_points) if total_points.is_integer() else total_points

    return data


def load_answer_key_json(json_path: str) -> dict:
    """수동으로 작성한 답안지 JSON을 로드합니다.

    Args:
        json_path: 답안지 JSON 파일 경로

    Returns:
        정답 딕셔너리
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 기본값 보정
    if "total_points" not in data:
        data["total_points"] = sum(q.get("points", 0) for q in data.get("questions", []))

    for q in data.get("questions", []):
        q.setdefault("type", "short_answer")
        q.setdefault("alt_answers", [])
        q.setdefault("rubric", None)

    return _finalize_answer_key(data, default_exam_title=Path(json_path).stem)


def create_answer_key_interactive() -> dict:
    """대화형으로 답안지를 입력받습니다."""
    print("\n📝 답안지 수동 입력 모드")
    print("=" * 40)

    exam_title = input("시험 제목: ").strip() or None
    num_questions = int(input("문제 수: "))
    default_points = 100 / num_questions

    questions = []
    for i in range(1, num_questions + 1):
        print(f"\n--- 문제 {i} ---")
        q_type = input(f"  유형 (m=객관식, s=단답형, d=서술형) [s]: ").strip().lower()
        type_map = {"m": "multiple_choice", "s": "short_answer", "d": "descriptive", "": "short_answer"}
        q_type = type_map.get(q_type, "short_answer")

        answer = input(f"  정답: ").strip()

        alt_input = input(f"  대체 정답 (쉼표 구분, 없으면 Enter): ").strip()
        alt_answers = [a.strip() for a in alt_input.split(",") if a.strip()] if alt_input else []

        points_input = input(f"  배점 [{default_points:.1f}]: ").strip()
        points = float(points_input) if points_input else round(default_points, 1)

        rubric = None
        if q_type == "descriptive":
            rubric = input(f"  채점 기준: ").strip() or None

        questions.append({
            "q_num": i,
            "type": q_type,
            "answer": answer,
            "alt_answers": alt_answers,
            "points": points,
            "rubric": rubric,
        })

    total_points = sum(q["points"] for q in questions)

    return {
        "exam_title": exam_title,
        "total_points": total_points,
        "questions": questions,
    }


def save_answer_key(data: dict, output_path: str) -> Path:
    """답안지 데이터를 JSON으로 저장합니다."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return out


# ----- CLI 진입점 -----

def main():
    import argparse

    parser = argparse.ArgumentParser(description="답안지(정답지) 파싱")
    parser.add_argument("source", nargs="?", help="답안지 PDF 또는 JSON 경로")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="대화형 수동 입력 모드")
    parser.add_argument("--output", "-o", type=str,
                        help="결과 저장 경로 (기본: data/extracted/answer_key.json)")
    parser.add_argument("--prompt", type=str, help="커스텀 프롬프트 경로")
    args = parser.parse_args()

    config = load_config()
    default_output = str(SKILL_DIR / config["paths"]["extracted"] / "answer_key.json")

    if args.interactive:
        data = create_answer_key_interactive()
    elif args.source:
        source_path = Path(args.source)
        if source_path.suffix.lower() == ".json":
            print(f"📂 JSON 답안지 로드: {source_path.name}")
            data = load_answer_key_json(str(source_path))
        elif source_path.suffix.lower() == ".pdf":
            print(f"🔍 답안지 PDF OCR: {source_path.name}")
            data = parse_answer_key_pdf(str(source_path), args.prompt)
        else:
            print(f"❌ 지원하지 않는 파일 형식: {source_path.suffix}")
            sys.exit(1)
    else:
        parser.print_help()
        return

    output_path = args.output or default_output
    saved = save_answer_key(data, output_path)
    print(f"\n✅ 답안지 저장: {saved}")
    print(f"   문제 수: {len(data.get('questions', []))}개")
    print(f"   총 배점: {data.get('total_points', '?')}점")
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
