"""
한글(HWP)의 저장된 인쇄 파라미터를 초기화합니다.

Windows 프린터 기본 용지함이 자동(15)인데도 한글에서만 계속 트레이2를
찾는 경우, 한글 사용자 설정 레지스트리에 남은 HPrint 파라미터가 원인일 수
있습니다. 이 스크립트는 해당 값을 백업한 뒤 삭제하고, 프린터 기본 용지함도
POST_PRINT_TRAY 값으로 맞춥니다.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import winreg
except ImportError:
    sys.exit("Windows에서만 실행할 수 있습니다.")

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("python-dotenv 없음 → pip install python-dotenv")


BASE_DIR = Path(__file__).parent
BACKUP_DIR = BASE_DIR / "registry_backups"
HPRINT_KEYS = [
    r"Software\HNC\Hwp\13.0\Parameters\00000215",
    r"Software\HNC\Hwp\10.2\Parameters\00000215",
]


load_dotenv(BASE_DIR / ".env")
PRINTER_NAME = os.getenv("PRINTER_NAME", "")
RESET_TRAY = int(os.getenv("POST_PRINT_TRAY", "15"))


def _hwp_is_running() -> bool:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Process Hwp,HwpApi -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName"],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def _read_key(root, path: str) -> dict | None:
    try:
        key = winreg.OpenKey(root, path)
    except FileNotFoundError:
        return None

    values = {}
    try:
        index = 0
        while True:
            try:
                name, value, value_type = winreg.EnumValue(key, index)
            except OSError:
                break
            values[name] = {
                "type": value_type,
                "value": list(value) if isinstance(value, bytes) else value,
            }
            index += 1
    finally:
        winreg.CloseKey(key)

    return values


def _delete_key(root, path: str) -> bool:
    try:
        winreg.DeleteKey(root, path)
        return True
    except FileNotFoundError:
        return False


def _reset_printer_tray() -> tuple[int, int] | None:
    try:
        import win32print
    except ImportError:
        print("pywin32 없음 → 프린터 용지함 복구는 건너뜁니다.")
        return None

    printer = PRINTER_NAME or win32print.GetDefaultPrinter()
    hprinter = win32print.OpenPrinter(printer)
    try:
        info = win32print.GetPrinter(hprinter, 9)
        dm = info.get("pDevMode")
        if dm is None:
            return None
        before = dm.DefaultSource
        dm.DefaultSource = RESET_TRAY
        win32print.SetPrinter(hprinter, 9, info, 0)
        refreshed = win32print.GetPrinter(hprinter, 9)
        after = refreshed.get("pDevMode").DefaultSource
        return before, after
    finally:
        win32print.ClosePrinter(hprinter)


def main() -> int:
    if _hwp_is_running():
        print("한글(Hwp.exe)이 실행 중입니다.")
        print("열려 있는 한글 문서를 저장하고 한글을 완전히 종료한 뒤 다시 실행하세요.")
        return 2

    backup = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "keys": {},
    }

    for path in HPRINT_KEYS:
        backup["keys"][path] = _read_key(winreg.HKEY_CURRENT_USER, path)

    BACKUP_DIR.mkdir(exist_ok=True)
    backup_file = BACKUP_DIR / f"hwp_print_parameters_{datetime.now():%Y%m%d_%H%M%S}.json"
    backup_file.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")

    deleted = []
    for path in HPRINT_KEYS:
        if _delete_key(winreg.HKEY_CURRENT_USER, path):
            deleted.append(path)

    print(f"백업: {backup_file}")
    if deleted:
        print("삭제한 한글 인쇄 파라미터:")
        for path in deleted:
            print(f"  HKCU\\{path}")
    else:
        print("삭제할 한글 인쇄 파라미터가 없습니다.")

    tray_result = _reset_printer_tray()
    if tray_result:
        before, after = tray_result
        print(f"프린터 사용자 기본 용지함(Level 9): {before} -> {after}")

    print("이제 한글을 다시 열고 다른 문서를 인쇄해 보세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
