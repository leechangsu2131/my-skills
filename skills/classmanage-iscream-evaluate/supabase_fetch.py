"""
supabase_fetch.py — Supabase 데이터 파이프라인 모듈

class-manage 테이블에서 학생 기록을 조회하고,
학생별·과목별로 분류하는 유틸리티 함수를 제공합니다.

사용법:
    모듈로 임포트:
        from supabase_fetch import fetch_all_records, get_unique_students

    단독 실행 (요약 통계 출력):
        python supabase_fetch.py
"""

import json
import os
import re
import warnings
from collections import defaultdict
from pathlib import Path

# SSL 검증 오류 해결을 위해 httpx Client 패치
import httpx
warnings.filterwarnings("ignore")

_original_init = httpx.Client.__init__
def _patched_init(self, *args, **kwargs):
    kwargs['verify'] = False
    _original_init(self, *args, **kwargs)
httpx.Client.__init__ = _patched_init

_original_async_init = httpx.AsyncClient.__init__
def _patched_async_init(self, *args, **kwargs):
    kwargs['verify'] = False
    _original_async_init(self, *args, **kwargs)
httpx.AsyncClient.__init__ = _patched_async_init

from dotenv import load_dotenv
from supabase import create_client, Client



# ──────────────────────────────────────────────
# 환경 변수 및 Supabase 클라이언트 설정
# ──────────────────────────────────────────────

# 출결 관련 자동 태깅에 사용되는 키워드 목록
_ATTENDANCE_KEYWORDS = [
    "출석", "결석", "지각", "조퇴", "결과", "출결",
    "병결", "무단", "사유", "출석부", "등교", "하교",
]

# 유효한 교과목 목록 (i-scream 평가 기록 대상)
VALID_SUBJECTS = [
    "국어", "수학", "사회", "과학", "도덕",
    "체육", "음악", "미술", "영어", "창의적 체험활동",
]


def _load_env() -> tuple[str, str]:
    """
    .env 파일에서 Supabase 자격 증명을 로드합니다.

    우선순위:
        1. 현재 프로젝트의 .env 파일
        2. 형제 프로젝트(classmanage-record-viewer)의 .env.local 파일

    Returns:
        (supabase_url, supabase_key) 튜플
    """
    # 1) 현재 프로젝트의 .env 로드 시도
    own_env = Path(__file__).parent / ".env"
    if own_env.exists():
        load_dotenv(own_env, override=True)

    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")

    # 2) 자격 증명이 없으면 형제 프로젝트의 .env.local 폴백
    if not url or not key:
        sibling_env = (
            Path(__file__).parent.parent
            / "classmanage-record-viewer"
            / ".env.local"
        )
        if sibling_env.exists():
            load_dotenv(sibling_env, override=True)
            url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
            key = os.environ.get("SUPABASE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")

    if not url or not key:
        raise EnvironmentError(
            "❌ Supabase 자격 증명을 찾을 수 없습니다. "
            ".env 파일에 SUPABASE_URL과 SUPABASE_KEY를 설정해주세요."
        )

    return url, key


def _get_client() -> Client:
    """Supabase 클라이언트 인스턴스를 생성하여 반환합니다."""
    url, key = _load_env()
    return create_client(url, key)


# ──────────────────────────────────────────────
# 데이터 조회
# ──────────────────────────────────────────────

def fetch_all_records() -> list[dict]:
    """
    class-manage 테이블의 전체 레코드를 날짜 내림차순으로 조회합니다.

    Returns:
        레코드 딕셔너리의 리스트
    """
    client = _get_client()
    # Supabase Python 클라이언트로 전체 조회 (날짜 내림차순)
    response = client.table("class-manage").select("*").order("날짜", desc=True).execute()
    records = response.data or []

    # 출결 자동 태깅: 과목이 비어 있고 출결 관련 키워드가 포함된 레코드
    for rec in records:
        rec = _auto_tag_attendance(rec)

    print(f"📥 Supabase에서 총 {len(records)}개의 기록을 조회했습니다.")
    return records


def _auto_tag_attendance(record: dict) -> dict:
    """
    과목이 비어 있는 레코드 중 출결 관련 키워드가 포함되어 있으면
    과목을 '출결'로 자동 태깅합니다.

    Args:
        record: 단일 레코드 딕셔너리

    Returns:
        (필요시 수정된) 레코드 딕셔너리
    """
    subject = (record.get("과목") or "").strip()
    if subject:
        return record  # 이미 과목이 지정된 경우 건너뛰기

    # 제목과 내용에서 출결 키워드 확인
    title = record.get("기록제목", "") or ""
    content = record.get("내용", "") or ""
    combined = f"{title} {content}"

    for keyword in _ATTENDANCE_KEYWORDS:
        if keyword in combined:
            record["과목"] = "출결"
            break

    return record


# ──────────────────────────────────────────────
# 학생 이름 파싱
# ──────────────────────────────────────────────

