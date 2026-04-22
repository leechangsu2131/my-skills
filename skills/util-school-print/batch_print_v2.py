"""
학교 전체 안내장 반별 자동 인쇄 (간지 자동 삽입 버전)
=========================================================
동작 흐름:
  ┌─────────────────────────────────────┐
  │ [간지] 3학년 1반 · 17명             │ ← 간지.hwpx 템플릿에서 자동 생성
  │  안내장 × 17장                       │
  │ [간지] 3학년 2반 · 18명             │
  │  안내장 × 18장                       │
  │  ...                                 │
  └─────────────────────────────────────┘
  → 교대 배출 없이도 간지만으로 반 구분 가능
  → 교대 배출까지 켜면 뭉치 경계가 더 명확

준비물:
  - Python 3.8+  (Windows 전용)
  - pip install pywin32 openpyxl
  - 한글 오피스 설치
  - 간지 템플릿 HWPX (SEPARATOR_TEMPLATE 경로)
  - 엑셀 명렬표 (학년/반/학생수 컬럼)

간지 템플릿 만들기:
  한글에서 새 문서 → 아래 두 줄만 크게 작성 후 HWPX 저장
  ─────────────────────────────
  {{학년}}학년 {{반}}반
  총 {{학생수}}명
  ─────────────────────────────
  (폰트 크기를 키워두면 한눈에 잘 보임)
"""

import csv
import re
import sys
import time
import logging
import zipfile
import tempfile
from io import StringIO
from urllib.request import urlopen
from pathlib import Path

# ─────────────────────────────────────────
#  ★ 여기만 수정하세요 ★
# ─────────────────────────────────────────

HWPX_FILE          = r"C:\Users\user\hwpprint\안내장.hwpx"
EXCEL_FILE         = r"C:\Users\user\hwpprint\학생명렬표.xlsx"
SEPARATOR_TEMPLATE = r"C:\Users\user\hwpprint\간지_템플릿.hwpx"  # 아래 설명 참고

# Google Sheets를 API 없이 읽고 싶다면 아래 CSV URL 사용:
#   1) 시트 공유를 "링크가 있는 사용자(뷰어)"로 설정
#   2) 시트 ID / gid를 넣어 CSV export URL 지정
# 예) https://docs.google.com/spreadsheets/d/<SHEET_ID>/export?format=csv&gid=<GID>
GOOGLE_SHEET_CSV_URL = ""   # 비워두면 EXCEL_FILE 사용

SHEET_NAME  = "Sheet1"
COL_GRADE   = "학년"
COL_CLASS   = "반"
COL_COUNT   = "학생수"

PRINTER_NAME = ""        # 비워두면 기본 프린터 / 예: "Fuji Apeos C2561 PCL6"
JOB_DELAY    = 3         # 인쇄 Job 사이 대기(초)
DRY_RUN      = False     # True → 실제 인쇄 없이 목록만 출력

# ─────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# 간지 HWPX 동적 생성
# ──────────────────────────────────────────────────────────

