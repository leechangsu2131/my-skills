"""
1개 반 인쇄 시뮬레이션 테스트 (win32print Level 9 트레이 방식)
"""
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("❌ python-dotenv 없음 → pip install python-dotenv")

import os
load_dotenv(Path(__file__).parent / ".env")

HWPX_DIR           = os.getenv("HWPX_DIR", "")
SEPARATOR_TEMPLATE = os.getenv("SEPARATOR_TEMPLATE", "")
PRINTER_NAME       = os.getenv("PRINTER_NAME", "")
SEPARATOR_TRAY     = int(os.getenv("SEPARATOR_TRAY", "3")) # 기본값 3 (Tray 2)
MAIN_TRAY          = 1  # 트레이 1 (안내장용)
JOB_DELAY          = int(os.getenv("JOB_DELAY", "3"))

print("=" * 60)
print("  한글 OLE 인쇄 시뮬레이션 (Level 9 DEVMODE 방식)")
print("=" * 60)

# ── 안내장 파일 선택 ──────────────────────────────────────
candidates = sorted(Path(HWPX_DIR).glob("*안내장.hwpx")) if HWPX_DIR else []
if not candidates:
    sys.exit(f"❌ 안내장 파일 없음: {HWPX_DIR}")

print("\n안내장 파일:")
for i, p in enumerate(candidates, 1):
    print(f"  [{i}] {p.name}")
raw = input(f"번호 선택 (1~{len(candidates)}): ").strip()
hwpx_file = str(candidates[int(raw) - 1])
try:
    copies = int(input("안내장 매수 (예: 3): ").strip() or 3)
except ValueError:
    copies = 3

print()
print("━" * 55)
print(f"  간지   : {Path(SEPARATOR_TEMPLATE).name} × 1장  (트레이 DEVMODE={SEPARATOR_TRAY})")
print(f"  안내장 : {Path(hwpx_file).name} × {copies}장   (트레이 DEVMODE={MAIN_TRAY})")
print(f"  프린터 : {PRINTER_NAME or '(기본 프린터)'}")
print("━" * 55)
input("준비됐으면 Enter...")

# ── pywin32 ───────────────────────────────────────────────
try:
    import win32com.client
    import win32print
except ImportError:
    sys.exit("❌ pywin32 없음 → pip install pywin32")

hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
try:
    hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
except Exception:
    pass

def set_bin(bin_num: int | None) -> int | None:
    """PRINTER_INFO_9 로 사용자 권한 영역의 DEVMODE.DefaultSource 변경"""
    if not PRINTER_NAME or bin_num is None:
        return None
    try:
        h = win32print.OpenPrinter(PRINTER_NAME)
        info = win32print.GetPrinter(h, 9)  # 2가 아닌 9 (사용자 권한 통과)
        dm = info.get("pDevMode")
        if dm is None:
            win32print.ClosePrinter(h)
            return None
        orig = dm.DefaultSource
        dm.DefaultSource = bin_num
        win32print.SetPrinter(h, 9, info, 0)
        win32print.ClosePrinter(h)
        print(f"  트레이 변경 성공: {orig} → {bin_num}")
        return orig
    except Exception as e:
        print(f"  트레이 설정 실패: {e}")
        return None

def do_print(file_path: str, n: int, label: str) -> bool:
    print(f"  [{label}] 열기...")
    hwp.Open(file_path, "HWPX", "forceopen:true")
    time.sleep(1.5)
    act  = hwp.CreateAction("Print")
    hset = act.CreateSet()
    act.GetDefault(hset)
    hset.SetItem("NumCopy", n)
    hset.SetItem("Range", 0)
    hset.SetItem("Collate", True)
    if PRINTER_NAME:
        hset.SetItem("UsePrinterName", PRINTER_NAME)
    result = act.Execute(hset)
    hwp.Clear(1)
    ok = bool(result)
    print(f"  ✔ {label} 전송 완료 ({n}장)" if ok else f"  ✗ {label} 전송 실패")
    return ok

try:
    # 윈도우 인쇄 스풀러 안정화를 위해 변경 -> 인쇄 -> 복원 순으로 명확하게 처리합니다.
    
    orig = None
    print("\n[STEP 1] 간지 인쇄")
    orig = set_bin(SEPARATOR_TRAY) # 트레이 3(B세트)으로 변경
    time.sleep(1) # 프린터 설정 적용 대기
    do_print(SEPARATOR_TEMPLATE, 1, "간지")

    print(f"  {JOB_DELAY}초 대기...")
    time.sleep(JOB_DELAY)

    print("\n[STEP 2] 안내장 인쇄")
    set_bin(MAIN_TRAY) # 트레이 1로 강제 변경 (안내장 전용)
    time.sleep(1) # 프린터 설정 적용 대기
    do_print(hwpx_file, copies, "안내장")

    print("\n[STEP 3] 트레이 원복")
    if orig is not None:
        set_bin(orig) # 맨 처음 설정으로 원복

    print("\n━" * 55)
    print("  확인 사항:")
    print(f"  ① 간지 → 트레이 {SEPARATOR_TRAY} 에서 나왔는지")
    print(f"  ② 안내장 → 트레이 {MAIN_TRAY} 에서 {copies}장 나왔는지")
    print("━" * 55)

except Exception as e:
    print(f"\n❌ 오류: {e}")
finally:
    try:
        hwp.Quit()
    except Exception:
        pass

input("\n아무 키나 누르면 종료...")
