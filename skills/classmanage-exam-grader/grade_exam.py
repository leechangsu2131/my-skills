#!/usr/bin/env python3
"""
grade_exam.py - 시험 채점 자동화 파이프라인 오케스트레이터.

전체 파이프라인:
  1. OCR  — Gemini CLI로 학생 시험지 PDF → 답안 JSON 추출
  2. 답안지 — 답안지 PDF → 정답 JSON 추출
  3. 채점  — 학생 답안 vs 정답 비교
  4. 분석  — 외부 LLM 분석 병합 (선택)
  5. PDF  — 원본 시험지에 결과 기입

사용법:
  # 전체 파이프라인
  python grade_exam.py all --students ./pdfs/ --answer-key ./answer.pdf

  # 단계별 실행
  python grade_exam.py ocr --students ./pdfs/
  python grade_exam.py parse-key --answer-key ./answer.pdf
  python grade_exam.py grade
  python grade_exam.py annotate --students ./pdfs/

  # 외부 분석 포함
  python grade_exam.py all --students ./pdfs/ --answer-key ./answer.pdf --analysis ./analysis.json
"""

import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent
sys.path.insert(0, str(SKILL_DIR))

from packages.answer_key_extraction.service import create_answer_key_interactive
from packages.answer_key_extraction.service import load_answer_key_json
from packages.answer_key_extraction.service import parse_answer_key_pdf
from packages.answer_key_extraction.service import save_answer_key
from packages.annotation.service import annotate_batch
from packages.export.service import generate_dashboard
from packages.grading.service import grade_batch
from packages.grading.service import grade_student
from packages.grading.service import grade_subjective_batch
from packages.grading.service import load_config
from packages.grading.service import merge_batch as merge_analysis_batch
from packages.student_extraction.service import extract_answers
from packages.student_extraction.service import extract_batch as ocr_batch


def resolve_paths(config: dict) -> dict:
    """상대 경로를 절대 경로로 변환합니다."""
    paths = {}
    for key, rel in config.get("paths", {}).items():
        paths[key] = str(SKILL_DIR / rel)
    return paths


def cmd_ocr(args, paths):
    """1단계: 학생 시험지 OCR (빈 시험지 템플릿 + Paddle OCR)"""
    print("\n" + "=" * 50)
    print("📸 1단계: 학생 시험지 OCR")
    print("=" * 50)

    blank_exam = getattr(args, "blank_exam", None)
    if not blank_exam:
        print("❌ --blank-exam 으로 빈 시험지 PDF 경로를 지정하세요.")
        return None

    students_dir = args.students or paths["input_students"]
    output_dir = args.extracted or paths["extracted"]

    offset = getattr(args, "student_page_offset", None)
    no_auto = getattr(args, "no_auto_page_window", False)

    results = ocr_batch(
        students_dir,
        output_dir,
        blank_exam_path=blank_exam,
        student_page_offset=offset,
        auto_pick_student_pages=False if no_auto else None,
    )
    return results


def cmd_parse_key(args, paths):
    """2단계: 답안지 파싱"""
    print("\n" + "=" * 50)
    print("📋 2단계: 답안지 파싱")
    print("=" * 50)

    output = str(Path(paths["extracted"]) / "answer_key.json")

    if args.interactive:
        data = create_answer_key_interactive()
    elif args.answer_key:
        source = Path(args.answer_key)
        if source.suffix.lower() == ".json":
            print(f"📂 JSON 답안지 로드: {source.name}")
            data = load_answer_key_json(str(source))
        elif source.suffix.lower() == ".pdf":
            print(f"🔍 답안지 PDF OCR: {source.name}")
            data = parse_answer_key_pdf(str(source))
        else:
            print(f"❌ 지원하지 않는 형식: {source.suffix}")
            return None
    else:
        print("❌ --answer-key 또는 --interactive 를 지정하세요.")
        return None

    saved = save_answer_key(data, output)
    print(f"✅ 답안지 저장: {saved}")
    print(f"   문제 수: {len(data.get('questions', []))}개, 총점: {data.get('total_points')}점")
    return data


def cmd_grade(args, paths):
    """3단계: 채점"""
    print("\n" + "=" * 50)
    print("⚖️ 3단계: 채점")
    print("=" * 50)

    extracted_dir = args.extracted or paths["extracted"]
    answer_key_path = str(Path(extracted_dir) / "answer_key.json")
    graded_dir = args.graded or paths["graded"]

    if not Path(answer_key_path).exists():
        # --answer-key 로 직접 지정한 경우
        if args.answer_key and Path(args.answer_key).exists():
            answer_key_path = args.answer_key
        else:
            print(f"❌ 답안지를 찾을 수 없습니다: {answer_key_path}")
            print("   먼저 parse-key 단계를 실행하거나 --answer-key를 지정하세요.")
            return None

    results = grade_batch(extracted_dir, answer_key_path, graded_dir)
    return results