def make_separator_hwpx(template_path: str, grade: int, cls: int, count: int) -> str:
    """
    템플릿 HWPX의 {{학년}} {{반}} {{학생수}} 플레이스홀더를
    실제 값으로 교체한 임시 HWPX 파일을 생성하여 경로 반환.
    HWPX는 ZIP이므로 내부 XML을 직접 수정.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".hwpx", delete=False)
    tmp.close()
    tmp_path = tmp.name

    replacements = {
        "{{학년}}": str(grade),
        "{{반}}": str(cls),
        "{{학생수}}": str(count),
        # 혹시 띄어쓰기 변형이 있을 경우를 위한 대체 패턴
        "{{ 학년 }}": str(grade),
        "{{ 반 }}": str(cls),
        "{{ 학생수 }}": str(count),
    }

    with zipfile.ZipFile(template_path, "r") as zin, \
         zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:

        # mimetype은 ZIP_STORED + 첫 번째 엔트리 (HWPX 규격)
        if "mimetype" in zin.namelist():
            zout.writestr(
                zipfile.ZipInfo("mimetype"),  # compression 기본값 = STORED
                zin.read("mimetype")
            )

        for item in zin.infolist():
            if item.filename == "mimetype":
                continue  # 이미 처리함

            data = zin.read(item.filename)

            # XML 파일만 텍스트 치환
            if item.filename.endswith((".xml", ".hpf", ".rels")):
                text = data.decode("utf-8", errors="replace")
                for old, new in replacements.items():
                    text = text.replace(old, new)
                data = text.encode("utf-8")

            zout.writestr(item, data)

    return tmp_path


# ──────────────────────────────────────────────────────────
# 엑셀 로드
# ──────────────────────────────────────────────────────────

def _normalize_header(value: str) -> str:
    return str(value).replace(" ", "").strip()


def _build_class_row(grade, cls, count) -> dict:
    return {
        "grade": int(grade),
        "cls": int(cls),
        "count": int(count),
        "label": f"{int(grade)}학년 {int(cls)}반",
    }


def _parse_rows_with_headers(rows: list[list]) -> list[dict]:
    if not rows:
        return []

    headers = [str(v).strip() if v is not None else "" for v in rows[0]]
    norm_headers = [_normalize_header(h) for h in headers]

    try:
        gi = norm_headers.index(_normalize_header(COL_GRADE))
        ci = norm_headers.index(_normalize_header(COL_CLASS))
        ni = norm_headers.index(_normalize_header(COL_COUNT))
    except ValueError as e:
        raise ValueError(f"컬럼 없음: {e}  실제 컬럼: {headers}") from e

    classes = []
    for row in rows[1:]:
        if ni >= len(row) or row[ni] in (None, ""):
            continue
        classes.append(_build_class_row(row[gi], row[ci], row[ni]))
    return classes


def _extract_grade_class_count_from_grid(rows: list[list[str]]) -> list[dict]:
    """
    헤더형 테이블이 아닐 때, 셀 전체에서 '1학년', '2반', 숫자 조합을 찾아
    학년/반/학생수를 추출하는 보조 파서.
    """
    classes = []
    pattern_grade = re.compile(r"^\s*(\d+)\s*학년\s*$")
    pattern_class = re.compile(r"^\s*(\d+)\s*반\s*$")
    pattern_number = re.compile(r"^\s*(\d+)\s*$")

    for row in rows:
        values = [str(v).strip() for v in row if v not in (None, "")]
        if len(values) < 3:
            continue
        for i in range(len(values) - 2):
            m_grade = pattern_grade.match(values[i])
            m_class = pattern_class.match(values[i + 1])
            m_count = pattern_number.match(values[i + 2])
            if m_grade and m_class and m_count:
                classes.append(
                    _build_class_row(
                        int(m_grade.group(1)),
                        int(m_class.group(1)),
                        int(m_count.group(1)),
                    )
                )

    dedup = {}
    for c in classes:
        dedup[(c["grade"], c["cls"])] = c
    return [dedup[k] for k in sorted(dedup.keys())]


def load_class_list_from_excel(excel_path: str, sheet: str) -> list[dict]:
    try:
        import openpyxl
    except ImportError:
        sys.exit("❌ openpyxl 없음 → pip install openpyxl")

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb[sheet] if sheet in wb.sheetnames else wb.active

    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    try:
        return _parse_rows_with_headers(rows)
    except ValueError:
        # 학교 시트처럼 구조가 복잡한 경우를 대비해 전체 셀에서 패턴 추출
        parsed = _extract_grade_class_count_from_grid(rows)
        if parsed:
            return parsed
        raise


def load_class_list_from_google_csv(csv_url: str) -> list[dict]:
    with urlopen(csv_url, timeout=15) as response:
        text = response.read().decode("utf-8-sig", errors="replace")

    rows = list(csv.reader(StringIO(text)))
    try:
        return _parse_rows_with_headers(rows)
    except ValueError:
        parsed = _extract_grade_class_count_from_grid(rows)
        if parsed:
            return parsed
        raise


# ──────────────────────────────────────────────────────────
# HWP OLE 헬퍼
# ──────────────────────────────────────────────────────────

def get_hwp():
    try:
        import win32com.client
    except ImportError:
        sys.exit("❌ pywin32 없음 → pip install pywin32")

    try:
        hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
        try:
            hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
        except Exception:
            pass
        return hwp
    except Exception as e:
        sys.exit(f"❌ 한글 OLE 연결 실패: {e}")


def print_hwpx(hwp, file_path: str, copies: int, printer: str) -> bool:
    """지정 HWPX 파일을 열고 copies매 인쇄 후 닫음"""
    try:
        hwp.Open(file_path, "HWPX", "forceopen:true")
        time.sleep(0.5)  # 파일 열기 안정화 대기

        act  = hwp.HAction
        pset = hwp.HParameterSet.HPrint
        act.GetDefault("Print", pset.HSet)
        pset.Copies = copies
        if printer:
            pset.PrinterName = printer
        result = act.Execute("Print", pset.HSet)

        hwp.Clear(1)  # 문서 닫기 (저장 안 함)
        return bool(result)
    except Exception as e:
        log.error(f"  인쇄 오류: {e}")
        return False


# ──────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────

def main():
    # 파일 확인
    for path, label in [
        (HWPX_FILE,          "안내장 HWPX"),
        (SEPARATOR_TEMPLATE, "간지 템플릿 HWPX"),
    ]:
        if not Path(path).exists():
            sys.exit(f"❌ {label} 파일 없음: {path}")

    if not GOOGLE_SHEET_CSV_URL and not Path(EXCEL_FILE).exists():
        sys.exit(f"❌ 학생 명렬표 엑셀 파일 없음: {EXCEL_FILE}")

    classes = []
    if GOOGLE_SHEET_CSV_URL:
        log.info("Google Sheets(CSV)에서 반 데이터 로드 시도...")
        try:
            classes = load_class_list_from_google_csv(GOOGLE_SHEET_CSV_URL)
            log.info("Google Sheets 로드 성공")
        except Exception as e:
            log.warning(f"Google Sheets 로드 실패: {e}")
            if Path(EXCEL_FILE).exists():
                log.info("로컬 엑셀 파일로 대체 로드 시도...")
                classes = load_class_list_from_excel(EXCEL_FILE, SHEET_NAME)
            else:
                sys.exit("❌ Google Sheets/엑셀 모두 로드 실패")
    else:
        classes = load_class_list_from_excel(EXCEL_FILE, SHEET_NAME)
    if not classes:
        sys.exit("❌ 엑셀에서 반 데이터를 읽지 못했습니다.")

    total = sum(c["count"] for c in classes)
    log.info(f"총 {len(classes)}개 반 / 전체 {total}매 (+ 간지 {len(classes)}장) 예정")
    print()

    # DRY RUN
    if DRY_RUN:
        print("[DRY RUN] 실제 인쇄 안 함 — 인쇄 순서 미리보기:")
        for c in classes:
            print(f"  [간지] {c['label']} · {c['count']}명")
            print(f"   안내장 × {c['count']}장")
        print(f"\n총 {total + len(classes)}장 (안내장 {total} + 간지 {len(classes)})")
        return

    # 한글 OLE 기동
    log.info("한글 OLE 기동 중...")
    hwp = get_hwp()
    printer_label = PRINTER_NAME or "(기본 프린터)"
    log.info(f"프린터: {printer_label}")
    print()

    tmp_files = []  # 인쇄 후 삭제할 임시 파일 목록

    try:
        for i, cls in enumerate(classes, 1):
            label = cls["label"]
            count = cls["count"]
            log.info(f"─── [{i}/{len(classes)}] {label} ({count}명) ───")

            # ① 간지 생성 및 인쇄
            log.info(f"  간지 생성 중...")
            sep_path = make_separator_hwpx(
                SEPARATOR_TEMPLATE,
                cls["grade"], cls["cls"], count
            )
            tmp_files.append(sep_path)

            log.info(f"  간지 인쇄 (1장)...")
            ok_sep = print_hwpx(hwp, sep_path, copies=1, printer=PRINTER_NAME)
            if ok_sep:
                log.info(f"  ✓ 간지 전송 완료")
            else:
                log.warning(f"  ✗ 간지 전송 실패")

            time.sleep(JOB_DELAY)

            # ② 안내장 인쇄
            log.info(f"  안내장 인쇄 ({count}장)...")
            ok_main = print_hwpx(hwp, HWPX_FILE, copies=count, printer=PRINTER_NAME)
            if ok_main:
                log.info(f"  ✓ 안내장 전송 완료")
            else:
                log.warning(f"  ✗ 안내장 전송 실패")

            if i < len(classes):
                log.info(f"  다음 반까지 {JOB_DELAY}초 대기...")
                time.sleep(JOB_DELAY)
            print()

    finally:
        # 임시 간지 파일 삭제
        hwp.Quit()
        for f in tmp_files:
            try:
                Path(f).unlink()
            except Exception:
                pass

    log.info("=" * 50)
    log.info("인쇄 전송 완료!")
    log.info("프린터 출력물에서 간지를 기준으로 반별로 나누세요.")


if __name__ == "__main__":
    main()
