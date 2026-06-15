"""
A4 인쇄가 트레이2만 찾는 문제 — Windows/한글 쪽 원상복구

복합기 본체 설정은 건드리지 않고, PC에서 바꿀 수 있는 것만 수정합니다.
- PRINTER_INFO_9: 현재 사용자 기본 용지함 → 트레이1 (번호 1)
- 한글 레지스트리: 마지막 인쇄 파라미터 삭제

FUJIFILM Apeos C2561 PCL6 기준 트레이 번호:
  1 = 트레이1,  3 = 트레이2,  15 = 자동
자동(15)은 복합기 설정에 따라 트레이2 A4를 요구할 수 있어 트레이1(1)로 고정합니다.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

try:
    import winreg
except ImportError:
    sys.exit("Windows에서만 실행할 수 있습니다.")

try:
    import win32print
    import win32con
except ImportError:
    sys.exit("pywin32 없음 → pip install pywin32")

BASE_DIR = Path(__file__).parent
BACKUP_DIR = BASE_DIR / "registry_backups"
TARGET_TRAY = 1  # 트레이1 고정
PRINTER_HINT = "Apeos C2561"


def find_printer() -> str:
  """후지필름 Apeos만 대상. 신도 등 기본 프린터는 사용하지 않음."""
  name = os.getenv("PRINTER_NAME", "").strip()
  if name:
    return name
  matches = [
      p[2] for p in win32print.EnumPrinters(
          win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
      )
      if PRINTER_HINT.lower() in p[2].lower()
  ]
  if not matches:
    sys.exit(f"후지필름 Apeos 프린터를 찾을 수 없습니다. (검색: {PRINTER_HINT})")
  if len(matches) > 1:
    print("여러 Apeos 프린터 발견, 첫 번째 사용:")
    for m in matches:
      print(f"  - {m}")
  return matches[0]


def list_trays(printer: str) -> list[tuple[int, str]]:
  h = win32print.OpenPrinter(printer)
  try:
    port = win32print.GetPrinter(h, 2)["pPortName"]
    bins = win32print.DeviceCapabilities(printer, port, win32con.DC_BINS)
    names = win32print.DeviceCapabilities(printer, port, win32con.DC_BINNAMES)
    return list(zip(bins, names))
  finally:
    win32print.ClosePrinter(h)


def read_level9_source(printer: str) -> int | None:
  h = win32print.OpenPrinter(printer)
  try:
    dm = win32print.GetPrinter(h, 9).get("pDevMode")
    return None if dm is None else dm.DefaultSource
  finally:
    win32print.ClosePrinter(h)


def set_level9_source(printer: str, tray: int) -> tuple[int | None, int | None]:
  h = win32print.OpenPrinter(printer)
  try:
    info = win32print.GetPrinter(h, 9)
    dm = info.get("pDevMode")
    if dm is None:
      return None, None
    before = dm.DefaultSource
    dm.DefaultSource = tray
    win32print.SetPrinter(h, 9, info, 0)
    after = win32print.GetPrinter(h, 9)["pDevMode"].DefaultSource
    return before, after
  finally:
    win32print.ClosePrinter(h)


def hwp_running() -> bool:
  r = subprocess.run(
      ["powershell", "-NoProfile", "-Command",
       "Get-Process Hwp,HwpApi -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName"],
      capture_output=True, text=True, check=False,
  )
  return bool(r.stdout.strip())


def hwp_print_keys() -> list[str]:
  keys: list[str] = []
  root = r"Software\HNC\Hwp"
  try:
    hnc = winreg.OpenKey(winreg.HKEY_CURRENT_USER, root)
    i = 0
    while True:
      try:
        ver = winreg.EnumKey(hnc, i)
        keys.append(rf"{root}\{ver}\Parameters\00000215")
        keys.append(rf"{root}\{ver}\Print")
        i += 1
      except OSError:
        break
    winreg.CloseKey(hnc)
  except FileNotFoundError:
    pass
  return keys


def read_reg_key(path: str) -> dict | None:
  try:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path)
  except FileNotFoundError:
    return None
  values = {}
  try:
    i = 0
    while True:
      try:
        name, value, vtype = winreg.EnumValue(key, i)
      except OSError:
        break
      values[name] = {
          "type": vtype,
          "value": list(value) if isinstance(value, bytes) else value,
      }
      i += 1
  finally:
    winreg.CloseKey(key)
  return values or None


def delete_reg_key(path: str) -> bool:
  try:
    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    return True
  except FileNotFoundError:
    return False


def reset_hwp_registry() -> tuple[Path | None, list[str]]:
  keys = hwp_print_keys()
  backup = {"created_at": datetime.now().isoformat(timespec="seconds"), "keys": {}}
  for path in keys:
    backup["keys"][path] = read_reg_key(path)
  nonempty = [p for p, v in backup["keys"].items() if v]
  if not nonempty:
    return None, []
  BACKUP_DIR.mkdir(exist_ok=True)
  backup_file = BACKUP_DIR / f"fix_a4_tray1_{datetime.now():%Y%m%d_%H%M%S}.json"
  backup_file.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")
  deleted = [p for p in keys if delete_reg_key(p)]
  return backup_file, deleted


def send_test_page(printer: str) -> bool:
  with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
    f.write(f"A4 tray1 test\nprinter={printer}\ntray={TARGET_TRAY}\n{datetime.now()}\n")
    path = f.name
  try:
    win32print.SetDefaultPrinter(printer)
    win32api = __import__("win32api")
    win32api.ShellExecute(0, "print", path, f'/d:"{printer}"', ".", 0)
    return True
  except Exception as e:
    print(f"  테스트 인쇄 전송 실패: {e}")
    return False
  finally:
    try:
      Path(path).unlink(missing_ok=True)
    except Exception:
      pass


def main() -> int:
  printer = find_printer()
  print(f"대상 프린터: {printer}")
  print()

  print("용지함 목록:")
  for num, name in list_trays(printer):
    mark = "  <-- 복구 목표" if num == TARGET_TRAY else ""
    print(f"  {num}: {name}{mark}")
  print()

  before = read_level9_source(printer)
  print(f"복구 전 사용자 기본 용지함(Level 9): {before}")

  b, after = set_level9_source(printer, TARGET_TRAY)
  print(f"복구 후 사용자 기본 용지함(Level 9): {b} -> {after}")

  if after != TARGET_TRAY:
    print("오류: 용지함 변경에 실패했습니다.")
    return 1

  if hwp_running():
    print()
    print("한글이 실행 중입니다. 저장 후 한글을 종료하고 이 스크립트를 다시 실행하세요.")
    print("(프린터 용지함은 이미 트레이1로 바뀌었습니다.)")
    return 2

  backup_file, deleted = reset_hwp_registry()
  if backup_file:
    print(f"한글 인쇄 설정 백업: {backup_file}")
    for p in deleted:
      print(f"  삭제: HKCU\\{p}")
  else:
    print("삭제할 한글 인쇄 레지스트리 항목 없음")

  print()
  ans = input("테스트 페이지 1장을 보낼까요? (Y/N, 기본 N): ").strip().upper()
  if ans == "Y":
    if send_test_page(printer):
      print("테스트 인쇄 작업을 스풀러에 넣었습니다. 트레이1에서 A4가 나오는지 확인하세요.")
  else:
    print("테스트 인쇄는 건너뜁니다.")

  print()
  print("완료. 메모장·한글에서 A4 문서를 인쇄해 보세요.")
  print("다른 PC에서도 같으면 fix_a4_tray1.bat 을 각 PC에서 실행하거나,")
  print("복합기 관리자에게 A4 기본 급지=트레이1 설정을 요청하세요.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
