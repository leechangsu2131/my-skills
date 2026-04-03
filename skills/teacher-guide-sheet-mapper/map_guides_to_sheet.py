"""
국어/도덕 지도서 PDF 파일들에서 차시 정보를 추출하여 구글 시트 진도표에 업로드하는 스크립트.

기타 교과용 범용 매핑은 `map_general_guides_to_sheet.py`를 사용한다.

사용법:
  python map_guides_to_sheet.py               # dry-run (미리보기)
  python map_guides_to_sheet.py --upload      # 실제 업로드
  python map_guides_to_sheet.py --cleanup     # 중복행 삭제 후 업로드
"""
import os
import sys
import json
import re
import io
import argparse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── 환경 설정 ──────────────────────────────────────────────
SCHEDULE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCHEDULE_DIR)
import fitz  # pymupdf
from sheet_uploader.core import (
    REPLACE_ALL,
    REPLACE_APPEND,
    REPLACE_SUBJECTS,
    build_row_for_headers as shared_build_row_for_headers,
    delete_duplicate_rows as shared_delete_duplicate_rows,
    get_sheet as shared_get_sheet,
    upload_rows_to_sheet,
)

SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME", "시트1")
GUIDE_DIR = r"D:\지도서"
SPLIT_GUIDE_OUTPUT_DIR = str((Path(SCHEDULE_DIR).parent / "teacher-guide-subunit-splitter" / "output").resolve())
DOWNLOADS_DIRS = [
    str(Path(os.environ.get("USERPROFILE", "")) / "Downloads"),
    r"D:\Downloads",
]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
DONE_COLUMN_NAME = "실행여부"
DONE_COLUMN_FALLBACK_INDEX = 6
GUIDE_SEARCH_DIRS = [GUIDE_DIR, SPLIT_GUIDE_OUTPUT_DIR]
ANNUAL_PLAN_SEARCH_DIRS = [GUIDE_DIR, *DOWNLOADS_DIRS]


