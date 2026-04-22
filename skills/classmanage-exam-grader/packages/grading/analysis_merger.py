#!/usr/bin/env python3
"""Merge external analysis into grading results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def load_analysis(analysis_path: str) -> dict:
    with open(analysis_path, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def merge_analysis(grading_result: dict, analysis_data: Optional[dict] = None) -> dict:
    result = grading_result.copy()
    result["details"] = [detail.copy() for detail in grading_result["details"]]

    if analysis_data is None:
        for detail in result["details"]:
            if detail["correct"] is False:
                detail["analysis"] = (
                    f"학생 답: {detail['student_answer'] or '(미응답)'}, "
                    f"정답: {detail['correct_answer']}"
                )
            elif detail["correct"] is None:
                detail["analysis"] = "서술형 문제 — 수동 채점 필요"
        return result

    analysis_map = {entry["q_num"]: entry for entry in analysis_data.get("analyses", [])}

    for detail in result["details"]:
        q_num = detail["q_num"]
        if q_num in analysis_map:
            analysis_entry = analysis_map[q_num]
            parts = []
            if analysis_entry.get("analysis"):
                parts.append(analysis_entry["analysis"])
            if analysis_entry.get("category"):
                parts.append(f"[{analysis_entry['category']}]")
            if analysis_entry.get("suggestion"):
                parts.append(f"💡 {analysis_entry['suggestion']}")
            detail["analysis"] = " | ".join(parts) if parts else None
        elif detail["correct"] is False:
            detail["analysis"] = (
                f"학생 답: {detail['student_answer'] or '(미응답)'}, "
                f"정답: {detail['correct_answer']}"
            )
        elif detail["correct"] is None:
            detail["analysis"] = "서술형 문제 — 수동 채점 필요"

    return result


def merge_batch(graded_dir: str, analysis_path: Optional[str] = None, output_dir: Optional[str] = None) -> list[dict]:
    graded_path = Path(graded_dir)
    output_path = Path(output_dir) if output_dir else graded_path
    output_path.mkdir(parents=True, exist_ok=True)

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
    for graded_file in graded_files:
        with open(graded_file, "r", encoding="utf-8") as file_obj:
            grading_result = json.load(file_obj)

        merged = merge_analysis(grading_result, analysis_data)

        out_file = output_path / graded_file.name
        with open(out_file, "w", encoding="utf-8") as file_obj:
            json.dump(merged, file_obj, ensure_ascii=False, indent=2)

        student = merged.get("student_name", graded_file.stem)
        wrong_with_analysis = sum(1 for detail in merged["details"] if detail["correct"] is False and detail.get("analysis"))
        print(f"  ✅ {student}: 오답 분석 {wrong_with_analysis}건 병합")
        results.append(merged)

    return results