def parse_student_names(raw_name) -> list[str]:
    """
    다양한 형식의 학생 이름 데이터를 파싱하여 이름 리스트로 반환합니다.

    지원 형식:
        - JSON 배열 문자열: '["김민준", "이서연"]'
        - 쉼표/공백 구분 문자열: "김민준, 이서연" 또는 "김민준 이서연"
        - 이미 리스트인 경우: ["김민준", "이서연"]
        - None 또는 빈 문자열

    Args:
        raw_name: 원본 이름 데이터

    Returns:
        정리된 이름 문자열의 리스트 (빈 문자열 제외)
    """
    if raw_name is None:
        return []

    # 이미 리스트인 경우
    if isinstance(raw_name, list):
        return [name.strip() for name in raw_name if isinstance(name, str) and name.strip()]

    # 문자열이 아닌 경우
    if not isinstance(raw_name, str):
        return []

    raw_name = raw_name.strip()
    if not raw_name:
        return []

    # JSON 배열 문자열 시도
    if raw_name.startswith("[") and raw_name.endswith("]"):
        try:
            parsed = json.loads(raw_name)
            if isinstance(parsed, list):
                return [
                    name.strip()
                    for name in parsed
                    if isinstance(name, str) and name.strip()
                ]
        except (json.JSONDecodeError, TypeError):
            pass  # JSON 파싱 실패 시 아래 구분자 방식으로 폴백

    # 쉼표 또는 공백 구분자 분리
    parts = re.split(r"[,\s]+", raw_name)
    return [p.strip() for p in parts if p.strip()]


# ──────────────────────────────────────────────
# 데이터 필터링·그룹핑 유틸리티
# ──────────────────────────────────────────────

def get_unique_students(records: list[dict]) -> list[str]:
    """
    전체 레코드에서 중복 없이 학생 이름을 추출하고 가나다순 정렬하여 반환합니다.

    Args:
        records: 레코드 딕셔너리 리스트

    Returns:
        정렬된 학생 이름 리스트
    """
    students: set[str] = set()
    for rec in records:
        names = parse_student_names(rec.get("🧑‍🎓 이름"))
        students.update(names)
    return sorted(students)


def get_unique_subjects(records: list[dict]) -> list[str]:
    """
    전체 레코드에서 고유 과목 목록을 추출하여 반환합니다.

    반환 순서: VALID_SUBJECTS에 정의된 순서 우선, 그 외 과목은 뒤에 추가.

    Args:
        records: 레코드 딕셔너리 리스트

    Returns:
        과목 문자열 리스트
    """
    found: set[str] = set()
    for rec in records:
        subject = (rec.get("과목") or "").strip()
        if subject:
            found.add(subject)

    # 정렬: 유효 과목 순서 우선 → 나머지 알파벳순
    ordered = [s for s in VALID_SUBJECTS if s in found]
    extras = sorted(found - set(VALID_SUBJECTS))
    return ordered + extras


def get_records_for_student(records: list[dict], student_name: str) -> list[dict]:
    """
    특정 학생이 포함된 레코드만 필터링하여 반환합니다.

    Args:
        records: 전체 레코드 리스트
        student_name: 검색할 학생 이름

    Returns:
        해당 학생이 포함된 레코드 리스트
    """
    result = []
    for rec in records:
        names = parse_student_names(rec.get("🧑‍🎓 이름"))
        if student_name in names:
            result.append(rec)
    return result


def group_by_subject(records: list[dict]) -> dict[str, list[dict]]:
    """
    레코드를 과목별로 그룹화하여 딕셔너리로 반환합니다.

    과목이 비어 있는 레코드는 '미분류' 키로 분류됩니다.

    Args:
        records: 레코드 딕셔너리 리스트

    Returns:
        {과목명: [레코드]} 형태의 딕셔너리
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        subject = (rec.get("과목") or "").strip() or "미분류"
        grouped[subject].append(rec)
    return dict(grouped)


# ──────────────────────────────────────────────
# 단독 실행 모드: 요약 통계 출력
# ──────────────────────────────────────────────

def _print_summary(records: list[dict]) -> None:
    """조회된 데이터의 요약 통계를 출력합니다."""
    students = get_unique_students(records)
    subjects = get_unique_subjects(records)

    print("\n" + "=" * 50)
    print("📊 데이터 요약 통계")
    print("=" * 50)
    print(f"  📋 전체 레코드 수: {len(records)}")
    print(f"  👨‍🎓 학생 수: {len(students)}명")
    print(f"  📚 과목 수: {len(subjects)}개")

    # 과목별 레코드 수
    print("\n📚 과목별 레코드 수:")
    grouped = group_by_subject(records)
    for subject in subjects:
        count = len(grouped.get(subject, []))
        if count > 0:
            print(f"  • {subject}: {count}개")
    if "미분류" in grouped:
        print(f"  • 미분류: {len(grouped['미분류'])}개")

    # 학생 목록
    print(f"\n👨‍🎓 학생 목록 ({len(students)}명):")
    for i, name in enumerate(students, 1):
        student_records = get_records_for_student(records, name)
        print(f"  {i:3d}. {name} — {len(student_records)}개 기록")

    # 날짜 범위
    dates = [rec.get("날짜", "") for rec in records if rec.get("날짜")]
    if dates:
        dates_sorted = sorted(dates)
        print(f"\n📅 기록 기간: {dates_sorted[0]} ~ {dates_sorted[-1]}")

    # 긍정도 분포
    sentiments = [rec.get("긍정도", "") for rec in records if rec.get("긍정도")]
    if sentiments:
        print("\n😊 긍정도 분포:")
        from collections import Counter
        counter = Counter(sentiments)
        for sentiment, count in counter.most_common():
            pct = count / len(sentiments) * 100
            print(f"  • {sentiment}: {count}개 ({pct:.1f}%)")

    print("=" * 50)


if __name__ == "__main__":
    print("🔍 Supabase class-manage 테이블 데이터 조회를 시작합니다...\n")
    try:
        all_records = fetch_all_records()
        if all_records:
            _print_summary(all_records)
        else:
            print("⚠️ 조회된 레코드가 없습니다.")
    except EnvironmentError as e:
        print(str(e))
    except Exception as e:
        print(f"❌ 데이터 조회 중 오류 발생: {e}")
