"""
grade_data_parser.py — 성취기준별 단계배정표 및 행동특성/창체 초안 파서

data/ 디렉터리에 있는 마크다운 파일들을 파싱하여
학생별·과목별·단원별 단계 정보와 행동특성/창체 평어 텍스트를
구조화된 파이썬 딕셔너리로 반환합니다.

사용법:
    from grade_data_parser import load_grade_data, load_behavior_data

    grade_data = load_grade_data()
    # grade_data["국어"]["강시우"] → {"1단원": "잘함", "4단원": "잘함"}

    behavior_data = load_behavior_data()
    # behavior_data["행동특성"]["강시우"] → "차분하고 생각이 깊은..."
"""

import re
import sys
from pathlib import Path
from typing import Optional

# Windows 콘솔 한글/이모지 출력 인코딩 오류 방지
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ── 파일 경로 ─────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
GRADE_TABLE_FILE = DATA_DIR / "2026_1학기_성취기준별_단계배정표.md"
BEHAVIOR_FILE = DATA_DIR / "2026_1학기_행동특성_창체_초안.md"


# ── 단계 용어 매핑 (배정표 3단계 → i-scream 4단계) ──────────────
# i-scream 성취기준 테이블에 표시되는 수준: 최상 / 상 / 중 / 하
LEVEL_MAP = {
    "매우잘함": "최상",
    "잘함": "상",
    "노력요함": "중",
    # 추정 표기 제거 후의 값도 처리
    "매우잘함(추정)": "최상",
    "잘함(추정)": "상",
    "노력요함(추정)": "중",
    # 띄어쓰기 대응
    "매우잘함": "최상",
    "노력요함": "중",
    # 미응시 등 특수 케이스
    "미응시": None,
}

# 역매핑 (i-scream 수준 → 배정표 단계)
REVERSE_LEVEL_MAP = {v: k for k, v in LEVEL_MAP.items() if v is not None}


def _clean_level(raw_level: str) -> Optional[str]:
    """
    배정표의 원본 단계 텍스트를 정리합니다.
    '(추정)' 접미사를 제거하고 순수 단계명만 반환합니다.
    또한 모든 공백을 제거하여 일관된 매핑을 보장합니다.

    Returns:
        정리된 단계명 또는 None (미응시 등)
    """
    if not raw_level:
        return None
    cleaned = raw_level.strip()
    if cleaned == "미응시":
        return None
    # "(추정)" 제거
    cleaned = re.sub(r'\(추정\)', '', cleaned).strip()
    # 모든 공백 제거 (예: "매우 잘함" -> "매우잘함", "노력 요함" -> "노력요함")
    cleaned = cleaned.replace(" ", "")
    return cleaned if cleaned else None


def _level_to_iscream(raw_level: str) -> Optional[str]:
    """
    배정표 단계를 i-scream 수준 표기로 변환합니다.

    Args:
        raw_level: 배정표의 원본 단계 (예: "잘함", "매우잘함(추정)")

    Returns:
        i-scream 수준 (예: "최상", "상", "하") 또는 None
    """
    cleaned = _clean_level(raw_level)
    if cleaned is None:
        return None
    return LEVEL_MAP.get(cleaned)


# ── 마크다운 테이블 파서 ──────────────────────────────────────

def _parse_md_table(lines: list[str]) -> list[list[str]]:
    """
    마크다운 테이블 라인들을 파싱하여 2D 리스트로 반환합니다.
    구분선(---|---) 행은 제거합니다.

    Args:
        lines: 마크다운 테이블의 라인 리스트 (| col1 | col2 | 형식)

    Returns:
        [[cell1, cell2, ...], ...] 형태의 2D 리스트
    """
    rows = []
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        # 구분선 행 스킵 (--- 패턴: 모든 셀이 하이픈/콜론/공백으로만 구성)
        stripped_no_space = line.replace(' ', '')
        if re.match(r'^\|[\-:]+(\|[\-:]+)*\|?$', stripped_no_space):
            continue
        # 셀 분리
        cells = [cell.strip() for cell in line.split('|')]
        # 맨 앞뒤 빈 문자열 제거 (| 로 시작/끝하므로)
        if cells and cells[0] == '':
            cells = cells[1:]
        if cells and cells[-1] == '':
            cells = cells[:-1]
        if cells:
            rows.append(cells)
    return rows


