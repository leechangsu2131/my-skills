"""
프린터 사용자별 기본 용지함(Level 9 DEVMODE.DefaultSource)을 복구합니다.

FUJIFILM Apeos C2561 기준:
- 15 = 자동
- 1  = 트레이 1
- 3  = 트레이 2
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("python-dotenv 없음 → pip install python-dotenv")


load_dotenv(Path(__file__).parent / ".env")

PRINTER_NAME = os.getenv("PRINTER_NAME", "")
RESET_TRAY = int(os.getenv("POST_PRINT_TRAY", "15"))


def main() -> None:
    try:
        import win32print
    except ImportError:
        sys.exit("pywin32 없음 → pip install pywin32")

    printer = PRINTER_NAME or win32print.GetDefaultPrinter()
    hprinter = win32print.OpenPrinter(printer)
    try:
        info = win32print.GetPrinter(hprinter, 9)
        dm = info.get("pDevMode")
        if dm is None:
            sys.exit("pDevMode를 찾을 수 없습니다.")

        before = dm.DefaultSource
        dm.DefaultSource = RESET_TRAY
        win32print.SetPrinter(hprinter, 9, info, 0)

        refreshed = win32print.GetPrinter(hprinter, 9)
        after = refreshed.get("pDevMode").DefaultSource
    finally:
        win32print.ClosePrinter(hprinter)

    print(f"프린터: {printer}")
    print(f"사용자 기본 용지함(Level 9): {before} -> {after}")


if __name__ == "__main__":
    main()
