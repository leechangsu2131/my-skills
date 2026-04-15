#!/usr/bin/env python3
"""
grader.py - 학생 답안과 정답을 비교하여 채점하는 엔진.

객관식/단답형은 자동 채점, 서술형은 needs_review 플래그 처리.
"""

import json
import re
import unicodedata
from pathlib import Path
from typing import Optional

SKILL_DIR = Path(__file__).parent


def load_config() -> dict:
    with open(SKILL_DIR / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_answer(answer: str, config: dict) -> str:
    """답안을 정규화합니다.

    - 공백 제거 (strip_whitespace)
    - 대소문자 통일 (case_sensitive=false → 소문자)
    - 숫자 정규화 (normalize_numbers → "24 cm" == "24cm")
    - 유니코드 정규화
    """
    text = answer.strip() if config.get("strip_whitespace", True) else answer

    if not config.get("case_sensitive", False):
        text = text.lower()

    # 유니코드 정규화 (전각 → 반각 등)
    text = unicodedata.normalize("NFKC", text)

    if config.get("normalize_numbers", True):
        # 숫자와 단위 사이 공백 제거: "24 cm" → "24cm"
        text = re.sub(r"(\d+)\s+([a-zA-Z가-힣])", r"\1\2", text)
        # 불필요한 소수점 제거: "24.0" → "24"
        text = re.sub(r"\.0+$", "", text)

    return text


def compare_answers(student_answer: str, correct_answer: str,
                    alt_answers: list[str], q_type: str, config: dict) -> Optional[bool]:
    """단일 문제의 답을 비교합니다.

    Returns:
        True (정답), False (오답), None (수동 채점 필요)
    """
    grading_config = config.get("grading", {})

    # 서술형: 자동 채점 비활성화 시 review 표시
    if q_type == "descriptive" and not grading_config.get("descriptive_auto_grade", False):
        return None

    # 답이 비어 있으면 무조건 오답
    if not student_answer.strip():
        return False

    norm_student = normalize_answer(student_answer, grading_config)
    norm_correct = normalize_answer(correct_answer, grading_config)

    # 정답과 직접 비교
    if norm_student == norm_correct:
        return True

    # 대체 정답 비교
    for alt in alt_answers:
        if norm_student == normalize_answer(alt, grading_config):
            return True

    return False


def grade_student(student_answers: dict, answer_key: dict, config: Optional[dict] = None) -> dict:
    """한 학생의 답안을 채점합니다.

    Args:
        student_answers: 학생 답안 데이터 (student_answers schema)
        answer_key: 정답 데이터 (answer_key schema)
        config: 설정 (없으면 config.json에서 로드)

    Returns:
        채점 결과 딕셔너리 (grading_result schema)
    """
    if config is None:
        config = load_config()

    # 학생 답안을 문제번호 기준으로 딕셔너리화
    student_map = {a["q_num"]: a for a in student_answers.get("answers", [])}

    details = []
    total_score = 0
    correct_count = 0
    wrong_count = 0
    review_count = 0

    for question in answer_key.get("questions", []):
        q_num = question["q_num"]
        correct_answer = question["answer"]
        alt_answers = question.get("alt_answers", [])
        points = question.get("points", 0)
        q_type = question.get("type", "short_answer")

        # 학생 답안 찾기
        student_q = student_map.get(q_num, {})
        student_answer = student_q.get("answer", "")

        # 비교
        is_correct = compare_answers(student_answer, correct_answer, alt_answers, q_type, config)

        if is_correct is True:
            points_earned = points
            correct_count += 1
        elif is_correct is False:
            points_earned = 0
            wrong_count += 1
        else:  # None → review
            points_earned = 0
            review_count += 1

        total_score += points_earned

        details.append({
            "q_num": q_num,
            "correct": is_correct,
            "student_answer": student_answer,
            "correct_answer": correct_answer,
            "points_earned": points_earned,
            "points_possible": points,
            "analysis": None,
        })

    total_points = answer_key.get("total_points", sum(q.get("points", 0) for q in answer_key.get("questions", [])))
    graded_count = correct_count + wrong_count
    accuracy = (correct_count / graded_count * 100) if graded_count > 0 else 0

    return {
        "student_name": student_answers.get("student_name", "Unknown"),
        "student_number": student_answers.get("student_number"),
        "exam_title": answer_key.get("exam_title") or student_answers.get("exam_title"),
        "total_score": total_score,
        "total_points": total_points,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "review_count": review_count,
        "accuracy": round(accuracy, 1),
        "details": details,
    }


def grade_batch(extracted_dir: str, answer_key_path: str, output_dir: str) -> list[dict]:
    """폴더 내 모든 추출된 답안을 배치 채점합니다.

    Args:
        extracted_dir: OCR 추출 결과 JSON 폴더
        answer_key_path: 답안지 JSON 경로
        output_dir: 채점 결과 저장 폴더

    Returns:
        채점 결과 리스트
    """
    config = load_config()
    extracted_path = Path(extracted_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 답안지 로드
    with open(answer_key_path, "r", encoding="utf-8") as f:
        answer_key = json.load(f)

    # 학생 답안 파일들 (answer_key.json 제외)
    answer_files = sorted([
        f for f in extracted_path.glob("*_answers.json")
        if f.name != "answer_key.json"
    ])

    if not answer_files:
        print(f"⚠️ 추출된 답안 파일이 없습니다: {extracted_dir}")
        return []

    print(f"\n📊 {len(answer_files)}명 채점 시작...\n")

    results = []
    for i, answer_file in enumerate(answer_files, 1):
        with open(answer_file, "r", encoding="utf-8") as f:
            student_answers = json.load(f)

        student_name = student_answers.get("student_name", answer_file.stem)
        print(f"[{i}/{len(answer_files)}] {student_name}")

        result = grade_student(student_answers, answer_key, config)

        # 결과 저장
        out_file = output_path / f"{answer_file.stem.replace('_answers', '_graded')}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        review_str = f", 검토 {result['review_count']}" if result['review_count'] else ""
        print(f"  ✅ {result['total_score']}/{result['total_points']}점 "
              f"(정답 {result['correct_count']}, 오답 {result['wrong_count']}{review_str})")

        results.append(result)

    # 전체 요약
    avg_score = sum(r["total_score"] for r in results) / len(results) if results else 0
    avg_accuracy = sum(r["accuracy"] for r in results) / len(results) if results else 0
    print(f"\n📋 전체 평균: {avg_score:.1f}점 ({avg_accuracy:.1f}%)")

    return results


# ----- CLI 진입점 -----

def main():
    import argparse

    parser = argparse.ArgumentParser(description="시험 채점 엔진")
    parser.add_argument("--student", type=str, help="단일 학생 답안 JSON")
    parser.add_argument("--answer-key", "-k", type=str, required=True, help="답안지 JSON 경로")
    parser.add_argument("--batch", type=str, help="배치 처리할 폴더 (추출된 답안들)")
    parser.add_argument("--output", "-o", type=str, help="결과 저장 폴더")
    args = parser.parse_args()

    config = load_config()
    default_output = str(SKILL_DIR / config["paths"]["graded"])

    if args.batch:
        results = grade_batch(args.batch, args.answer_key, args.output or default_output)
    elif args.student:
        with open(args.student, "r", encoding="utf-8") as f:
            student_answers = json.load(f)
        with open(args.answer_key, "r", encoding="utf-8") as f:
            answer_key = json.load(f)

        result = grade_student(student_answers, answer_key)
        output_dir = Path(args.output or default_output)
        output_dir.mkdir(parents=True, exist_ok=True)
        out_file = output_dir / f"{Path(args.student).stem.replace('_answers', '_graded')}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 채점 완료: {out_file}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