def _extract_unit_label(header_text: str) -> str:
    """
    테이블 헤더에서 단원 라벨을 추출합니다.

    예시:
        "1단원: 시 낭송 [4국05-04/05]" → "1단원"
        "2단원: 평면도형" → "2단원"
        "1단원: 덧셈·뺄셈" → "1단원"
        "[4사01-01] 장소 소개" → "01-01"
        "자율: 학교폭력예방교육" → "자율"

    Returns:
        단원을 식별하는 간결한 라벨
    """
    text = header_text.strip()

    # 패턴 1: "N단원: ..." 형태
    m = re.match(r'^(\d+)단원', text)
    if m:
        return f"{m.group(1)}단원"

    # 패턴 2: "N. 제목" 형태 (성취기준 표 헤더)
    m = re.match(r'^(\d+)\.\s', text)
    if m:
        return f"{m.group(1)}단원"

    # 패턴 3: "[4사01-01]" 같은 성취기준 코드
    m = re.search(r'\[4\w+(\d{2}-\d{2}(?:/\d{2})?)\]', text)
    if m:
        return m.group(1)

    # 패턴 4: 창체 영역명 (자율/동아리/진로)
    for keyword in ["자율", "동아리", "진로"]:
        if keyword in text:
            return keyword

    # 폴백: 원본 텍스트의 앞 20자
    return text[:20]


def _extract_unit_number_from_header(header_text: str) -> Optional[int]:
    """
    테이블 헤더에서 단원 번호를 추출합니다.

    Returns:
        단원 번호 (1~6) 또는 None
    """
    text = header_text.strip()
    # "N단원" 또는 "N. 제목" 형태
    m = re.match(r'^(\d+)', text)
    if m:
        num = int(m.group(1))
        if 1 <= num <= 9:
            return num

    # 성취기준 코드 형태인 경우 (예: "[4사01-01] 장소 소개")
    m = re.search(r'\[4\w+(\d{2})-\d{2}', text)
    if m:
        num = int(m.group(1))
        if 1 <= num <= 9:
            return num

    return None


# ── 성취기준별 단계배정표 로더 ────────────────────────────────

def load_grade_data(filepath: Optional[str] = None) -> dict:
    """
    성취기준별 단계배정표 마크다운 파일을 파싱합니다.

    Args:
        filepath: 파일 경로 (미지정 시 기본 경로 사용)

    Returns:
        중첩 딕셔너리:
        {
            "국어": {
                "강시우": {
                    "1단원": {"raw": "잘함", "iscream": "상", "unit_num": 1},
                    "4단원": {"raw": "잘함", "iscream": "상", "unit_num": 4},
                },
                ...
            },
            "수학": { ... },
            ...
        }
    """
    path = Path(filepath) if filepath else GRADE_TABLE_FILE
    if not path.exists():
        raise FileNotFoundError(f"단계배정표 파일을 찾을 수 없습니다: {path}")

    content = path.read_text(encoding='utf-8')
    lines = content.split('\n')

    result = {}
    current_subject = None
    table_lines = []
    in_table = False

    for line in lines:
        stripped = line.strip()

        # 과목 섹션 헤더 감지 (## 국어, ## 수학 등)
        subject_match = re.match(r'^##\s+(.+)$', stripped)
        if subject_match:
            # 이전 과목의 테이블 처리
            if current_subject and table_lines:
                result[current_subject] = _parse_subject_table(current_subject, table_lines)
                table_lines = []
                in_table = False

            subject_name = subject_match.group(1).strip()
            # 유효한 과목명인지 확인 (부가 설명 섹션은 건너뛰기)
            valid_subjects = ["도덕", "국어", "수학", "사회", "음악", "미술", "창체"]
            if subject_name in valid_subjects:
                current_subject = subject_name
            else:
                current_subject = None
            continue

        # 테이블 행 감지
        if current_subject and stripped.startswith('|'):
            in_table = True
            table_lines.append(stripped)
        elif in_table and not stripped.startswith('|') and not stripped.startswith('>'):
            # 테이블 종료
            if current_subject and table_lines:
                result[current_subject] = _parse_subject_table(current_subject, table_lines)
                table_lines = []
            in_table = False

    # 마지막 과목 처리
    if current_subject and table_lines:
        result[current_subject] = _parse_subject_table(current_subject, table_lines)

    return result


