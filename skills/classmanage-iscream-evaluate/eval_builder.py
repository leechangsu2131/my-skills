"""
eval_builder.py — 학생 교과 평가 데이터 구축 모듈

Supabase에서 조회한 기록을 학생별·과목별로 분석하여
i-scream 평가 입력용 데이터를 구성합니다.

사용법:
    모듈로 임포트:
        from eval_builder import build_eval_data_for_iscream, preview_all_students

    단독 실행 (전체 미리보기):
        python eval_builder.py

    특정 학생만 미리보기:
        python eval_builder.py --student 김민준
"""

import argparse
from collections import Counter, defaultdict

from supabase_fetch import (
    fetch_all_records,
    get_records_for_student,
    get_unique_students,
    group_by_subject,
    parse_student_names,
)


# ──────────────────────────────────────────────
# 평가 요약 통계 구축
# ──────────────────────────────────────────────

def build_eval_summary(student_name: str, records: list[dict]) -> dict:
    """
    특정 학생의 과목별 평가 요약 통계를 생성합니다.

    각 과목에 대해 기록 수, 긍정도 분포, 날짜 범위, 주요 기록 내용을
    계산합니다.

    Args:
        student_name: 학생 이름
        records: 해당 학생의 전체 레코드 리스트

    Returns:
        구조화된 평가 요약 딕셔너리:
        {
            "student": str,
            "total_records": int,
            "subjects": {
                "국어": {
                    "count": int,
                    "positive_pct": float,
                    "neutral_pct": float,
                    "negative_pct": float,
                    "date_range": {"start": str, "end": str},
                    "key_records": [{"date": str, "title": str, "content": str, "sentiment": str}, ...]
                },
                ...
            }
        }
    """
    grouped = group_by_subject(records)
    subjects_summary = {}

    for subject, subject_records in grouped.items():
        # 긍정도 분포 계산
        sentiments = [
            rec.get("긍정도", "").strip()
            for rec in subject_records
            if rec.get("긍정도", "").strip()
        ]
        total_sentiments = len(sentiments) if sentiments else 1  # 0 나눗셈 방지
        counter = Counter(sentiments)

        positive_count = counter.get("긍정✅", 0)
        neutral_count = counter.get("중립📋", 0)
        negative_count = counter.get("관찰필요🔍", 0)

        positive_pct = round(positive_count / total_sentiments * 100, 1)
        neutral_pct = round(neutral_count / total_sentiments * 100, 1)
        negative_pct = round(negative_count / total_sentiments * 100, 1)

        # 날짜 범위
        dates = sorted(
            [rec.get("날짜", "") for rec in subject_records if rec.get("날짜")]
        )
        date_range = {
            "start": dates[0] if dates else "",
            "end": dates[-1] if dates else "",
        }

        # 주요 기록 (최대 5개, 최신순)
        key_records = []
        sorted_records = sorted(
            subject_records,
            key=lambda r: r.get("날짜", ""),
            reverse=True,
        )
        for rec in sorted_records[:5]:
            key_records.append({
                "date": rec.get("날짜", ""),
                "title": rec.get("기록제목", ""),
                "content": rec.get("내용", ""),
                "sentiment": rec.get("긍정도", ""),
            })

        subjects_summary[subject] = {
            "count": len(subject_records),
            "positive_pct": positive_pct,
            "neutral_pct": neutral_pct,
            "negative_pct": negative_pct,
            "date_range": date_range,
            "key_records": key_records,
        }

    return {
        "student": student_name,
        "total_records": len(records),
        "subjects": subjects_summary,
    }


# ──────────────────────────────────────────────
# 평가 텍스트 구성 (단순 연결 방식)
# ──────────────────────────────────────────────

def build_eval_text_simple(
    student_name: str,
    subject: str,
    records: list[dict],
) -> str:
    """
    LLM 생성 평가문이 없을 때 사용하는 단순 연결 요약 텍스트를 생성합니다.

    날짜순(오름차순)으로 정렬하여 각 기록을 불릿 포인트로 나열합니다.

    Args:
        student_name: 학생 이름
        subject: 과목명
        records: 해당 학생·과목의 레코드 리스트

    Returns:
        불릿 포인트 형식의 평가 텍스트 문자열

    Example:
        • 2026-03-15: 수업 태도가 바르고 적극적으로 참여함
        • 2026-04-02: 발표를 자신 있게 잘 함
    """
    if not records:
        return ""

    # 날짜 오름차순 정렬 (시간순)
    sorted_records = sorted(
        records,
        key=lambda r: r.get("날짜", ""),
    )

    lines = []
    for rec in sorted_records:
        date = rec.get("날짜", "날짜 없음")
        content = (rec.get("내용", "") or "").strip()
        if content:
            lines.append(f"• {date}: {content}")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# i-scream 입력용 평가 데이터 구성
# ──────────────────────────────────────────────

