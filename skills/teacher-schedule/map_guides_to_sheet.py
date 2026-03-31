"""
지도서 PDF 파일들에서 차시 정보를 추출하여 구글 시트 진도표에 업로드하는 스크립트.

사용법:
  python map_guides_to_sheet.py              # dry-run (미리보기)
  python map_guides_to_sheet.py --upload      # 실제 업로드
  python map_guides_to_sheet.py --cleanup     # 중복행 삭제 후 업로드
"""
import os
import sys
import json
import re
import io
import argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── 환경 설정 ──────────────────────────────────────────────
SCHEDULE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCHEDULE_DIR)
from dotenv import load_dotenv
load_dotenv(os.path.join(SCHEDULE_DIR, ".env"))

import gspread
from google.oauth2.service_account import Credentials
import fitz  # pymupdf

SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME", "시트1")
GUIDE_DIR = r"D:\지도서"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
DONE_COLUMN_NAME = "실행여부"
DONE_COLUMN_FALLBACK_INDEX = 6


# ── 구글 시트 연결 ───────────────────────────────────────────
def get_sheet():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON").replace("\\n", "\n")
    creds = Credentials.from_service_account_info(
        json.loads(creds_json, strict=False), scopes=SCOPES
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    return sh, sh.worksheet(SHEET_NAME)


from pathlib import Path

def find_best_pdf(subject_prefix, unit_num, lesson_num=None, grade_str="3-1"):
    search_path = Path(GUIDE_DIR)
    if not search_path.exists():
        return None
        
    all_pdfs = list(search_path.rglob(f"*{subject_prefix}*.pdf"))
    if not all_pdfs:
        return None
        
    best_pdf = None
    best_score = -1
    
    for pdf in all_pdfs:
        name = pdf.name.replace(" ", "")
        score = 0
        
        if subject_prefix in name:
            score += 1
            
        lesson_match = False
        if lesson_num is not None:
            l_str = str(lesson_num)
            if f"{l_str}차시" in name or f"_{l_str}.pdf" in name or f"-{l_str}.pdf" in name or f"_{l_str}_" in name:
                score += 20
                lesson_match = True
                
        unit_match = False
        u_str = str(unit_num)
        if f"{u_str}단원" in name or f"_{u_str}_" in name or f"-{u_str}_" in name or f"_{u_str}." in name:
            score += 10
            unit_match = True
        elif isinstance(unit_num, str) and unit_num in name:
            score += 10
            unit_match = True
            
        if grade_str and grade_str in name:
            score += 5
            
            # 일반 통권 지도서 파일은 조각 파일(Split)보다 우선순위를 대폭 낮춥니다.
            # 이로써 아무리 이름이 부실한 조각 파일이더라도 원본 파일보다 우선적으로 매칭됩니다.
            is_original = "지도서" in name and "subunit_" not in name and "pdf_splits" not in str(pdf)
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
    pdf_path = os.path.join(GUIDE_DIR, f"도덕3_{unit_num}_1_지도서.pdf")
    if not os.path.exists(pdf_path):
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
            lesson_pdf_path = find_best_pdf("도덕", unit_num, lesson_num) or find_best_pdf("도덕", unit_num, None)
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
    elif overview_titles:
        fallback = overview_titles.get(lesson_range, "")
        if fallback and fallback != objective:
            subunit = fallback

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


def generate_general_data(subject_name, prefix, max_unit=5, disable_heuristic=False, grade_str="3-1"):
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
            
    return rows



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
def main():
    parser = argparse.ArgumentParser(description="지도서 PDF → 진도표 구글시트 매핑")
    parser.add_argument("--upload", action="store_true", help="실제 구글 시트에 업로드")
    parser.add_argument("--cleanup", action="store_true", help="중복 행 삭제 포함")
    args = parser.parse_args()

    print("=" * 60)
    print("  📚 지도서 → 진도표 매핑 스크립트")
    print("=" * 60)

    # 1. 국어 데이터 생성
    print("\n[1/3] 국어 데이터 생성 중...")
    korean_rows = generate_korean_data()
    print(f"  국어 {len(korean_rows)}행 생성됨")
    for r in korean_rows:
        print(f"    {r['과목']} | {r['대단원'][:25]:<25} | {r['차시']:<5} | {r['수업내용'][:40]}")

    # 2. 도덕 데이터 생성
    print(f"\n[2/3] 도덕 데이터 생성 중...")
    moral_rows = generate_moral_data()
    print(f"  도덕 {len(moral_rows)}행 생성됨")
    for r in moral_rows:
        print(f"    {r['과목']} | {r['대단원'][:25]:<25} | {r['차시']:<5} | {r['수업내용'][:40]}")

    # 3. 범용 과목 데이터 생성 (전 과목 지원)
    print(f"\n[3/3] 범용 데이터 생성 중 (수학, 사회, 과학, 음악, 미술, 체육, 영어, 실과)...")
    # prefix는 오로지 '과목' 기명으로 유지하여 어떠한 파일명 포맷이든 전부 스캔(rglob)되게 합니다.
    # 대신 grade_str 인자를 넘겨서 구체적인 학년 점수(score)를 채점합니다.
    math_rows = generate_general_data("수학", "수학", max_unit=6, grade_str="3-1")
    social_rows = generate_general_data("사회", "사회", max_unit=4, disable_heuristic=True, grade_str="3-1")
    science_rows = generate_general_data("과학", "과학", max_unit=5, grade_str="3-1")
    music_rows = generate_general_data("음악", "음악", max_unit=8, grade_str="3")
    art_rows = generate_general_data("미술", "미술", max_unit=8, grade_str="3")
    pe_rows = generate_general_data("체육", "체육", max_unit=5, grade_str="3")
    english_rows = generate_general_data("영어", "영어", max_unit=11, grade_str="3")
    prac_rows = generate_general_data("실과", "실과", max_unit=6, grade_str="5")
    
    general_rows = math_rows + social_rows + science_rows + music_rows + art_rows + pe_rows + english_rows + prac_rows
    print(f"  기타 {len(general_rows)}행 생성됨")

    all_rows = korean_rows + moral_rows + general_rows

    if not args.upload and not args.cleanup:
        print(f"\n[미리보기 모드] 총 {len(all_rows)}행.")
        print("  실제 업로드:      python map_guides_to_sheet.py --upload")
        print("  중복삭제+업로드:  python map_guides_to_sheet.py --upload --cleanup")
        return

    # 3. 구글 시트 연결 및 업로드
    print("\n[3/3] 구글 시트 연결 중...")
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