def _parse_subject_table(subject: str, table_lines: list[str]) -> dict:
    """
    과목별 마크다운 테이블을 파싱하여 학생별 단원 단계 딕셔너리를 반환합니다.

    Returns:
        {
            "강시우": {
                "1단원": {"raw": "잘함", "iscream": "상", "unit_num": 1},
                ...
            },
            ...
        }
    """
    rows = _parse_md_table(table_lines)
    if len(rows) < 2:
        return {}

    # 첫 행은 헤더 (학생 | 단원1 | 단원2 | ...)
    headers = rows[0]
    # 첫 번째 컬럼은 "학생"이므로 건너뛰기
    unit_headers = headers[1:]

    # 단원 라벨 및 번호 추출
    unit_labels = [_extract_unit_label(h) for h in unit_headers]
    unit_numbers = [_extract_unit_number_from_header(h) for h in unit_headers]

    student_data = {}
    for row in rows[1:]:  # 데이터 행
        if len(row) < 2:
            continue
        student_name = row[0].strip()
        if not student_name:
            continue

        units = {}
        for i, cell in enumerate(row[1:]):
            if i >= len(unit_labels):
                break
            label = unit_labels[i]
            raw_level = cell.strip()
            iscream_level = _level_to_iscream(raw_level)
            clean = _clean_level(raw_level)

            units[label] = {
                "raw": clean,            # 정리된 원본 단계 (매우잘함/잘함/노력요함)
                "iscream": iscream_level, # i-scream 표기 (최상/상/하) 또는 None
                "unit_num": unit_numbers[i],  # 단원 번호 (1~6) 또는 None
                "header": unit_headers[i] if i < len(unit_headers) else "",  # 원본 헤더
            }

        student_data[student_name] = units

    return student_data


# ── 행동특성 및 창체 초안 로더 ────────────────────────────────

def load_behavior_data(filepath: Optional[str] = None) -> dict:
    """
    행동특성 및 창체 초안 마크다운 파일을 파싱합니다.

    Args:
        filepath: 파일 경로 (미지정 시 기본 경로 사용)

    Returns:
        {
            "행동특성": {"강시우": "차분하고 생각이 깊은...", ...},
            "창체_자율자치_동아리": {"강시우": "마니또 활동에서...", ...},
            "창체_진로": {"강시우": "자기이해 활동에서...", ...},
            "교사참고": {"정두영": "3/25 모둠활동 중...", ...},
        }
    """
    path = Path(filepath) if filepath else BEHAVIOR_FILE
    if not path.exists():
        raise FileNotFoundError(f"행동특성/창체 파일을 찾을 수 없습니다: {path}")

    content = path.read_text(encoding='utf-8')
    lines = content.split('\n')

    result = {
        "행동특성": {},
        "창체_자율자치_동아리": {},
        "창체_진로": {},
        "교사참고": {},
    }

    current_section = None
    current_student = None
    current_text_lines = []

    def _flush_student():
        """현재 학생의 텍스트를 결과에 저장합니다."""
        nonlocal current_student, current_text_lines
        if current_section and current_student and current_text_lines:
            text = '\n'.join(current_text_lines).strip()
            if text:
                result[current_section][current_student] = text
        current_text_lines = []

    for line in lines:
        stripped = line.strip()

        # 섹션 헤더 감지
        if stripped == "## 행동특성 및 종합의견 (18명)":
            _flush_student()
            current_section = "행동특성"
            current_student = None
            continue
        elif stripped == "### 가. 자율·자치활동 및 동아리활동":
            _flush_student()
            current_section = "창체_자율자치_동아리"
            current_student = None
            continue
        elif stripped == "### 나. 진로활동":
            _flush_student()
            current_section = "창체_진로"
            current_student = None
            continue
        elif stripped.startswith("## 교사 참고"):
            _flush_student()
            current_section = "교사참고"
            current_student = None
            continue
        elif stripped.startswith("## 창의적 체험활동"):
            _flush_student()
            current_section = None  # 임시, 하위 섹션에서 설정됨
            current_student = None
            continue
        elif stripped == "---":
            _flush_student()
            continue

        # 학생 이름 감지 (**N. 이름** 형태)
        student_match = re.match(r'^\*\*(?:\d+\.\s+)?(.+?)\*\*$', stripped)
        if student_match and current_section:
            _flush_student()
            current_student = student_match.group(1).strip()
            continue

        # 텍스트 수집
        if current_section and current_student and stripped:
            current_text_lines.append(stripped)

    # 마지막 학생 처리
    _flush_student()

    return result