def build_eval_data_for_iscream(
    student_name: str,
    records: list[dict],
    eval_texts: dict[str, str] | None = None,
) -> list[dict]:
    """
    i-scream 자동화에 직접 사용할 수 있는 평가 데이터 리스트를 구성합니다.

    eval_texts가 제공되면 LLM이 생성한 평가 텍스트를 사용하고,
    제공되지 않으면 build_eval_text_simple로 폴백합니다.

    Args:
        student_name: 학생 이름
        records: 해당 학생의 전체 레코드 리스트
        eval_texts: LLM 생성 평가문 딕셔너리 {과목: 평가문} (선택)

    Returns:
        i-scream 입력용 딕셔너리 리스트:
        [
            {
                "student": "김민준",
                "subject": "국어",
                "eval_text": "수업 태도가 우수하고..."
            },
            ...
        ]
    """
    if eval_texts is None:
        eval_texts = {}

    grouped = group_by_subject(records)
    result = []

    for subject, subject_records in grouped.items():
        # LLM 생성 텍스트 우선, 없으면 단순 연결 폴백
        if subject in eval_texts and eval_texts[subject].strip():
            eval_text = eval_texts[subject].strip()
        else:
            eval_text = build_eval_text_simple(
                student_name, subject, subject_records
            )

        # 빈 텍스트는 건너뛰기
        if not eval_text:
            continue

        result.append({
            "student": student_name,
            "subject": subject,
            "eval_text": eval_text,
        })

    return result


# ──────────────────────────────────────────────
# 전체 학생 미리보기
# ──────────────────────────────────────────────

def preview_all_students(
    records: list[dict],
    eval_texts: dict[str, dict[str, str]] | None = None,
) -> list[dict]:
    """
    전체 학생의 i-scream 평가 데이터를 일괄 생성하여 반환합니다.

    Args:
        records: Supabase에서 조회한 전체 레코드
        eval_texts: 학생별 LLM 평가문 딕셔너리
                    {학생이름: {과목: 평가문}} (선택)

    Returns:
        전체 학생의 평가 데이터 리스트 (자동화 입력 준비 완료)
    """
    students = get_unique_students(records)
    all_eval_data = []

    for student_name in students:
        student_records = get_records_for_student(records, student_name)
        student_eval_texts = (eval_texts or {}).get(student_name)

        eval_data = build_eval_data_for_iscream(
            student_name, student_records, student_eval_texts
        )
        all_eval_data.extend(eval_data)

    return all_eval_data


# ──────────────────────────────────────────────
# 출력 유틸리티
# ──────────────────────────────────────────────

def _print_eval_preview(
    student_name: str,
    eval_data: list[dict],
    summary: dict,
) -> None:
    """학생별 평가 미리보기를 콘솔에 출력합니다."""
    print(f"\n{'━' * 60}")
    print(f"👨‍🎓 {student_name} — 총 {summary['total_records']}개 기록")
    print(f"{'━' * 60}")

    for entry in eval_data:
        subject = entry["subject"]
        eval_text = entry["eval_text"]
        subj_summary = summary["subjects"].get(subject, {})

        count = subj_summary.get("count", 0)
        pos = subj_summary.get("positive_pct", 0)
        neu = subj_summary.get("neutral_pct", 0)
        neg = subj_summary.get("negative_pct", 0)
        date_range = subj_summary.get("date_range", {})
        start = date_range.get("start", "?")
        end = date_range.get("end", "?")

        print(f"\n  📚 [{subject}] — {count}개 기록 ({start} ~ {end})")
        print(f"     긍정도: ✅{pos}% | 📋{neu}% | 🔍{neg}%")
        print(f"     ──────────────────────────────────────")

        # 평가 텍스트 (들여쓰기 처리)
        for line in eval_text.split("\n"):
            print(f"     {line}")

    print()


# ──────────────────────────────────────────────
# 단독 실행 모드
# ──────────────────────────────────────────────

def main():
    """CLI 진입점: 학생 평가 데이터 미리보기를 출력합니다."""
    parser = argparse.ArgumentParser(
        description="학생 교과 평가 데이터 미리보기"
    )
    parser.add_argument(
        "--student",
        type=str,
        default=None,
        help="특정 학생만 미리보기 (예: --student 김민준)",
    )
    args = parser.parse_args()

    print("🔍 Supabase에서 데이터를 조회합니다...\n")

    try:
        records = fetch_all_records()
    except EnvironmentError as e:
        print(str(e))
        return
    except Exception as e:
        print(f"❌ 데이터 조회 중 오류 발생: {e}")
        return

    if not records:
        print("⚠️ 조회된 레코드가 없습니다.")
        return

    # 대상 학생 결정
    if args.student:
        students = [args.student]
        # 해당 학생이 데이터에 존재하는지 확인
        all_students = get_unique_students(records)
        if args.student not in all_students:
            print(f"⚠️ '{args.student}' 학생을 찾을 수 없습니다.")
            print(f"   등록된 학생: {', '.join(all_students[:10])}")
            if len(all_students) > 10:
                print(f"   ... 외 {len(all_students) - 10}명")
            return
    else:
        students = get_unique_students(records)

    print(f"📋 총 {len(students)}명의 학생 평가 미리보기를 생성합니다.\n")

    # 전체 평가 데이터 및 미리보기 출력
    total_entries = 0
    for student_name in students:
        student_records = get_records_for_student(records, student_name)
        if not student_records:
            continue

        eval_data = build_eval_data_for_iscream(student_name, student_records)
        summary = build_eval_summary(student_name, student_records)

        _print_eval_preview(student_name, eval_data, summary)
        total_entries += len(eval_data)

    # 최종 요약
    print("=" * 60)
    print(f"✅ 미리보기 완료: {len(students)}명, 총 {total_entries}개 과목 평가")
    print("=" * 60)


if __name__ == "__main__":
    main()