# ── 구글 시트 연결 ───────────────────────────────────────────
def get_sheet():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON").replace("\\n", "\n")
    creds = Credentials.from_service_account_info(
        json.loads(creds_json, strict=False), scopes=SCOPES
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    return sh, sh.worksheet(SHEET_NAME)

def normalize_search_text(text):
    return re.sub(r"[\s_\-\[\]\(\)]+", "", str(text)).lower()


def build_grade_search_tokens(grade_str):
    grade_text = str(grade_str or "").strip()
    if not grade_text:
        return []

    numbers = re.findall(r"\d+", grade_text)
    tokens = set()

    if len(numbers) >= 2:
        grade_num, term_num = numbers[:2]
        tokens.update(
            {
                normalize_search_text(grade_text),
                normalize_search_text(f"{grade_num}-{term_num}"),
                normalize_search_text(f"{grade_num}_{term_num}"),
                normalize_search_text(f"{grade_num}\ud559\ub144 {term_num}\ud559\uae30"),
                normalize_search_text(f"{grade_num}\ud559\ub144{term_num}\ud559\uae30"),
                normalize_search_text(f"{grade_num}\ud559\ub144 {term_num}"),
                normalize_search_text(f"{grade_num}\ud559\ub144{term_num}"),
            }
        )
    elif len(numbers) == 1:
        grade_num = numbers[0]
        tokens.update(
            {
                normalize_search_text(f"{grade_num}\ud559\ub144"),
                normalize_search_text(f"{grade_num}\ud559\ub144\uad70"),
            }
        )
    else:
        tokens.add(normalize_search_text(grade_text))

    return [token for token in tokens if token]


def build_split_run_search_text(groups_path, source_name, data):
    fragments = [str(groups_path), str(source_name), data.get("pdf", "")]

    for section in data.get("sections", []):
        fragments.append(section.get("title", ""))

    for group in data.get("groups", []):
        fragments.append(group.get("title", ""))
        fragments.append(group.get("parent_unit_title", ""))
        fragments.extend(group.get("context") or [])

    return normalize_search_text(" ".join(str(fragment) for fragment in fragments if fragment))


def is_schedule_content_group(group):
    detected_level = str(group.get("detected_level", "")).strip().lower()
    return detected_level not in {"section", "plan"}


def iter_search_pdfs(subject_prefix, search_dirs):
    seen = set()
    normalized_subject = normalize_search_text(subject_prefix)
    for base_dir in search_dirs:
        if not base_dir:
            continue
        search_path = Path(base_dir)
        if not search_path.exists():
            continue
        for pdf in search_path.rglob("*.pdf"):
            key = str(pdf.resolve())
            if key in seen:
                continue
            normalized_path = normalize_search_text(key)
            if normalized_subject not in normalized_path:
                continue
            seen.add(key)
            yield pdf


def build_lesson_name_patterns(lesson_value):
    lesson_text = str(lesson_value).replace("∼", "~").strip()
    if not lesson_text:
        return []
    patterns = {lesson_text}
    if "~" in lesson_text:
        left, right = [part.strip() for part in lesson_text.split("~", 1)]
        patterns.update(
            {
                lesson_text.replace("~", "-"),
                lesson_text.replace("~", "_"),
                f"{left}차시~{right}차시",
                f"{left}차시-{right}차시",
                f"{left}차시_{right}차시",
                f"{left}차시{right}차시",
            }
        )
    else:
        patterns.update(
            {
                f"{lesson_text}차시",
                f"_{lesson_text}.pdf",
                f"-{lesson_text}.pdf",
                f"_{lesson_text}_",
            }
        )
    return [normalize_search_text(pattern) for pattern in patterns if pattern]


def extract_title_match_tokens(title):
    tokens = [normalize_search_text(token) for token in re.findall(r"[0-9A-Za-z가-힣]+", str(title)) if len(token) >= 2]
    tokens = sorted(set(token for token in tokens if token), key=len, reverse=True)
    return tokens[:6]


MORAL_FILENAME_RE = re.compile(r"도덕(?P<grade>\d+)_(?P<unit>\d+)_(?P<lesson>\d+)_지도서\.pdf$", re.IGNORECASE)
KOREAN_FILENAME_RE = re.compile(r"국어(?P<grade>\d+-\d+)지도서_2_(?P<unit>\d+|독서|매체)\.pdf$", re.IGNORECASE)
GENERIC_UNIT_LABEL_RE = re.compile(r"^\d+\s*단원$")


def extract_grade_number(grade_str):
    match = re.search(r"\d+", str(grade_str or ""))
    return match.group(0) if match else ""


def find_exact_moral_pdf(all_pdfs, unit_num, lesson_num=None, grade_str="3-1"):
    try:
        target_unit = int(unit_num)
    except Exception:
        return None

    target_lesson = None
    if lesson_num is not None:
        lesson_match = re.search(r"\d+", str(lesson_num))
        if lesson_match:
            target_lesson = int(lesson_match.group(0))

    target_grade = extract_grade_number(grade_str) or "3"

    for pdf in all_pdfs:
        match = MORAL_FILENAME_RE.fullmatch(pdf.name)
        if not match or match.group("grade") != target_grade:
            continue
        if int(match.group("unit")) != target_unit:
            continue
        lesson_value = int(match.group("lesson"))
        if target_lesson is None:
            if lesson_value == 1:
                return str(pdf.resolve())
            continue
        if lesson_value == target_lesson:
            return str(pdf.resolve())

    return None


def normalize_korean_unit_key(unit_num):
    unit_text = str(unit_num).strip()
    if unit_text.isdigit():
        return str(int(unit_text))
    if "독서" in unit_text:
        return "독서"
    if "매체" in unit_text:
        return "매체"
    return unit_text


def find_exact_korean_pdf(all_pdfs, unit_num, grade_str="3-1"):
    target_unit = normalize_korean_unit_key(unit_num)
    target_grade = str(grade_str or "").strip()

    for pdf in all_pdfs:
        match = KOREAN_FILENAME_RE.fullmatch(pdf.name)
        if not match or match.group("grade") != target_grade:
            continue
        if match.group("unit") == target_unit:
            return str(pdf.resolve())

    return None


def find_subject_specific_pdf(subject_prefix, all_pdfs, unit_num, lesson_num=None, grade_str="3-1"):
    subject_text = str(subject_prefix).strip()
    if subject_text == "도덕":
        return find_exact_moral_pdf(all_pdfs, unit_num, lesson_num=lesson_num, grade_str=grade_str)
    if subject_text == "국어":
        return find_exact_korean_pdf(all_pdfs, unit_num, grade_str=grade_str)
    return None


def find_best_pdf(subject_prefix, unit_num, lesson_num=None, grade_str="3-1", lesson_title=None):
    all_pdfs = list(iter_search_pdfs(subject_prefix, GUIDE_SEARCH_DIRS))
    if not all_pdfs:
        return None

    exact_pdf = find_subject_specific_pdf(
        subject_prefix,
        all_pdfs,
        unit_num,
        lesson_num=lesson_num,
        grade_str=grade_str,
    )
    if exact_pdf:
        return exact_pdf

    best_pdf = None
    best_score = -1

    normalized_subject = normalize_search_text(subject_prefix)
    normalized_grade = normalize_search_text(grade_str)
    normalized_unit = normalize_search_text(unit_num)
    lesson_patterns = build_lesson_name_patterns(lesson_num) if lesson_num is not None else []
    lesson_title_tokens = extract_title_match_tokens(lesson_title)

    for pdf in all_pdfs:
        name = normalize_search_text(pdf.name)
        full_path = normalize_search_text(str(pdf))
        score = 0

        if normalized_subject in full_path:
            score += 1

        lesson_match = False
        if lesson_patterns:
            if any(pattern and pattern in full_path for pattern in lesson_patterns):
                score += 20
                lesson_match = True

        unit_match = False
        if any(
            pattern in full_path
            for pattern in (
                f"{normalized_unit}단원",
                f"_{normalized_unit}_",
                f"-{normalized_unit}_",
                f"_{normalized_unit}.",
            )
        ):
            score += 10
            unit_match = True
        elif isinstance(unit_num, str) and normalized_unit in full_path:
            score += 10
            unit_match = True

        if lesson_title_tokens:
            token_hits = sum(1 for token in lesson_title_tokens if token in full_path)
            if token_hits >= 3:
                score += 24
            elif token_hits == 2:
                score += 16
            elif token_hits == 1:
                score += 8

        if normalized_grade and normalized_grade in full_path:
            score += 5

        # 일반 통권 지도서 파일은 조각 파일(Split)보다 우선순위를 대폭 낮춥니다.
        # 이로써 아무리 이름이 부실한 조각 파일이더라도 원본 파일보다 우선적으로 매칭됩니다.
        is_original = "지도서" in pdf.name and "subunit_" not in pdf.name and "pdf_splits" not in str(pdf)
        if is_original and not unit_match and not lesson_match:
            score -= 100

        if score > best_score:
            best_score = score
            best_pdf = pdf

    if best_pdf:
        return str(best_pdf.resolve())
    return None

def format_pdf_path(pdf_path):
    if not pdf_path: return ""
    abs_p = os.path.abspath(pdf_path)
    user_prof = os.environ.get("USERPROFILE")
    if user_prof and abs_p.startswith(user_prof):
        return abs_p.replace(user_prof, "%USERPROFILE%")
    return abs_p


ANNUAL_PLAN_HEADER_LINES = {
    "단원",
    "주제",
    "차시",
    "차시명",
    "교과서 쪽수",
    "연간 지도 계획",
}
ANNUAL_PLAN_RESOURCE_MARKERS = (
    "별별 직업 속으로",
    "디지털 +",
    "할 수 있어요",
    "풍덩 사회 속으로",
)
ANNUAL_PLAN_UNIT_MARKER_RE = re.compile(r"^(\d+)\.\s*$")
ANNUAL_PLAN_THEME_START_RE = re.compile(r"^(\d+)\.\s*(.+)$")
ANNUAL_PLAN_LESSON_RE = re.compile(r"^(\d+(?:[~∼]\d+)?)$")
ANNUAL_PLAN_PAGE_RANGE_RE = re.compile(r"^(\d+\s*[~∼]\s*\d+)$")


def find_annual_plan_pdf(subject_prefix, grade_str="3-1"):
    normalized_grade = normalize_search_text(grade_str)
    best_pdf = None
    best_score = -1

    seen = set()
    for base_dir in ANNUAL_PLAN_SEARCH_DIRS:
        if not base_dir:
            continue
        root = Path(base_dir)
        if not root.exists():
            continue
        candidate_patterns = [
            f"*{subject_prefix}*연간*계획*.pdf",
            f"*{subject_prefix}*지도계획*.pdf",
            f"*{subject_prefix}*연간지도계획*.pdf",
        ]
        for pattern in candidate_patterns:
            for pdf in root.rglob(pattern):
                resolved = str(pdf.resolve())
                if resolved in seen:
                    continue
                seen.add(resolved)
                text = normalize_search_text(resolved)

                score = 10
                if normalized_grade and normalized_grade in text:
                    score += 8
                if root == Path(GUIDE_DIR):
                    score += 4
                if pdf.parent == root:
                    score += 2

                if score > best_score:
                    best_score = score
                    best_pdf = pdf

    return str(best_pdf.resolve()) if best_pdf else None


def dedupe_consecutive_lines(lines):
    deduped = []
    previous = None
    for raw in lines:
        normalized = normalize_pdf_line(raw)
        if not normalized:
            continue
        if normalized == previous:
            continue
        deduped.append(normalized)
        previous = normalized
    return deduped


def parse_range_start(range_text):
    text = str(range_text).replace("∼", "~")
    try:
        return int(text.split("~", 1)[0])
    except Exception:
        return 10**9


def parse_range_end(range_text):
    text = str(range_text).replace("бн", "~")
    try:
        parts = text.split("~", 1)
        return int(parts[1] if len(parts) > 1 else parts[0])
    except Exception:
        return -1


def normalize_unit_lesson_range(lesson_range, unit_start):
    text = str(lesson_range).replace("бн", "~").strip()
    if not text or unit_start in (None, 10**9):
        return text

    start = parse_range_start(text)
    end = parse_range_end(text)
    if start == 10**9 or end < start or unit_start <= 0:
        return text

    local_start = start - unit_start + 1
    local_end = end - unit_start + 1
    if local_start <= 0 or local_end < local_start:
        return text
    if local_start == local_end:
        return str(local_start)
    return f"{local_start}~{local_end}"


def parse_positive_int(value):
    try:
        number = int(str(value).strip())
    except Exception:
        return None
    return number if number > 0 else None


def infer_group_lesson_span(group):
    for key in ("hours", "lesson_span", "lesson_count"):
        span = parse_positive_int(group.get(key))
        if span is not None:
            return span

    lesson_range = str(group.get("lesson_range") or group.get("unit_lesson_range") or "").strip()
    if lesson_range:
        start = parse_range_start(lesson_range)
        end = parse_range_end(lesson_range)
        if start != 10**9 and end >= start:
            return end - start + 1

    return 1


def format_sequential_lesson_range(start, span):
    span = parse_positive_int(span) or 1
    end = start + span - 1
    if end <= start:
        return str(start)
    return f"{start}~{end}"


LESSON_RANGE_ONLY_RE = re.compile(r"^\s*(\d+)\s*[~∼-]\s*(\d+)\s*$")


def expand_rows_by_lesson_range(rows):
    expanded_rows = []

    for row in rows:
        lesson_text = str(row.get("차시", "")).strip()
        if not lesson_text or ("(" in lesson_text and ")" in lesson_text):
            expanded_rows.append(row)
            continue

        match = LESSON_RANGE_ONLY_RE.fullmatch(lesson_text)
        if not match:
            expanded_rows.append(row)
            continue

        start = int(match.group(1))
        end = int(match.group(2))
        if end <= start:
            expanded_rows.append(row)
            continue

        for lesson_num in range(start, end + 1):
            cloned = dict(row)
            cloned["차시"] = str(lesson_num)
            expanded_rows.append(cloned)

    return expanded_rows


def is_annual_plan_header_or_noise(line):
    return line in ANNUAL_PLAN_HEADER_LINES


def is_annual_plan_lesson_token(line):
    return bool(ANNUAL_PLAN_LESSON_RE.fullmatch(line))


def is_annual_plan_page_range(line):
    return bool(ANNUAL_PLAN_PAGE_RANGE_RE.fullmatch(line))


def is_annual_plan_resource_line(line):
    return any(line.startswith(marker) for marker in ANNUAL_PLAN_RESOURCE_MARKERS)


def join_wrapped_lines(parts):
    return normalize_pdf_line(" ".join(part.strip() for part in parts if part.strip()))


def extract_annual_plan_entries(pdf_path):
    if not pdf_path or not os.path.exists(pdf_path):
        return []

    doc = fitz.open(pdf_path)
    try:
        lines = []
        for page_num in range(len(doc)):
            lines.extend(doc[page_num].get_text().splitlines())
    finally:
        doc.close()

    lines = dedupe_consecutive_lines(lines)
    entries = []
    current_unit_num = None
    current_unit_title = ""
    current_subunit = ""
    i = 0

    while i < len(lines):
        line = lines[i]
        if is_annual_plan_header_or_noise(line):
            i += 1
            continue

        unit_match = ANNUAL_PLAN_UNIT_MARKER_RE.fullmatch(line)
        if unit_match:
            unit_num = int(unit_match.group(1))
            j = i + 1
            title_parts = []
            while j < len(lines):
                candidate = lines[j]
                if (
                    is_annual_plan_header_or_noise(candidate)
                    or ANNUAL_PLAN_UNIT_MARKER_RE.fullmatch(candidate)
                    or ANNUAL_PLAN_THEME_START_RE.fullmatch(candidate)
                    or is_annual_plan_lesson_token(candidate)
                    or is_annual_plan_page_range(candidate)
                ):
                    break
                title_parts.append(candidate)
                j += 1
            if title_parts:
                current_unit_num = unit_num
                current_unit_title = f"{unit_num}. {join_wrapped_lines(title_parts)}"
                current_subunit = ""
            i = j
            continue

        theme_match = ANNUAL_PLAN_THEME_START_RE.fullmatch(line)
        if theme_match:
            j = i + 1
            theme_parts = [theme_match.group(2)]
            while j < len(lines):
                candidate = lines[j]
                if (
                    is_annual_plan_header_or_noise(candidate)
                    or ANNUAL_PLAN_UNIT_MARKER_RE.fullmatch(candidate)
                    or ANNUAL_PLAN_THEME_START_RE.fullmatch(candidate)
                    or is_annual_plan_lesson_token(candidate)
                    or is_annual_plan_page_range(candidate)
                ):
                    break
                theme_parts.append(candidate)
                j += 1
            current_subunit = f"{theme_match.group(1)}. {join_wrapped_lines(theme_parts)}"
            i = j
            continue

        if is_annual_plan_lesson_token(line):
            lesson_range = line.replace("∼", "~")
            j = i + 1
            title_parts = []
            page_range = ""
            suppress_detail = False

            while j < len(lines):
                candidate = lines[j]
                if is_annual_plan_page_range(candidate):
                    page_range = candidate.replace("∼", "~")
                    j += 1
                    break
                if (
                    is_annual_plan_lesson_token(candidate)
                    or ANNUAL_PLAN_UNIT_MARKER_RE.fullmatch(candidate)
                    or ANNUAL_PLAN_THEME_START_RE.fullmatch(candidate)
                ):
                    break
                if is_annual_plan_header_or_noise(candidate):
                    j += 1
                    continue
                if is_annual_plan_resource_line(candidate):
                    suppress_detail = True
                    j += 1
                    continue
                if not suppress_detail:
                    title_parts.append(candidate)
                j += 1

            title = join_wrapped_lines(title_parts)
            if title and current_unit_num is not None:
                entries.append(
                    {
                        "unit_num": current_unit_num,
                        "unit_title": current_unit_title or f"{current_unit_num}단원",
                        "subunit": current_subunit,
                        "lesson_range": lesson_range,
                        "title": title,
                        "textbook_pages": page_range,
                    }
                )
            i = j
            continue

        i += 1

    entries.sort(key=lambda item: (item["unit_num"], parse_range_start(item["lesson_range"])))
    return entries


# ══════════════════════════════════════════════════════════
#  도덕 데이터 생성
# ══════════════════════════════════════════════════════════
MORAL_UNIT_MAP = {
    1: "1. 나를 찾아 떠나는 여행",
    2: "2. 성실하게 사는 삶",
    3: "3. 함께하는 우리 가족",
    4: "4. 인공지능 로봇 연구소에 가요!",
    5: "5. 너와 나의 공감",
    6: "6. 함께 가는 공정의 길",
    7: "7. 생명을 소중히 여기는 우리",
    8: "8. 더 나은 세상을 위한 탐구",
}

# 도덕 PDF 페이지 구조:
# p1: 단원 개요 (설치 취지, 교육과정 내용 요소)
# p2: 단원 구성 표 - 차시별 소제목과 활동 (도입/전개/정리)  
# p3: 단원 학습목표, 주안점, 차시별 요약


def extract_moral_titles(unit_num):
    """도덕 단원의 p2(구성 표)에서 차시별 소제목 추출"""
    pdf_path = find_best_pdf("도덕", unit_num, 1, grade_str="3")
    if not pdf_path or not os.path.exists(pdf_path):
        return {}

    doc = fitz.open(pdf_path)
    titles = {}

    # p2에서 차시별 소제목 찾기
    if len(doc) >= 2:
        text = doc[1].get_text()
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # 패턴: "N차시" 줄 다음에 소제목 + 유형 정보
        for i, line in enumerate(lines):
            m = re.match(r'^(\d)차시$', line)
            if m:
                lesson_num = int(m.group(1))
                # 다음 줄들에서 소제목 찾기 (유형 정보 제외)
                for j in range(i + 1, min(i + 5, len(lines))):
                    candidate = lines[j]
                    # 학습 유형 키워드 건너뛰기
                    if candidate in ('도입', '전개', '정리') or '중심 학습' in candidate:
                        continue
                    if candidate.startswith('•') or candidate.startswith('·'):
                        continue
                    if len(candidate) > 2 and not candidate[0].isdigit():
                        titles[lesson_num] = candidate
                        break

    # p3에서도 시도 (단원의 흐름 섹션)  
    if len(doc) >= 3 and len(titles) < 4:
        text = doc[2].get_text()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for i, line in enumerate(lines):
            m = re.match(r'^(\d)차시$', line)
            if m:
                lesson_num = int(m.group(1))
                if lesson_num not in titles:
                    # 다음 줄에서 bullet point 찾기
                    for j in range(i + 1, min(i + 5, len(lines))):
                        cand = lines[j]
                        if cand.startswith('•') or cand.startswith('·'):
                            cand = cand.lstrip('•·\t ')
                            if len(cand) > 3:
                                titles[lesson_num] = cand[:50]
                                break
                        elif '중심' not in cand and '범주' not in cand and len(cand) > 3:
                            titles[lesson_num] = cand[:50]
                            break

    doc.close()
    return titles


def generate_moral_data():
    """도덕 지도서 PDF 32개 → 32행 데이터 생성"""
    rows = []
    for unit_num in range(1, 9):
        unit_name = MORAL_UNIT_MAP[unit_num]
        titles = extract_moral_titles(unit_num)

        for lesson_num in range(1, 5):
            lesson_pdf_path = find_best_pdf("도덕", unit_num, lesson_num, grade_str="3") or find_best_pdf("도덕", unit_num, None, grade_str="3")
            title = titles.get(lesson_num, f"{unit_name} {lesson_num}차시")
            rows.append({
                "수업내용": title,
                "과목": "도덕",
                "대단원": unit_name,
                "차시": str(lesson_num),
                "계획일": "",
                "실행여부": False,
                "pdf파일": format_pdf_path(lesson_pdf_path),
                "시작페이지": "",
                "끝페이지": "",
                "비고": "",
            })
    return rows


# ══════════════════════════════════════════════════════════
#  국어 데이터 생성
# ══════════════════════════════════════════════════════════
KOREAN_UNIT_NAMES = {
    1: "1. 생생하게 표현해요",
    2: "2. 분명하고 유창하게",
    3: "3. 짜임새 있는 글, 재미와 감동이 있는 글",
    4: "4. 중요한 내용을 알아봐요",
    5: "5. 인물에게 마음을 전해요",
    6: "6. 의견이 있어요",
}

# PDF p3 구조에서 추출한 차시 구조
KOREAN_LESSON_STRUCTURE = {
    1: ["1", "2~5", "6~10", "11~12", "13"],
    2: ["1", "2~6", "7~11", "12~13", "14"],
    3: ["1", "2~5", "6~10", "11~12", "13"],
    4: ["1", "2~5", "6~10", "11~12", "13"],
    5: ["1", "2~6", "7~11", "12~13", "14"],
    6: ["1", "2~6", "7~10", "11~12", "13"],
}

PDF_CONTROL_CHAR_RE = re.compile(r'[\x00-\x1f\u200b\u200c\u200d\ufeff]')
KOREAN_OVERVIEW_RANGE_RE = re.compile(r'^(\d+(?:[~∼]\d+)?)차시$')
KOREAN_NUMBERED_TITLE_RE = re.compile(r'^(\d+)\.\s*(.+)$')
KOREAN_DETAIL_RANGE_RE = re.compile(r'^(\d+(?:[~∼]\d+)?)\s*차시\s*/\s*\d+\s*차시$')


def normalize_pdf_line(text):
    """PDF 추출 과정에서 섞인 제어문자와 줄바꿈 흔적을 정리한다."""
    text = text.replace('\xa0', ' ')
    text = PDF_CONTROL_CHAR_RE.sub('', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def cleanup_korean_title(text):
    """국어 지도서 PDF에서 자주 생기는 단어 중간 띄어쓰기 깨짐을 보정한다."""
    replacements = {
        " 바 르게 ": " 바르게 ",
        " 글 을 ": " 글을 ",
        " 내 어 ": " 내어 ",
        " 말 투": " 말투",
        " 문단 을 ": " 문단을 ",
        " 표현 하기": " 표현하기",
    }
    cleaned = f" {text} "
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    return cleaned.strip()


def normalize_block_text(text):
    return cleanup_korean_title(normalize_pdf_line(" ".join(text.splitlines())))


def parse_lesson_range_key(value):
    m = re.match(r'^(\d+)(?:[~∼](\d+))?$', value)
    if not m:
        return (10**9, 10**9)
    start = int(m.group(1))
    end = int(m.group(2) or m.group(1))
    return (start, end)


def is_korean_overview_break(line):
    if not line:
        return True
    if KOREAN_OVERVIEW_RANGE_RE.match(line):
        return True
    if KOREAN_NUMBERED_TITLE_RE.match(line):
        return True
    if line.startswith(("▶", "●", "•", "소단원")):
        return True
    if line in {"단원의 름", "단원 학습 목표", "평가 예시", "단원 학습", "실천", "준비"}:
        return True
    return False


def extract_numbered_titles(lines):
    """개요 페이지에서 '1. ...', '2. ...' 형식의 소단원 제목을 뽑는다."""
    titles = []
    i = 0

    while i < len(lines):
        m = KOREAN_NUMBERED_TITLE_RE.match(lines[i])
        if not m:
            i += 1
            continue

        title_number = int(m.group(1))
        title_parts = [m.group(2).strip()]
        j = i + 1

        while j < len(lines) and not is_korean_overview_break(lines[j]):
            title_parts.append(lines[j])
            j += 1

        title = cleanup_korean_title(normalize_pdf_line(" ".join(title_parts)))
        if title:
            titles.append((title_number, title))
        i = j

    titles.sort(key=lambda item: item[0])
    return titles


def parse_korean_overview_lines(lines):
    """국어 개요 페이지에서 차시 구조와 차시별 대표 제목을 추출한다."""
    normalized_lines = [normalize_pdf_line(line) for line in lines]
    normalized_lines = [line for line in normalized_lines if line]

    lesson_ranges = []
    seen_ranges = set()
    for line in normalized_lines:
        m = KOREAN_OVERVIEW_RANGE_RE.match(line)
        if not m:
            continue
        lesson_range = m.group(1).replace("∼", "~")
        if lesson_range not in seen_ranges:
            lesson_ranges.append(lesson_range)
            seen_ranges.add(lesson_range)

    lesson_ranges.sort(key=parse_lesson_range_key)

    titles = {}
    if "배울 내용 살펴보기" in normalized_lines:
        titles["1"] = "배울 내용 살펴보기"

    numbered_titles = [title for _, title in extract_numbered_titles(normalized_lines)]
    content_ranges = lesson_ranges[1:-2] if len(lesson_ranges) > 3 else lesson_ranges[1:]
    for lesson_range, title in zip(content_ranges, numbered_titles):
        titles[lesson_range] = title

    if len(lesson_ranges) >= 2 and "배운 내용 실천하기" in normalized_lines:
        titles[lesson_ranges[-2]] = "배운 내용 실천하기"
    if lesson_ranges and "마무리하기" in normalized_lines:
        titles[lesson_ranges[-1]] = "마무리하기"

    return lesson_ranges, titles


def extract_korean_overview(unit_num):
    """국어 지도서 개요 페이지(p3)에서 차시 구조와 대표 제목을 읽어온다."""
    pdf_path = find_best_pdf("국어", unit_num, None, "3-1")
    if not pdf_path or not os.path.exists(pdf_path):
        return [], {}

    doc = fitz.open(pdf_path)
    try:
        if len(doc) < 3:
            return [], {}
        lines = doc[2].get_text().splitlines()
        return parse_korean_overview_lines(lines)
    finally:
        doc.close()


def clean_learning_objective(text):
    text = normalize_block_text(text)
    match = re.search(r'(.+?(?:수 있다\.|안다\.))', text)
    if match:
        text = match.group(1)
    text = re.sub(r'\s*학습 목표$', '', text)
    text = re.sub(r'^학습 목표\s*', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_korean_noise_block(text):
    if not text:
        return True
    if KOREAN_DETAIL_RANGE_RE.match(text):
        return True
    if text.startswith(("『", "수업의 흐름", "동기 유발", "문제 확인하기", "준비 및 연습", "정리")):
        return True
    if text in {"학습 목표", "실", "준", "비"}:
        return True
    if re.fullmatch(r'\d+', text):
        return True
    if "교수·학습의 실제" in text:
        return True
    return False


def extract_korean_lesson_header(normalized_blocks):
    candidates = []
    for block in normalized_blocks:
        text = block["text"]
        if block["y"] > 95 or block["x"] < 40 or block["x"] > 260:
            continue
        if is_korean_noise_block(text):
            continue
        if "학습 목표" in text and clean_learning_objective(text) != text:
            continue
        if len(text) < 4:
            continue
        candidates.append((block["y"], block["x"], text))

    if candidates:
        return min(candidates, key=lambda item: (item[0], item[1]))[2]
    return ""


def parse_korean_detail_page_blocks(blocks, overview_titles=None):
    """상세 차시 페이지의 블록 좌표를 바탕으로 범위/소단원/학습목표를 추출한다."""
    overview_titles = overview_titles or {}

    normalized_blocks = []
    lesson_range = ""
    for x0, y0, _x1, _y1, raw_text, *_rest in blocks:
        text = normalize_block_text(raw_text)
        if not text:
            continue
        normalized_blocks.append({"x": x0, "y": y0, "text": text})
        match = KOREAN_DETAIL_RANGE_RE.match(text)
        if match:
            lesson_range = match.group(1).replace("∼", "~")

    if not lesson_range:
        return None

    objective_candidates = []
    for block in normalized_blocks:
        text = clean_learning_objective(block["text"])
        if block["y"] > 105:
            continue
        if "수 있다" not in text and "안다." not in text:
            continue
        objective_candidates.append((block["y"], block["x"], text))

    objective = ""
    if objective_candidates:
        objective = min(objective_candidates, key=lambda item: (item[0], item[1]))[2]

    lesson_header = extract_korean_lesson_header(normalized_blocks)

    subunit_candidates = []
    for block in normalized_blocks:
        text = block["text"]
        if block["y"] >= 45 or block["x"] < 45 or block["x"] > 260:
            continue
        if is_korean_noise_block(text):
            continue
        subunit_candidates.append((block["y"], block["x"], text))

    subunit = ""
    if subunit_candidates:
        subunit = min(subunit_candidates, key=lambda item: (item[0], item[1]))[2]
    elif lesson_header and lesson_header != objective:
        subunit = lesson_header
    elif overview_titles:
        fallback = overview_titles.get(lesson_range, "")
        if fallback and fallback != objective:
            subunit = fallback

    if not objective:
        objective = lesson_header or overview_titles.get(lesson_range, "")

    return {
        "lesson_range": lesson_range,
        "소단원": subunit,
        "수업내용": objective,
    }


def extract_korean_detail_entries(unit_num, overview_titles=None):
    """국어 지도서 상세 차시 페이지에서 실제 차시 범위별 학습목표를 추출한다."""
    pdf_path = find_best_pdf("국어", unit_num, None, "3-1")
    if not pdf_path or not os.path.exists(pdf_path):
        return {}

    entries = {}
    doc = fitz.open(pdf_path)
    try:
        for page_num in range(len(doc)):
            entry = parse_korean_detail_page_blocks(
                doc[page_num].get_text("blocks"),
                overview_titles=overview_titles,
            )
            if entry:
                entries[entry["lesson_range"]] = {
                    "소단원": entry.get("소단원", ""),
                    "수업내용": entry.get("수업내용", ""),
                }
        return entries
    finally:
        doc.close()


def extract_korean_detail_titles(unit_num):
    """하위 호환용: 상세 차시 페이지에서 범위별 학습목표만 반환한다."""
    entries = extract_korean_detail_entries(unit_num)
    return {
        lesson_range: entry.get("수업내용", "")
        for lesson_range, entry in entries.items()
        if entry.get("수업내용")
    }


def generate_korean_data():
    """국어 지도서 PDF → 진도표 행 생성"""
    rows = []

    # 단원 1~6
    for unit_num in range(1, 7):
        unit_name = KOREAN_UNIT_NAMES[unit_num]
        overview_ranges, overview_titles = extract_korean_overview(unit_num)
        detail_entries = extract_korean_detail_entries(unit_num, overview_titles=overview_titles)

        lesson_ranges = sorted(detail_entries.keys(), key=parse_lesson_range_key)
        if not lesson_ranges:
            lesson_ranges = list(overview_ranges or KOREAN_LESSON_STRUCTURE[unit_num])

        for lr in lesson_ranges:
            detail = detail_entries.get(lr, {})
            title = detail.get("수업내용", "") or overview_titles.get(lr, "") or f"{unit_name} {lr}차시"
            subunit = detail.get("소단원", "")
            if not subunit:
                fallback_subunit = overview_titles.get(lr, "")
                if fallback_subunit and fallback_subunit != title:
                    subunit = fallback_subunit
             
            m = re.match(r'(\d+)[~∼](\d+)', lr)
            if m:
                start = int(m.group(1))
                end = int(m.group(2))
                for i in range(start, end + 1):
                    lesson_pdf_path = find_best_pdf("국어", unit_num, i, "3-1") or find_best_pdf("국어", unit_num, None, "3-1")
                    rows.append({
                        "수업내용": title,
                        "과목": "국어",
                        "대단원": unit_name,
                        "소단원": subunit,
                        "차시": f"{i}({lr})",
                        "계획일": "",
                        "실행여부": False,
                        "pdf파일": format_pdf_path(lesson_pdf_path),
                        "시작페이지": "",
                        "끝페이지": "",
                        "비고": "",
                    })
            else:
                first_lesson = int(re.match(r'^(\d+)', lr).group(1)) if re.match(r'^(\d+)', lr) else None
                lesson_pdf_path = find_best_pdf("국어", unit_num, first_lesson, "3-1") or find_best_pdf("국어", unit_num, None, "3-1")
                rows.append({
                    "수업내용": title,
                    "과목": "국어",
                    "대단원": unit_name,
                    "소단원": subunit,
                    "차시": lr,
                    "계획일": "",
                    "실행여부": False,
                    "pdf파일": format_pdf_path(lesson_pdf_path),
                    "시작페이지": "",
                    "끝페이지": "",
                    "비고": "",
                })

    # 독서 단원 (10차시)
    for i in range(1, 11):
        lesson_pdf_path = find_best_pdf("국어", "독서", i, "3-1") or find_best_pdf("국어", "독서", None, "3-1")
        rows.append({
            "수업내용": f"독서 단원 {i}차시",
            "과목": "국어",
            "대단원": "독서 단원",
            "소단원": "",
            "차시": str(i),
            "계획일": "",
            "실행여부": False,
            "pdf파일": format_pdf_path(lesson_pdf_path),
            "시작페이지": "",
            "끝페이지": "",
            "비고": "",
        })

    # 매체 단원 (10차시)
    for i in range(1, 11):
        lesson_pdf_path = find_best_pdf("국어", "매체", i, "3-1") or find_best_pdf("국어", "매체", None, "3-1")
        rows.append({
            "수업내용": f"매체 단원 {i}차시",
            "과목": "국어",
            "대단원": "매체 단원",
            "소단원": "",
            "차시": str(i),
            "계획일": "",
            "실행여부": False,
            "pdf파일": format_pdf_path(lesson_pdf_path),
            "시작페이지": "",
            "끝페이지": "",
            "비고": "",
        })

    return rows

# ══════════════════════════════════════════════════════════
#  범용 데이터 생성 (정규식 기본 추출)
# ══════════════════════════════════════════════════════════
def extract_heuristic_titles(pdf_path):
    """
    외부 API 없이 PyMuPDF(fitz)의 폰트 크기와 좌표 Heuristics를 분석하여 
    동적으로 대단원/소단원/차시를 유추하는 로컬 파싱 엔진
    """
    if not os.path.exists(pdf_path):
        return {}

    doc = fitz.open(pdf_path)
    titles = {}
    current_subunit = ""
    
    lesson_pattern = re.compile(r'(?:차시|단원|lesson|unit)\s*(\d+)', re.IGNORECASE)
    
    for page_num in range(min(5, len(doc))):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        
        text_spans = []
        for b in blocks:
            if "lines" in b:
                for line in b["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            text_spans.append({
                                "text": text,
                                "size": round(span["size"], 1),
                                "y": span["bbox"][1]
                            })
                            
        if not text_spans:
            continue
            
        sizes = [s["size"] for s in text_spans]
        if not sizes: continue
        max_size = max(sizes)
        
        for i, span in enumerate(text_spans):
            # 먼저 소단원(Subunit)인지 검사 (예: "3-1-1. 우리 마을" 또는 "1. 우리 마을")
            sub_m = re.match(r'^(\d+(?:-\d+)*)[\.\s]+(.*)', span["text"])
            m = lesson_pattern.search(span["text"])
            
            if sub_m and not m and span["size"] >= max_size * 0.7:
                # 이것은 차시가 아니라 소단원 제목임
                current_subunit = span["text"][:50]
                
            lesson_num = None
            if m:
                lesson_num = int(m.group(1))
            # 기존의 "단순 숫자로 시작하면 무조건 차시로 본다"는 fallback을 제거하여
            # 사회의 소단원을 차시로 오해하지 않도록 함.
                    
            if lesson_num and lesson_num not in titles:
                title_cand = span["text"]
                lesson_title = ""
                
                if len(title_cand) < 6 or m:
                    for j in range(i+1, min(i+4, len(text_spans))):
                        cand_span = text_spans[j]
                        if cand_span["size"] >= span["size"] * 0.8: 
                            cand_text = cand_span["text"].lstrip('•·\t ')
                            if len(cand_text) > 2 and not cand_text.isdigit():
                                lesson_title = cand_text[:50]
                                break
                else:
                    lesson_title = re.sub(r'^\d+[\.\s]*', '', title_cand)[:50]
                    
                titles[lesson_num] = {
                    "title": lesson_title,
                    "subunit": current_subunit
                }

    doc.close()
    return titles


def build_rows_from_annual_plan(subject_name, prefix, grade_str="3-1"):
    annual_plan_pdf = find_annual_plan_pdf(prefix, grade_str)
    entries = extract_annual_plan_entries(annual_plan_pdf)
    if not entries:
        return []

    rows = []
    unit_start_by_number = {}
    for entry in entries:
        unit_num = entry.get("unit_num")
        if unit_num not in unit_start_by_number:
            unit_start_by_number[unit_num] = parse_range_start(entry["lesson_range"])
        unit_lesson_range = normalize_unit_lesson_range(
            entry["lesson_range"],
            unit_start_by_number.get(unit_num),
        )
        lesson_pdf_path = (
            find_best_pdf(prefix, entry["unit_num"], entry["lesson_range"], grade_str, lesson_title=entry["title"])
            or find_best_pdf(prefix, entry["unit_num"], None, grade_str, lesson_title=entry["title"])
        )
        rows.append(
            {
                "수업내용": entry["title"],
                "과목": subject_name,
                "대단원": entry["unit_title"],
                "소단원": entry["subunit"],
                "차시": unit_lesson_range,
                "계획일": "",
                "실행여부": False,
                "pdf파일": format_pdf_path(lesson_pdf_path),
                "시작페이지": "",
                "끝페이지": "",
                "비고": "",
            }
        )
    return rows


def collect_split_group_runs(subject_prefix, grade_str="3-1", search_dirs=None):
    search_dirs = search_dirs or GUIDE_SEARCH_DIRS
    normalized_subject = normalize_search_text(subject_prefix)
    grade_tokens = build_grade_search_tokens(grade_str)
    best_by_source = {}

    for base_dir in search_dirs:
        if not base_dir:
            continue
        root = Path(base_dir)
        if not root.exists():
            continue

        for groups_path in root.rglob("groups.json"):
            try:
                data = json.loads(groups_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            groups = data.get("groups", [])
            if data.get("split_level") != "detail" or not groups:
                continue

            pdf_dir = groups_path.parent / "pdf_splits"
            if not pdf_dir.exists():
                continue

            source_name = str(data.get("pdf") or groups_path.parent.name)
            subject_haystack = normalize_search_text(f"{groups_path} {source_name}")
            if normalized_subject and normalized_subject not in subject_haystack:
                continue

            grade_haystack = build_split_run_search_text(groups_path, source_name, data)
            grade_matched = not grade_tokens or any(token in grade_haystack for token in grade_tokens)

            source_key = normalize_search_text(source_name)
            candidate = {
                "groups_path": groups_path,
                "pdf_dir": pdf_dir,
                "source_name": source_name,
                "groups": groups,
                "grade_matched": grade_matched,
            }
            existing = best_by_source.get(source_key)
            if (
                existing is None
                or (grade_matched and not existing["grade_matched"])
                or (
                    grade_matched == existing["grade_matched"]
                    and len(groups) > len(existing["groups"])
                )
            ):
                best_by_source[source_key] = candidate

    candidates = list(best_by_source.values())
    if any(candidate["grade_matched"] for candidate in candidates):
        candidates = [candidate for candidate in candidates if candidate["grade_matched"]]

    return sorted(
        candidates,
        key=lambda item: normalize_search_text(item["source_name"]),
    )


def find_split_pdf_for_group(pdf_dir, group):
    group_index = group.get("index")
    start_page = group.get("start_page")
    end_page = group.get("end_page")

    patterns = []
    if isinstance(group_index, int) and start_page and end_page:
        patterns.append(f"*subunit_{group_index:02d}_*_p{start_page}-{end_page}.pdf")
    if isinstance(group_index, int):
        patterns.append(f"*subunit_{group_index:02d}_*.pdf")
    if start_page and end_page:
        patterns.append(f"*_p{start_page}-{end_page}.pdf")

    for pattern in patterns:
        matches = sorted(pdf_dir.glob(pattern))
        if matches:
            return str(matches[0].resolve())

    title_tokens = extract_title_match_tokens(group.get("title", ""))
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        full_path = normalize_search_text(str(pdf))
        if start_page and end_page and f"p{start_page}{end_page}" not in normalize_search_text(pdf.name):
            continue
        if all(token in full_path for token in title_tokens[:2]):
            return str(pdf.resolve())

    return ""


def title_alignment_score(left_title, right_title):
    left_normalized = normalize_search_text(left_title)
    right_normalized = normalize_search_text(right_title)
    if left_normalized and right_normalized and (
        left_normalized in right_normalized or right_normalized in left_normalized
    ):
        return 0.6

    left_tokens = set(extract_title_match_tokens(left_title))
    right_tokens = set(extract_title_match_tokens(right_title))
    if not left_tokens or not right_tokens:
        return 1.0 if left_normalized == right_normalized and left_normalized else 0.0

    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def should_merge_annual_and_split_rows(annual_plan_rows, split_rows):
    if not annual_plan_rows or not split_rows or len(annual_plan_rows) != len(split_rows):
        return False

    split_generic_units = sum(
        1 for row in split_rows if GENERIC_UNIT_LABEL_RE.match(str(row.get("대단원", "")).strip())
    )
    annual_specific_units = sum(
        1 for row in annual_plan_rows if row.get("대단원") and not GENERIC_UNIT_LABEL_RE.match(str(row.get("대단원", "")).strip())
    )
    if split_generic_units == 0 or annual_specific_units == 0:
        return False

    scores = [
        title_alignment_score(split_row.get("수업내용", ""), annual_row.get("수업내용", ""))
        for split_row, annual_row in zip(split_rows, annual_plan_rows)
    ]
    strong_matches = sum(score >= 0.2 for score in scores)
    required_matches = 1 if len(scores) <= 3 else max(3, len(scores) // 3)
    return (sum(scores) / len(scores)) >= 0.2 and strong_matches >= required_matches


def merge_annual_and_split_rows(annual_plan_rows, split_rows):
    merged_rows = []
    for annual_row, split_row in zip(annual_plan_rows, split_rows):
        merged = dict(annual_row)
        for key in ("pdf파일", "시작페이지", "끝페이지", "비고"):
            if split_row.get(key):
                merged[key] = split_row.get(key)
        if not merged.get("소단원") and split_row.get("소단원"):
            merged["소단원"] = split_row.get("소단원")
        merged_rows.append(merged)
    return merged_rows


def infer_math_unit_title(unit_titles):
    joined = " ".join(unit_titles)
    if any(keyword in joined for keyword in ("분수", "소수")):
        return "분수와 소수"
    if any(keyword in joined for keyword in ("cm보다", "m보다", "분보다", "길이", "시간은")):
        return "길이와 시간"
    if any(keyword in joined for keyword in ("나눗셈", "나누어 볼까요")):
        return "나눗셈"
    if any(keyword in joined for keyword in ("선의 종류", "각을", "직각", "직사각형", "정사각형")):
        return "평면도형"
    if any(keyword in joined for keyword in ("덧셈", "뺄셈")):
        return "덧셈과 뺄셈"
    if any(keyword in joined for keyword in ("곱셈", "(몇십)", "(몇십몇)")):
        return "곱셈"
    return ""


def infer_split_unit_labels(subject_name, groups):
    if subject_name != "수학":
        return {}

    labels = {}
    current_titles = []
    unit_index = 0

    for group in groups:
        title = normalize_pdf_line(str(group.get("title", "")))
        if not title:
            continue
        if title == "단원 도입":
            if current_titles:
                labels[unit_index] = infer_math_unit_title(current_titles)
            unit_index += 1
            current_titles = []
            continue
        current_titles.append(title)

    if current_titles and unit_index:
        labels[unit_index] = infer_math_unit_title(current_titles)

    return labels


def build_rows_from_split_groups(subject_name, prefix, grade_str="3-1"):
    runs = collect_split_group_runs(prefix, grade_str=grade_str)
    if not runs:
        return []

    rows = []

    for run in runs:
        groups = sorted(
            (
                group
                for group in run["groups"]
                if is_schedule_content_group(group)
            ),
            key=lambda item: (
                int(item.get("index", 10**9)),
                int(item.get("start_page", 10**9)),
                normalize_pdf_line(str(item.get("title", ""))),
            ),
        )
        if not groups:
            continue

        inferred_unit_titles = infer_split_unit_labels(subject_name, groups)
        current_unit_title = ""
        inferred_unit_index = 0
        unit_lesson_counter = 0
        last_unit_label = None
        source_label = normalize_pdf_line(Path(run["source_name"]).stem)

        for group in groups:
            title = normalize_pdf_line(str(group.get("title", "")))
            if not title:
                continue

            parent_unit_title = normalize_pdf_line(str(group.get("parent_unit_title", "")))
            context_values = group.get("context") or []
            context_title = normalize_pdf_line(str(context_values[0])) if context_values else ""

            if parent_unit_title:
                current_unit_title = parent_unit_title
            elif title == "단원 도입":
                inferred_unit_index += 1
                inferred_unit_title = inferred_unit_titles.get(inferred_unit_index, "").strip()
                if inferred_unit_title:
                    current_unit_title = f"{inferred_unit_index}단원 {inferred_unit_title}"
                else:
                    current_unit_title = f"{inferred_unit_index}단원"

            unit_label = current_unit_title or source_label
            if unit_label != last_unit_label:
                unit_lesson_counter = 0
                last_unit_label = unit_label

            lesson_span = infer_group_lesson_span(group)
            lesson_range = format_sequential_lesson_range(unit_lesson_counter + 1, lesson_span)
            unit_lesson_counter += lesson_span
            lesson_pdf_path = find_split_pdf_for_group(run["pdf_dir"], group)

            rows.append(
                {
                    "수업내용": title,
                    "과목": subject_name,
                    "대단원": unit_label,
                    "소단원": context_title,
                    "차시": lesson_range,
                    "계획일": "",
                    "실행여부": False,
                    "pdf파일": format_pdf_path(lesson_pdf_path),
                    "시작페이지": group.get("start_page", ""),
                    "끝페이지": group.get("end_page", ""),
                    "비고": source_label if len(runs) > 1 else "",
                }
            )

    return rows


def generate_general_data(subject_name, prefix, max_unit=5, disable_heuristic=False, grade_str="3-1"):
    split_rows = build_rows_from_split_groups(subject_name, prefix, grade_str=grade_str)
    annual_plan_rows = build_rows_from_annual_plan(subject_name, prefix, grade_str=grade_str)
    if should_merge_annual_and_split_rows(annual_plan_rows, split_rows):
        return expand_rows_by_lesson_range(merge_annual_and_split_rows(annual_plan_rows, split_rows))
    if split_rows and (not annual_plan_rows or len(split_rows) > len(annual_plan_rows)):
        return expand_rows_by_lesson_range(split_rows)
    if annual_plan_rows:
        return expand_rows_by_lesson_range(annual_plan_rows)
    if split_rows:
        return expand_rows_by_lesson_range(split_rows)

    rows = []
    
    for unit_num in range(1, max_unit + 1):
        pdf_path = find_best_pdf(prefix, unit_num, None, grade_str)
                
        if disable_heuristic:
            titles = {}
            max_lessons = 15
        else:
            titles = extract_heuristic_titles(pdf_path) if pdf_path else {}
            max_lessons = max(titles.keys()) if titles else 3
            
        unit_name = f"{unit_num}단원"
        
        for lesson_num in range(1, max_lessons + 1):
            lesson_pdf_path = find_best_pdf(prefix, unit_num, lesson_num, grade_str) or pdf_path
            
            lesson_info = titles.get(lesson_num, {})
            if isinstance(lesson_info, str):
                title = lesson_info
                subunit = ""
            else:
                title = lesson_info.get("title", f"{unit_name} {lesson_num}차시") if lesson_info.get("title") else f"{unit_name} {lesson_num}차시"
                subunit = lesson_info.get("subunit", "")
                
            rows.append({
                "수업내용": title,
                "과목": subject_name,
                "대단원": unit_name,
                "소단원": subunit,
                "차시": str(lesson_num),
                "계획일": "",
                "실행여부": False,
                "pdf파일": format_pdf_path(lesson_pdf_path),
                "시작페이지": "",
                "끝페이지": "",
                "비고": "",
            })
            
    return expand_rows_by_lesson_range(rows)



# ══════════════════════════════════════════════════════════
#  중복 행 삭제
# ══════════════════════════════════════════════════════════
def find_duplicate_rows(ws):
    """중복 행 탐색 (같은 과목+차시+수업내용+대단원)"""
    records = ws.get_all_records(default_blank="")
    seen = {}
    duplicates = []
    for i, r in enumerate(records, start=2):
        key = (r.get("과목", ""), str(r.get("차시", "")), r.get("수업내용", ""), r.get("대단원", ""))
        if key[0]:
            if key in seen:
                duplicates.append(i)
            else:
                seen[key] = i
    return duplicates


def delete_duplicate_rows(ws):
    """중복 행 삭제 (뒤에서부터)"""
    dups = find_duplicate_rows(ws)
    if not dups:
        print("  중복 행이 없습니다.")
        return 0
    print(f"  중복 행 {len(dups)}개 발견: {dups}")
    for row_num in sorted(dups, reverse=True):
        ws.delete_rows(row_num)
        print(f"    행 {row_num} 삭제됨")
    return len(dups)


def build_row_for_headers(headers, record):
    row = []
    for index, header in enumerate(headers, start=1):
        normalized_header = str(header).strip()
        if normalized_header:
            row.append(record.get(normalized_header, ""))
        elif index == DONE_COLUMN_FALLBACK_INDEX:
            row.append(record.get(DONE_COLUMN_NAME, False))
        else:
            row.append("")
    return row


# ══════════════════════════════════════════════════════════
#  메인
# ══════════════════════════════════════════════════════════
get_sheet = shared_get_sheet
delete_duplicate_rows = shared_delete_duplicate_rows
build_row_for_headers = shared_build_row_for_headers


def main():
    parser = argparse.ArgumentParser(description="국어/도덕 지도서 PDF → 진도표 구글시트 매핑")
    parser.add_argument("--upload", action="store_true", help="실제 구글 시트에 업로드")
    parser.add_argument("--cleanup", action="store_true", help="중복 행 삭제 포함")
    parser.add_argument("--replace-subjects", action="store_true", help="업로드할 과목의 기존 행을 지우고 업로드")
    parser.add_argument("--replace-all", action="store_true", help="진도표의 기존 행 전체를 지우고 업로드")
    args = parser.parse_args()

    if args.replace_subjects and args.replace_all:
        parser.error("--replace-subjects와 --replace-all은 같이 사용할 수 없습니다.")

    print("=" * 60)
    print("  📚 국어/도덕 지도서 → 진도표 매핑 스크립트")
    print("=" * 60)

    # 1. 국어 데이터 생성
    print("\n[1/2] 국어 데이터 생성 중...")
    korean_rows = generate_korean_data()
    print(f"  국어 {len(korean_rows)}행 생성됨")
    for r in korean_rows:
        print(f"    {r['과목']} | {r['대단원'][:25]:<25} | {r['차시']:<5} | {r['수업내용'][:40]}")

    # 2. 도덕 데이터 생성
    print(f"\n[2/2] 도덕 데이터 생성 중...")
    moral_rows = generate_moral_data()
    print(f"  도덕 {len(moral_rows)}행 생성됨")
    for r in moral_rows:
        print(f"    {r['과목']} | {r['대단원'][:25]:<25} | {r['차시']:<5} | {r['수업내용'][:40]}")

    all_rows = korean_rows + moral_rows

    if not args.upload and not args.cleanup:
        print(f"\n[미리보기 모드] 총 {len(all_rows)}행.")
        print("  실제 업로드:      python map_guides_to_sheet.py --upload")
        print("  과목만 교체 업로드: python map_guides_to_sheet.py --upload --replace-subjects")
        print("  전체 교체 업로드:   python map_guides_to_sheet.py --upload --replace-all")
        print("  중복삭제+업로드:  python map_guides_to_sheet.py --upload --cleanup")
        return

    print("\n[업로드] 구글 시트 연결 중...")
    replace_mode = REPLACE_APPEND
    if args.replace_all:
        replace_mode = REPLACE_ALL
    elif args.replace_subjects:
        replace_mode = REPLACE_SUBJECTS
    upload_rows_to_sheet(all_rows, cleanup=args.cleanup, replace_mode=replace_mode)
    print("\n[?꾨즺] 援ш? ?쒗듃瑜??뺤씤??二쇱꽭??")
    return

    sh, ws = get_sheet()
    headers = ws.row_values(1)
    print(f"  헤더: {headers}")

    if args.cleanup:
        print("\n  [중복 삭제 중...]")
        deleted = delete_duplicate_rows(ws)
        print(f"  {deleted}개 중복 행 삭제됨")

    # 기존 데이터의 마지막 행 찾기
    existing = ws.get_all_values()
    last_row = len(existing)
    print(f"  현재 마지막 행: {last_row}")

    # 새 데이터를 시트 헤더 순서에 맞춰 변환
    new_rows = []
    for r in all_rows:
        new_rows.append(build_row_for_headers(headers, r))

    # 일괄 추가
    if new_rows:
        ws.append_rows(new_rows, value_input_option="USER_ENTERED")
        print(f"\n  ✅ {len(new_rows)}행 업로드 완료!")

    print("\n[완료] 구글 시트를 확인해 주세요.")


if __name__ == "__main__":
    main()
