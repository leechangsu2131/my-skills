#!/usr/bin/env python3
"""
answer_key_parser.py - 답안지(정답지) PDF를 파싱하여 정답 데이터를 추출합니다.

Gemini CLI를 사용한 PDF OCR 또는 수동 JSON 입력을 지원합니다.
"""

import json
import sys
from pathlib import Path
from typing import Optional

from ocr_extractor import load_config, load_prompt, run_gemini_ocr, extract_json_from_response

SKILL_DIR = Path(__file__).parent
ANSWER_KEY_PROMPT = SKILL_DIR / "prompts" / "ocr_answer_key.txt"


def parse_answer_key_pdf(pdf_path: str, prompt_path: Optional[str] = None) -> dict:
    """답안지 PDF에서 정답 데이터를 추출합니다.

    Args:
        pdf_path: 답안지 PDF 경로
        prompt_path: 커스텀 프롬프트 경로

    Returns:
        정답 딕셔너리 (answer_key schema)
    """
    config = load_config()
    prompt = load_prompt(Path(prompt_path) if prompt_path else ANSWER_KEY_PROMPT)
    result = run_gemini_ocr(pdf_path, prompt, config)

    # 후처리: total_points 계산
    if "questions" in result:
        total = sum(q.get("points", 0) for q in result["questions"])
        if total > 0:
            result["total_points"] = total

    return result


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

    return data


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
