#!/usr/bin/env python3
"""
analysis_merger.py - 외부 LLM 분석 파일을 채점 결과에 병합합니다.

외부 LLM(예: Claude, GPT 등)이 분석한 오답 분석 텍스트를
채점 결과의 각 문제에 추가합니다.
분석 파일이 없으면 기본 맞음/틀림 표시만 유지합니다.
"""

import json
from pathlib import Path
from typing import Optional


def load_analysis(analysis_path: str) -> dict:
    """외부 분석 파일을 로드합니다.

    Args:
        analysis_path: 분석 JSON 파일 경로

    Returns:
        분석 데이터 딕셔너리 (analysis schema)
    """
    with open(analysis_path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_analysis(grading_result: dict, analysis_data: Optional[dict] = None) -> dict:
    """채점 결과에 분석 데이터를 병합합니다.

    Args:
        grading_result: 채점 결과 (grading_result schema)
        analysis_data: 외부 분석 데이터 (없으면 기본 표시)

    Returns:
        분석이 병합된 채점 결과
    """
    result = grading_result.copy()
    result["details"] = [d.copy() for d in grading_result["details"]]

    if analysis_data is None:
        # 분석 파일 없음 → 기본 오답 메시지
        for detail in result["details"]:
            if detail["correct"] is False:
                detail["analysis"] = (
                    f"학생 답: {detail['student_answer'] or '(미응답)'}, "
                    f"정답: {detail['correct_answer']}"
                )
            elif detail["correct"] is None:
                detail["analysis"] = "서술형 문제 — 수동 채점 필요"
        return result

    # 분석 데이터를 문제번호별로 매핑
    analysis_map = {
        a["q_num"]: a for a in analysis_data.get("analyses", [])
    }

    analyst = analysis_data.get("analyst", "외부 LLM")

    for detail in result["details"]:
        q_num = detail["q_num"]
        if q_num in analysis_map:
            analysis_entry = analysis_map[q_num]
            parts = []

            # 분석 텍스트
            if analysis_entry.get("analysis"):
                parts.append(analysis_entry["analysis"])

            # 오류 유형
            if analysis_entry.get("category"):
                parts.append(f"[{analysis_entry['category']}]")

            # 개선 제안
            if analysis_entry.get("suggestion"):
                parts.append(f"💡 {analysis_entry['suggestion']}")

            detail["analysis"] = " | ".join(parts) if parts else None
        elif detail["correct"] is False:
            # 분석 데이터에 없는 오답 → 기본 메시지
            detail["analysis"] = (
                f"학생 답: {detail['student_answer'] or '(미응답)'}, "
                f"정답: {detail['correct_answer']}"
            )
        elif detail["correct"] is None:
            detail["analysis"] = "서술형 문제 — 수동 채점 필요"

    return result


def merge_batch(graded_dir: str, analysis_path: Optional[str] = None,
                output_dir: Optional[str] = None) -> list[dict]:
    """폴더 내 모든 채점 결과에 분석을 병합합니다.

    Args:
        graded_dir: 채점 결과 JSON 폴더
        analysis_path: 분석 파일 경로 (없으면 기본 표시)
        output_dir: 저장 폴더 (없으면 graded_dir에 덮어쓰기)

    Returns:
        병합된 결과 리스트
    """
    graded_path = Path(graded_dir)
    output_path = Path(output_dir) if output_dir else graded_path
    output_path.mkdir(parents=True, exist_ok=True)

    # 분석 데이터 로드
    analysis_data = None
    if analysis_path:
        analysis_data = load_analysis(analysis_path)
        print(f"📝 분석 파일 로드: {Path(analysis_path).name}")
        print(f"   분석가: {analysis_data.get('analyst', '미상')}")
        print(f"   분석 수: {len(analysis_data.get('analyses', []))}건")
    else:
        print("ℹ️ 분석 파일 없음 → 기본 오답 표시 모드")

    graded_files = sorted(graded_path.glob("*_graded.json"))
    if not graded_files:
        print(f"⚠️ 채점 결과 파일이 없습니다: {graded_dir}")
        return []

    results = []
    for gf in graded_files:
        with open(gf, "r", encoding="utf-8") as f:
            grading_result = json.load(f)

        merged = merge_analysis(grading_result, analysis_data)

        out_file = output_path / gf.name
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

        student = merged.get("student_name", gf.stem)
        wrong_with_analysis = sum(
            1 for d in merged["details"]
            if d["correct"] is False and d.get("analysis")
        )
        print(f"  ✅ {student}: 오답 분석 {wrong_with_analysis}건 병합")
        results.append(merged)

    return results


# ----- CLI 진입점 -----

def main():
    import argparse

    parser = argparse.ArgumentParser(description="외부 LLM 분석 병합")
    parser.add_argument("--graded", type=str, required=True, help="채점 결과 폴더")
    parser.add_argument("--analysis", "-a", type=str, help="외부 분석 JSON 파일")
    parser.add_argument("--output", "-o", type=str, help="결과 저장 폴더")
    args = parser.parse_args()

    results = merge_batch(args.graded, args.analysis, args.output)
    print(f"\n📊 {len(results)}명 분석 병합 완료")


if __name__ == "__main__":
    main()
