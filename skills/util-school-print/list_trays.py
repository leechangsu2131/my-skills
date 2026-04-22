"""
프린터 용지함(트레이) 번호 목록 조회
- 이 스크립트를 실행하면 프린터의 실제 트레이 번호와 이름을 출력합니다
- 출력된 번호를 .env의 SEPARATOR_TRAY에 입력하세요
"""
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("❌ python-dotenv 없음")
import os
load_dotenv(Path(__file__).parent / ".env")
PRINTER_NAME = os.getenv("PRINTER_NAME", "")

try:
    import win32print
    import win32con
except ImportError:
    sys.exit("❌ pywin32 없음 → pip install pywin32")

if not PRINTER_NAME:
    # 기본 프린터 사용
    PRINTER_NAME = win32print.GetDefaultPrinter()

print(f"\n프린터: {PRINTER_NAME}")
print("=" * 60)

try:
    hprinter = win32print.OpenPrinter(PRINTER_NAME)
    pinfo    = win32print.GetPrinter(hprinter, 2)
    port     = pinfo["pPortName"]
    win32print.ClosePrinter(hprinter)

    bins    = win32print.DeviceCapabilities(PRINTER_NAME, port, win32con.DC_BINS)
    names   = win32print.DeviceCapabilities(PRINTER_NAME, port, win32con.DC_BINNAMES)

    print(f"{'번호':>6}  이름")
    print("-" * 40)
    for num, name in zip(bins, names):
        name_str = name.rstrip('\x00').strip()
        marker = "  ← 트레이2(B세트) 후보" if "2" in name_str or "B" in name_str else ""
        print(f"  {num:>4}   {name_str}{marker}")

    print()
    print("위 번호 중 트레이2(B세트)에 해당하는 번호를 .env의 SEPARATOR_TRAY에 입력하세요.")
except Exception as e:
    print(f"❌ 오류: {e}")
    print("프린터 이름을 확인하거나 관리자 권한으로 실행해보세요.")

input("\n아무 키나 누르면 종료...")
