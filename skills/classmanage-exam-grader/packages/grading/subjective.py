from __future__ import annotations

import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_prompt_template() -> str:
    prompt_path = PROJECT_ROOT / "prompts" / "subjective_grader.txt"
    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as file_obj:
            return file_obj.read()
    return "Evaluate the subjective answers below and return JSON array."


def call_gemini_subjective_grade(prompt_text: str, student_data: list, config: dict) -> list:
    final_prompt = prompt_text + "\n\n## 평가할 데이터:\n"
    final_prompt += json.dumps(student_data, ensure_ascii=False, indent=2)

    model = config.get("gemini_model", "gemini-2.5-flash")

    import os

    cmd_name = "gemini.cmd" if os.name == "nt" else "gemini"

    try:
        result = subprocess.run(
            [cmd_name, "-p", final_prompt, "-m", model],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        )
        output = result.stdout.strip()

        if "```json" in output:
            output = output.split("```json")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].split("```")[0].strip()

        return json.loads(output)

    except subprocess.CalledProcessError as exc:
        print(f"❌ Gemini 주관식 채점 API 호출 실패: {exc.stderr}")
        return []
    except json.JSONDecodeError:
        print("❌ Gemini 반환값이 유효한 JSON이 아닙니다.")
        return []


def grade_subjective_batch(graded_dir: str, config: dict) -> None:
    graded_path = Path(graded_dir)
    if not graded_path.exists():
        print(f"❌ 채점 폴더가 없습니다: {graded_path}")
        return

    prompt_template = load_prompt_template()

    for graded_file in graded_path.glob("*_graded.json"):
        with open(graded_file, "r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)

        student_name = data.get("student_name", "Unknown")
        details = data.get("details", [])
        review_items = [detail for detail in details if detail.get("correct") is None and detail.get("points_possible", 0) > 0]

        if not review_items:
            continue

        print(f"⏳ {student_name}: 주관식/검토 대기 문항 {len(review_items)}개 AI 채점 진행 중...")

        request_data = []
        for item in review_items:
            request_data.append(
                {
                    "q_num": item["q_num"],
                    "max_points": item.get("points_possible", 0),
                    "model_answer": item.get("correct_answer", ""),
                    "student_answer": item.get("student_answer", ""),
                    "rubric": item.get("rubric", ""),
                }
            )

        ai_grades = call_gemini_subjective_grade(prompt_template, request_data, config)

        if not ai_grades:
            print(f"  ⚠️ {student_name}: AI 채점 실패 또는 반환값 없음")
            continue

        ai_grades_map = {grade["q_num"]: grade for grade in ai_grades if "q_num" in grade}

        for item in details:
            q_num = item["q_num"]
            if item.get("correct") is None and q_num in ai_grades_map:
                grade_info = ai_grades_map[q_num]
                earned = grade_info.get("earned_points", 0)
                earned = max(0, min(earned, item.get("points_possible", 0)))
                item["points_earned"] = earned
                item["correct"] = grade_info.get("correct")

                reason = grade_info.get("reason", "")
                if reason:
                    item["analysis"] = reason

        total_score = sum(detail.get("points_earned", 0) for detail in details)
        correct_count = sum(1 for detail in details if detail.get("correct") is True)
        wrong_count = sum(1 for detail in details if detail.get("correct") is False)
        new_review_count = len(details) - correct_count - wrong_count
        total_questions = len(details)
        accuracy = round((correct_count / total_questions) * 100, 1) if total_questions > 0 else 0.0

        data["total_score"] = total_score
        data["correct_count"] = correct_count
        data["wrong_count"] = wrong_count
        data["review_count"] = new_review_count
        data["accuracy"] = accuracy

        with open(graded_file, "w", encoding="utf-8") as file_obj:
            json.dump(data, file_obj, ensure_ascii=False, indent=2)

        print(f"  ✅ {student_name}: 채점 완료 (총점 갱신: {total_score}점, 검토 대기 잔여: {new_review_count}건)")
