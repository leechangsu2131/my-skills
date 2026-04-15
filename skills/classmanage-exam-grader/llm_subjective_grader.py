import json
import subprocess
import copy
from pathlib import Path

SKILL_DIR = Path(__file__).parent

def load_prompt_template() -> str:
    prompt_path = SKILL_DIR / "prompts" / "subjective_grader.txt"
    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Evaluate the subjective answers below and return JSON array."

def call_gemini_subjective_grade(prompt_text: str, student_data: list, config: dict) -> list:
    """Gemini CLI를 호출하여 주관식(또는 null 판정) 문제의 채점을 수행합니다."""
    
    # 1. 프롬프트 구성
    final_prompt = prompt_text + "\n\n## 평가할 데이터:\n"
    final_prompt += json.dumps(student_data, ensure_ascii=False, indent=2)

    model = config.get("gemini_model", "gemini-2.5-flash")

    # 2. Gemini 호출
    import os
    cmd_name = "gemini.cmd" if os.name == "nt" else "gemini"
    
    try:
        result = subprocess.run(
            [cmd_name, "-p", final_prompt, "-m", model],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8"
        )
        output = result.stdout.strip()
        
        # JSON 블록 추출
        if "```json" in output:
            output = output.split("```json")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].split("```")[0].strip()
            
        return json.loads(output)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Gemini 주관식 채점 API 호출 실패: {e.stderr}")
        return []
    except json.JSONDecodeError:
        print("❌ Gemini 반환값이 유효한 JSON이 아닙니다.")
        return []

def grade_subjective_batch(graded_dir: str, config: dict) -> None:
    """채점된 폴더 내 학생들의 주관식(needs_review) 문항들을 모아 Gemini로 자동 채점합니다."""
    graded_path = Path(graded_dir)
    if not graded_path.exists():
        print(f"❌ 채점 폴더가 없습니다: {graded_path}")
        return

    prompt_template = load_prompt_template()

    # 모든 _graded.json 파일을 찾음
    for graded_file in graded_path.glob("*_graded.json"):
        with open(graded_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        student_name = data.get("student_name", "Unknown")
        details = data.get("details", [])

        # 리뷰가 필요한 항목 필터링 (correct == None 이고 배점이 있는 항목)
        review_items = [d for d in details if d.get("correct") is None and d.get("points_possible", 0) > 0]
        
        if not review_items:
            continue

        print(f"⏳ {student_name}: 주관식/검토 대기 문항 {len(review_items)}개 AI 채점 진행 중...")

        # Gemini 요청용 데이터 생성
        request_data = []
        for item in review_items:
            # model_answer, rubric 등이 필요함. 
            # (현재 grader.py가 details에 이것들을 전부 넣어둔 상태임)
            request_data.append({
                "q_num": item["q_num"],
                "max_points": item.get("points_possible", 0),
                "model_answer": item.get("correct_answer", ""),
                "student_answer": item.get("student_answer", ""),
                "rubric": item.get("rubric", ""),
            })

        # Gemini 호출
        ai_grades = call_gemini_subjective_grade(prompt_template, request_data, config)

        if not ai_grades:
            print(f"  ⚠️ {student_name}: AI 채점 실패 또는 반환값 없음")
            continue

        # 결과 맵핑 및 data 갱신
        correct_updated_count = 0
        ai_grades_map = {g["q_num"]: g for g in ai_grades if "q_num" in g}

        for item in details:
            q_num = item["q_num"]
            if item.get("correct") is None and q_num in ai_grades_map:
                grade_info = ai_grades_map[q_num]
                earned = grade_info.get("earned_points", 0)
                # 만약을 대비해 최대 점수 클리핑
                earned = max(0, min(earned, item.get("points_possible", 0)))
                
                item["points_earned"] = earned
                item["correct"] = grade_info.get("correct") # true, false, or null
                
                # 분석/채점 이유로 reason/analysis 업데이트
                reason = grade_info.get("reason", "")
                if reason:
                    item["analysis"] = reason
                
                correct_updated_count += 1

        # 총점 재계산
        total_score = sum(d.get("points_earned", 0) for d in details)
        
        # 정답수/오답수 재계산
        correct_count = sum(1 for d in details if d.get("correct") is True)
        wrong_count = sum(1 for d in details if d.get("correct") is False)
        new_review_count = len(details) - correct_count - wrong_count
        
        # 정확도 재계산
        total_q = len(details)
        accuracy = round((correct_count / total_q) * 100, 1) if total_q > 0 else 0.0

        data["total_score"] = total_score
        data["correct_count"] = correct_count
        data["wrong_count"] = wrong_count
        data["review_count"] = new_review_count
        data["accuracy"] = accuracy

        # 변동사항 덮어쓰기
        with open(graded_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  ✅ {student_name}: 채점 완료 (총점 갱신: {total_score}점, 검토 대기 잔여: {new_review_count}건)")