# ── 통합 데이터 로더 ──────────────────────────────────────────

def load_all_data() -> dict:
    """
    성취기준별 단계배정표와 행동특성/창체 초안을 모두 로드합니다.

    Returns:
        {
            "grades": { ... },      # load_grade_data() 결과
            "behavior": { ... },    # load_behavior_data() 결과
        }
    """
    return {
        "grades": load_grade_data(),
        "behavior": load_behavior_data(),
    }


def get_student_grade_for_subject(
    grade_data: dict,
    student_name: str,
    subject: str,
) -> list[dict]:
    """
    특정 학생의 특정 과목에 대한 단원별 단계 정보를 반환합니다.
    i-scream 자동 입력에 사용할 수 있는 형태로 가공합니다.

    Args:
        grade_data: load_grade_data()의 반환값
        student_name: 학생 이름
        subject: 과목명

    Returns:
        [
            {"unit_label": "1단원", "unit_num": 1, "iscream_level": "상", "raw_level": "잘함"},
            {"unit_label": "4단원", "unit_num": 4, "iscream_level": "하", "raw_level": "노력요함"},
        ]
        유효한 단원만 포함 (미응시 제외)
    """
    subject_data = grade_data.get(subject, {})
    student_units = subject_data.get(student_name, {})

    entries = []
    for label, info in student_units.items():
        if info["iscream"] is None:
            continue  # 미응시 건너뛰기
        entries.append({
            "unit_label": label,
            "unit_num": info["unit_num"],
            "iscream_level": info["iscream"],
            "raw_level": info["raw"],
            "header": info.get("header", ""),
        })

    # 단원 번호 순으로 정렬
    entries.sort(key=lambda x: x["unit_num"] if x["unit_num"] is not None else 999)
    return entries


def get_all_students() -> list[str]:
    """
    배정표에서 전체 학생 이름 목록을 반환합니다.

    Returns:
        ["강시우", "김가을", ...] (순서 유지)
    """
    grade_data = load_grade_data()
    # 아무 과목에서나 학생 목록 추출 (모든 과목에 동일 학생)
    for subject, students in grade_data.items():
        return list(students.keys())
    return []


# ── CLI 진입점 ────────────────────────────────────────────────

def main():
    """단독 실행 시 파싱 결과를 출력합니다."""
    print("=" * 60)
    print("📊 성취기준별 단계배정표 파서 테스트")
    print("=" * 60)

    try:
        grade_data = load_grade_data()
        print(f"\n✅ 과목 수: {len(grade_data)}")
        for subject, students in grade_data.items():
            print(f"\n📚 [{subject}] — {len(students)}명")
            for student, units in students.items():
                unit_summary = []
                for label, info in units.items():
                    raw = info['raw'] or '미응시'
                    iscream = info['iscream'] or '제외'
                    unit_summary.append(f"{label}={raw}({iscream})")
                print(f"   {student}: {', '.join(unit_summary)}")
    except Exception as e:
        print(f"❌ 단계배정표 파싱 실패: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n{'=' * 60}")
    print("📝 행동특성 및 창체 초안 파서 테스트")
    print("=" * 60)

    try:
        behavior_data = load_behavior_data()
        for section, students in behavior_data.items():
            print(f"\n📋 [{section}] — {len(students)}명")
            for student, text in students.items():
                preview = text[:60] + "..." if len(text) > 60 else text
                print(f"   {student}: {preview}")
    except Exception as e:
        print(f"❌ 행동특성/창체 파싱 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