def cmd_grade_subj(args, paths):
    """3.5단계: 주관식 AI 채점"""
    print("\n" + "=" * 50)
    print("🤖 3.5단계: 주관식/검토 대기 문항 AI 자동 채점")
    print("=" * 50)
    
    graded_dir = args.graded or paths["graded"]
    config = load_config()
    grade_subjective_batch(graded_dir, config)
    # 딕셔너리 리스트 반환이 필요없으므로 생략가능. 또는 재로딩 처리.
    return True

def cmd_merge(args, paths):
    """4단계: 분석 병합"""
    print("\n" + "=" * 50)
    print("🔗 4단계: 분석 병합")
    print("=" * 50)

    graded_dir = args.graded or paths["graded"]
    analysis = getattr(args, "analysis", None)

    results = merge_analysis_batch(graded_dir, analysis)
    return results


def cmd_annotate(args, paths):
    """5단계: PDF 어노테이션"""
    print("\n" + "=" * 50)
    print("✏️ 5단계: PDF 채점 결과 기입")
    print("=" * 50)

    students_dir = args.students or paths["input_students"]
    graded_dir = args.graded or paths["graded"]
    output_dir = args.output or paths["output"]

    results = annotate_batch(students_dir, graded_dir, output_dir)
    return results


def cmd_dashboard(args, paths):
    """6단계: HTML 대시보드 생성"""
    print("\n" + "=" * 50)
    print("📈 6단계: HTML 채점 대시보드 생성")
    print("=" * 50)

    graded_dir = args.graded or paths["graded"]
    output_dir = args.output or paths["output"]

    generate_dashboard(graded_dir, output_dir)
    return True


def cmd_all(args, paths):
    """전체 파이프라인 실행"""
    print("\n" + "🚀" * 25)
    print("  시험 채점 자동화 파이프라인 시작")
    print("🚀" * 25)

    if not getattr(args, "blank_exam", None):
        print("❌ 전체 파이프라인에는 --blank-exam (빈 시험지 PDF)이 필요합니다.")
        return

    # 1단계: OCR
    ocr_results = cmd_ocr(args, paths)
    if not ocr_results:
        print("\n❌ OCR 실패 — 중단합니다.")
        return

    # 2단계: 답안지 파싱
    key_result = cmd_parse_key(args, paths)
    if not key_result:
        print("\n❌ 답안지 파싱 실패 — 중단합니다.")
        return

    # 3단계: 채점
    grade_results = cmd_grade(args, paths)
    if not grade_results:
        print("\n❌ 채점 실패 — 중단합니다.")
        return

    # 3.5단계: 주관식 AI 채점 (선택적일 수도 있지만 all에서는 기본 실행)
    cmd_grade_subj(args, paths)

    # 4단계: 분석 병합
    cmd_merge(args, paths)

    # 5단계: PDF 어노테이션
    annotate_results = cmd_annotate(args, paths)
    
    # 6단계: HTML 대시보드 생성
    cmd_dashboard(args, paths)

    # ===== 최종 요약 =====
    print("\n" + "=" * 50)
    print("🎉 전체 파이프라인 완료!")
    print("=" * 50)

    total = len(grade_results)
    avg_score = sum(r["total_score"] for r in grade_results) / total if total else 0
    avg_accuracy = sum(r["accuracy"] for r in grade_results) / total if total else 0
    total_points = grade_results[0]["total_points"] if grade_results else 0

    print(f"\n📊 채점 요약")
    print(f"   학생 수: {total}명")
    print(f"   평균 점수: {avg_score:.1f} / {total_points}")
    print(f"   평균 정답률: {avg_accuracy:.1f}%")

    # 성적 분포
    if grade_results:
        scores = sorted([r["total_score"] for r in grade_results])
        print(f"   최고점: {scores[-1]}")
        print(f"   최저점: {scores[0]}")
        print(f"   중앙값: {scores[len(scores)//2]}")

    output_dir = args.output or paths["output"]
    print(f"\n📁 채점 완료 PDF: {output_dir}")

    # 결과를 JSON으로도 저장
    summary = {
        "total_students": total,
        "average_score": round(avg_score, 1),
        "average_accuracy": round(avg_accuracy, 1),
        "max_score": max(r["total_score"] for r in grade_results) if grade_results else 0,
        "min_score": min(r["total_score"] for r in grade_results) if grade_results else 0,
        "results": [
            {
                "name": r["student_name"],
                "number": r.get("student_number"),
                "score": r["total_score"],
                "total": r["total_points"],
                "accuracy": r["accuracy"],
            }
            for r in grade_results
        ],
    }
    summary_path = Path(output_dir) / "_grading_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"📋 전체 요약: {summary_path}")


