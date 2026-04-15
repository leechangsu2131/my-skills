#!/usr/bin/env python3
"""
pdf_annotator.py - 원본 학생 시험지 PDF에 채점 결과를 기입합니다.

PyMuPDF(fitz)를 사용하여:
1. 마지막에 성적표 페이지를 추가
2. 문제별 O/X 마크, 총점, 정답률, 오답 분석 표시
"""

import json
from pathlib import Path
from typing import Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    print("❌ PyMuPDF가 설치되어 있지 않습니다: pip install PyMuPDF")
    raise

SKILL_DIR = Path(__file__).parent


def load_config() -> dict:
    with open(SKILL_DIR / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def _color(rgb_list: list) -> tuple:
    """[r, g, b] 리스트를 fitz 호환 튜플로 변환"""
    return tuple(rgb_list)


def create_summary_page(doc: fitz.Document, grading_result: dict, config: dict) -> None:
    """채점 결과 요약 페이지를 PDF에 추가합니다."""
    ann_config = config.get("annotation", {})

    # A4 크기 새 페이지 추가
    page = doc.new_page(width=595, height=842)  # A4 in points

    correct_color = _color(ann_config.get("correct_color", [0, 0.6, 0]))
    wrong_color = _color(ann_config.get("wrong_color", [0.8, 0, 0]))
    info_color = _color(ann_config.get("info_color", [0, 0, 0.6]))
    black = (0, 0, 0)
    gray = (0.4, 0.4, 0.4)

    title_size = ann_config.get("title_font_size", 16)
    summary_size = ann_config.get("summary_font_size", 12)
    body_size = ann_config.get("font_size", 10)
    font = "helv"  # Helvetica (한글은 fitz 내장 지원 범위에 따라)

    correct_mark = ann_config.get("correct_mark", "O")
    wrong_mark = ann_config.get("wrong_mark", "X")
    review_mark = ann_config.get("needs_review_mark", "?")

    y = 40  # 시작 Y 좌표
    left_margin = 40
    right_margin = 555

    # ===== 제목 =====
    page.insert_text(
        fitz.Point(left_margin, y),
        "채점 결과표",
        fontname=font, fontsize=title_size, color=info_color,
    )
    y += 30

    # 구분선
    page.draw_line(fitz.Point(left_margin, y), fitz.Point(right_margin, y),
                   color=info_color, width=1.5)
    y += 20

    # ===== 학생 정보 =====
    student = grading_result.get("student_name", "Unknown")
    number = grading_result.get("student_number", "")
    exam = grading_result.get("exam_title", "")
    score = grading_result.get("total_score", 0)
    total = grading_result.get("total_points", 0)
    correct_cnt = grading_result.get("correct_count", 0)
    wrong_cnt = grading_result.get("wrong_count", 0)
    review_cnt = grading_result.get("review_count", 0)
    accuracy = grading_result.get("accuracy", 0)

    info_lines = [
        f"학생: {student}" + (f" ({number}번)" if number else ""),
        f"시험: {exam}" if exam else "",
        f"총점: {score} / {total}",
        f"정답: {correct_cnt}개 | 오답: {wrong_cnt}개" +
        (f" | 검토: {review_cnt}개" if review_cnt else ""),
        f"정답률: {accuracy}%",
    ]

    for line in info_lines:
        if not line:
            continue
        page.insert_text(
            fitz.Point(left_margin, y),
            line,
            fontname=font, fontsize=summary_size, color=black,
        )
        y += 18

    y += 10

    # 구분선
    page.draw_line(fitz.Point(left_margin, y), fitz.Point(right_margin, y),
                   color=gray, width=0.5)
    y += 15

    # ===== 문제별 결과 테이블 헤더 =====
    col_x = {
        "num": left_margin,
        "result": left_margin + 40,
        "student": left_margin + 80,
        "correct": left_margin + 200,
        "points": left_margin + 320,
    }

    headers = [
        (col_x["num"], "번호"),
        (col_x["result"], "결과"),
        (col_x["student"], "학생 답"),
        (col_x["correct"], "정답"),
        (col_x["points"], "배점"),
    ]

    for x, text in headers:
        page.insert_text(
            fitz.Point(x, y),
            text,
            fontname=font, fontsize=body_size, color=info_color,
        )
    y += 5

    page.draw_line(fitz.Point(left_margin, y), fitz.Point(right_margin, y),
                   color=gray, width=0.3)
    y += 12

    # ===== 문제별 결과 =====
    details = grading_result.get("details", [])

    for detail in details:
        # 페이지 넘침 체크 — 새 페이지 필요 시
        if y > 780:
            page = doc.new_page(width=595, height=842)
            y = 40
            page.insert_text(
                fitz.Point(left_margin, y),
                "채점 결과표 (계속)",
                fontname=font, fontsize=title_size - 2, color=info_color,
            )
            y += 25
            for x, text in headers:
                page.insert_text(
                    fitz.Point(x, y), text,
                    fontname=font, fontsize=body_size, color=info_color,
                )
            y += 5
            page.draw_line(fitz.Point(left_margin, y), fitz.Point(right_margin, y),
                           color=gray, width=0.3)
            y += 12

        q_num = detail["q_num"]
        is_correct = detail["correct"]

        if is_correct is True:
            mark = correct_mark
            mark_color = correct_color
        elif is_correct is False:
            mark = wrong_mark
            mark_color = wrong_color
        else:
            mark = review_mark
            mark_color = gray

        student_ans = str(detail.get("student_answer", ""))[:20]
        correct_ans = str(detail.get("correct_answer", ""))[:20]
        pts = f"{detail.get('points_earned', 0)}/{detail.get('points_possible', 0)}"

        # 번호
        page.insert_text(fitz.Point(col_x["num"], y), str(q_num),
                         fontname=font, fontsize=body_size, color=black)
        # 결과 마크
        page.insert_text(fitz.Point(col_x["result"], y), mark,
                         fontname=font, fontsize=body_size + 2, color=mark_color)
        # 학생 답
        page.insert_text(fitz.Point(col_x["student"], y),
                         student_ans or "(미응답)",
                         fontname=font, fontsize=body_size, color=black)
        # 정답
        page.insert_text(fitz.Point(col_x["correct"], y), correct_ans,
                         fontname=font, fontsize=body_size, color=black)
        # 배점
        page.insert_text(fitz.Point(col_x["points"], y), pts,
                         fontname=font, fontsize=body_size, color=black)

        y += 14

        # 오답 분석이 있으면 표시
        analysis = detail.get("analysis")
        if analysis and is_correct is not True:
            # 분석 텍스트를 들여쓰기하여 표시
            analysis_text = f"  → {analysis}"
            # 긴 텍스트 줄바꿈 처리
            max_chars = 70
            while len(analysis_text) > max_chars:
                page.insert_text(
                    fitz.Point(col_x["result"], y),
                    analysis_text[:max_chars],
                    fontname=font, fontsize=body_size - 1, color=gray,
                )
                analysis_text = "    " + analysis_text[max_chars:]
                y += 12
                if y > 780:
                    page = doc.new_page(width=595, height=842)
                    y = 40

            page.insert_text(
                fitz.Point(col_x["result"], y),
                analysis_text,
                fontname=font, fontsize=body_size - 1, color=gray,
            )
            y += 14

    # ===== 하단 생성 정보 =====
    y = max(y + 20, 800)
    if y > 830:
        y = 820
    page.insert_text(
        fitz.Point(left_margin, y),
        "Generated by Exam Grader (Gemini CLI)",
        fontname=font, fontsize=7, color=gray,
    )


def stamp_first_page(page: fitz.Page, grading_result: dict, config: dict) -> None:
    """첫 페이지 우측 상단에 채점 결과(점수) 도장을 찍습니다."""
    ann_config = config.get("annotation", {})
    score = grading_result.get("total_score", 0)
    total = grading_result.get("total_points", 0)
    
    # 만점이면 초록색, 아니면 빨간색 계열
    color = _color(ann_config.get("wrong_color", [0.8, 0, 0]))
    if score == total and total > 0:
        color = _color(ann_config.get("info_color", [0, 0, 0.6]))
        
    font = "helv"
    
    # 우측 상단 50px 위치에 표시
    rect = page.rect
    x = rect.width - 140
    y = 50
    if x < 10:
        x = 10
        
    # 박스 테두리 그리기 및 배경색은 생략하고 텍스트만 큼직하게
    text_score = f"{score} / {total}"
    page.insert_text(
        fitz.Point(x, y), text_score,
        fontname=font, fontsize=24, color=color,
    )
    
    # 정답/오답 개수 요약
    correct = grading_result.get("correct_count", 0)
    wrong = grading_result.get("wrong_count", 0)
    review = grading_result.get("review_count", 0)
    
    y += 20
    summary_text = f"O: {correct}  X: {wrong}"
    if review > 0:
        summary_text += f"  ?: {review}"
        
    page.insert_text(
        fitz.Point(x, y), summary_text,
        fontname=font, fontsize=12, color=color,
    )


def annotate_pdf(student_pdf_path: str, grading_result: dict,
                 output_path: str, config: Optional[dict] = None) -> Path:
    """원본 학생 시험지 PDF에 채점 결과를 추가합니다.

    Args:
        student_pdf_path: 원본 학생 시험지 PDF
        grading_result: 채점 결과 (grading_result schema, 분석 포함)
        output_path: 결과 PDF 저장 경로
        config: 설정 (없으면 config.json 로드)

    Returns:
        저장된 PDF 경로
    """
    if config is None:
        config = load_config()

    doc = fitz.open(student_pdf_path)

    # 1. 첫 페이지에 큰 점수 도장 찍기
    if len(doc) > 0:
        stamp_first_page(doc[0], grading_result, config)

    # 2. 성적표 요약 페이지 추가
    if config.get("annotation", {}).get("add_summary_page", True):
        create_summary_page(doc, grading_result, config)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    doc.close()

    return out


def annotate_batch(student_pdf_dir: str, graded_dir: str,
                   output_dir: str, config: Optional[dict] = None) -> list[dict]:
    """폴더 내 모든 학생의 시험지를 배치 어노테이션합니다.

    학생 PDF 파일명과 채점 결과 파일명을 매칭하여 처리합니다.
    매칭 규칙: {name}.pdf ↔ {name}_graded.json

    Args:
        student_pdf_dir: 원본 학생 시험지 PDF 폴더
        graded_dir: 채점 결과 JSON 폴더
        output_dir: 채점 완료 PDF 저장 폴더

    Returns:
        처리 결과 리스트
    """
    if config is None:
        config = load_config()

    pdf_path = Path(student_pdf_dir)
    graded_path = Path(graded_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(pdf_path.glob("*.pdf"))
    if not pdf_files:
        print(f"⚠️ PDF 파일이 없습니다: {student_pdf_dir}")
        return []

    print(f"\n✏️ {len(pdf_files)}개 PDF 어노테이션 시작...\n")

    results = []
    for pdf_file in pdf_files:
        # 매칭되는 채점 결과 찾기
        graded_file = graded_path / f"{pdf_file.stem}_graded.json"
        if not graded_file.exists():
            # 대체: _answers → _graded 패턴 시도
            alt_graded = graded_path / f"{pdf_file.stem}_answers_graded.json"
            if alt_graded.exists():
                graded_file = alt_graded
            else:
                print(f"  ⚠️ {pdf_file.name}: 채점 결과 없음 → 건너뜀")
                results.append({"file": pdf_file.name, "status": "skipped", "reason": "no grading result"})
                continue

        with open(graded_file, "r", encoding="utf-8") as f:
            grading_result = json.load(f)

        student_name = grading_result.get("student_name", pdf_file.stem)
        output_filename = f"{pdf_file.stem}_채점완료.pdf"
        output_file = output_path / output_filename

        try:
            annotate_pdf(str(pdf_file), grading_result, str(output_file), config)
            score = grading_result.get("total_score", 0)
            total = grading_result.get("total_points", 0)
            print(f"  ✅ {student_name}: {score}/{total}점 → {output_filename}")
            results.append({
                "file": pdf_file.name,
                "student": student_name,
                "status": "success",
                "output": str(output_file),
                "score": f"{score}/{total}",
            })
        except Exception as e:
            print(f"  ❌ {pdf_file.name}: {e}")
            results.append({"file": pdf_file.name, "status": "error", "error": str(e)})

    success = sum(1 for r in results if r["status"] == "success")
    print(f"\n📊 완료: {success}/{len(results)} 성공")

    return results


# ----- CLI 진입점 -----

def main():
    import argparse

    parser = argparse.ArgumentParser(description="PDF 채점 결과 어노테이션")
    parser.add_argument("--pdf", type=str, help="단일 학생 시험지 PDF")
    parser.add_argument("--graded", type=str, help="단일 채점 결과 JSON")
    parser.add_argument("--batch-pdf", type=str, help="배치: 학생 PDF 폴더")
    parser.add_argument("--batch-graded", type=str, help="배치: 채점 결과 폴더")
    parser.add_argument("--output", "-o", type=str, help="결과 PDF 저장 위치")
    args = parser.parse_args()

    config = load_config()
    default_output = str(SKILL_DIR / config["paths"]["output"])

    if args.batch_pdf and args.batch_graded:
        annotate_batch(args.batch_pdf, args.batch_graded, args.output or default_output, config)
    elif args.pdf and args.graded:
        with open(args.graded, "r", encoding="utf-8") as f:
            grading_result = json.load(f)
        output = args.output or str(
            Path(default_output) / f"{Path(args.pdf).stem}_채점완료.pdf"
        )
        result = annotate_pdf(args.pdf, grading_result, output, config)
        print(f"\n✅ 채점 결과 PDF 생성: {result}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