def main():
    parser = argparse.ArgumentParser(
        description="시험 채점 자동화 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 전체 파이프라인 (원클릭)
  python grade_exam.py all --blank-exam ./blank.pdf --students ./pdfs/ --answer-key ./answer.pdf

  # 단계별
  python grade_exam.py ocr --blank-exam ./blank.pdf --students ./pdfs/
  python grade_exam.py parse-key --answer-key ./answer.pdf
  python grade_exam.py grade
  python grade_exam.py grade-subj
  python grade_exam.py merge --analysis ./analysis.json
  python grade_exam.py annotate --students ./pdfs/
  python grade_exam.py dashboard

  # 대화형 답안지 입력
  python grade_exam.py parse-key --interactive
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="실행할 단계")

    # all
    p_all = subparsers.add_parser("all", help="전체 파이프라인")
    p_all.add_argument("--blank-exam", "-b", type=str, help="빈 시험지 PDF (문항 좌표·정렬 기준)")
    p_all.add_argument("--students", "-s", type=str, help="학생 시험지 PDF 폴더")
    p_all.add_argument("--answer-key", "-k", type=str, help="답안지 (PDF 또는 JSON)")
    p_all.add_argument("--analysis", "-a", type=str, help="외부 분석 JSON (선택)")
    p_all.add_argument("--output", "-o", type=str, help="결과 PDF 저장 폴더")
    p_all.add_argument("--interactive", "-i", action="store_true", help="대화형 답안지 입력")
    p_all.add_argument("--extracted", type=str, help="OCR 결과 폴더")
    p_all.add_argument("--graded", type=str, help="채점 결과 폴더")
    p_all.add_argument(
        "--student-page-offset",
        type=int,
        default=None,
        help="학생 PDF에서 시험 첫 페이지의 0부터 시작하는 인덱스 (여분 페이지가 앞에 있을 때)",
    )
    p_all.add_argument(
        "--no-auto-page-window",
        action="store_true",
        help="학생 PDF가 더 길 때 자동 구간 탐색 끄기 (수동 offset과 함께 사용)",
    )

    # ocr
    p_ocr = subparsers.add_parser("ocr", help="1단계: 학생 시험지 OCR")
    p_ocr.add_argument("--blank-exam", "-b", type=str, required=True, help="빈 시험지 PDF")
    p_ocr.add_argument("--students", "-s", type=str, help="학생 시험지 PDF 폴더")
    p_ocr.add_argument("--extracted", type=str, help="결과 저장 폴더")
    p_ocr.add_argument("--student-page-offset", type=int, default=None, help="시험 시작 페이지 인덱스 (0부터)")
    p_ocr.add_argument(
        "--no-auto-page-window",
        action="store_true",
        help="자동 페이지 구간 탐색 끄기",
    )

    # parse-key
    p_key = subparsers.add_parser("parse-key", help="2단계: 답안지 파싱")
    p_key.add_argument("--answer-key", "-k", type=str, help="답안지 (PDF 또는 JSON)")
    p_key.add_argument("--interactive", "-i", action="store_true", help="대화형 입력")
    p_key.add_argument("--extracted", type=str, help="결과 저장 폴더")

    # grade
    p_grade = subparsers.add_parser("grade", help="3단계: 채점")
    p_grade.add_argument("--extracted", type=str, help="OCR 결과 폴더")
    p_grade.add_argument("--answer-key", "-k", type=str, help="답안지 JSON 직접 지정")
    p_grade.add_argument("--graded", type=str, help="채점 결과 저장 폴더")

    # grade-subj
    p_subj = subparsers.add_parser("grade-subj", help="3.5단계: 주관식 자동 채점")
    p_subj.add_argument("--graded", type=str, help="채점 결과 폴더")

    # merge
    p_merge = subparsers.add_parser("merge", help="4단계: 분석 병합")
    p_merge.add_argument("--graded", type=str, help="채점 결과 폴더")
    p_merge.add_argument("--analysis", "-a", type=str, help="외부 분석 JSON")

    # annotate
    p_anno = subparsers.add_parser("annotate", help="5단계: PDF 어노테이션")
    p_anno.add_argument("--students", "-s", type=str, help="원본 학생 PDF 폴더")
    p_anno.add_argument("--graded", type=str, help="채점 결과 폴더")
    p_anno.add_argument("--output", "-o", type=str, help="결과 PDF 저장 폴더")

    # dashboard
    p_dash = subparsers.add_parser("dashboard", help="6단계: HTML 대시보드 생성")
    p_dash.add_argument("--graded", type=str, help="채점 결과 폴더")
    p_dash.add_argument("--output", "-o", type=str, help="결과물 저장 폴더")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    config = load_config()
    paths = resolve_paths(config)

    command_map = {
        "all": cmd_all,
        "ocr": cmd_ocr,
        "parse-key": cmd_parse_key,
        "grade": cmd_grade,
        "grade-subj": cmd_grade_subj,
        "merge": cmd_merge,
        "annotate": cmd_annotate,
        "dashboard": cmd_dashboard,
    }

    handler = command_map.get(args.command)
    if handler:
        handler(args, paths)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
