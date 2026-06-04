"""
setup_check.py
──────────────
환경 점검 스크립트 — Appium, ADB, 앱 설치 상태 등을 확인한다.

사용법:
    python setup_check.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def check_mark(ok: bool) -> str:
    return "✅" if ok else "❌"


def check_python() -> bool:
    ver = sys.version_info
    ok = ver >= (3, 9)
    print(f"  {check_mark(ok)} Python {ver.major}.{ver.minor}.{ver.micro}")
    return ok


def check_node() -> bool:
    node = shutil.which("node")
    if node:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True, text=True
        )
        ver = result.stdout.strip()
        print(f"  ✅ Node.js {ver}")
        return True
    print("  ❌ Node.js — 설치 필요 (https://nodejs.org)")
    return False


def check_java() -> bool:
    java = shutil.which("java")
    if java:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True, text=True, stderr=subprocess.STDOUT
        )
        ver = result.stdout.split("\n")[0] if result.stdout else "unknown"
        print(f"  ✅ Java {ver}")
        return True
    print("  ❌ Java JDK — 설치 필요 (https://adoptium.net)")
    return False


def check_adb() -> bool:
    adb = shutil.which("adb")
    if adb:
        result = subprocess.run(
            ["adb", "version"],
            capture_output=True, text=True
        )
        ver = result.stdout.split("\n")[0] if result.stdout else "unknown"
        print(f"  ✅ ADB {ver}")
        return True
    print("  ❌ ADB — Android SDK Platform Tools 설치 필요")
    print("       https://developer.android.com/tools/releases/platform-tools")
    return False


def check_adb_devices() -> bool:
    adb = shutil.which("adb")
    if not adb:
        return False
    result = subprocess.run(
        ["adb", "devices"],
        capture_output=True, text=True
    )
    lines = result.stdout.strip().split("\n")[1:]  # 헤더 제외
    devices = [l for l in lines if l.strip() and "device" in l]
    if devices:
        print(f"  ✅ 연결된 디바이스: {len(devices)}대")
        for d in devices:
            print(f"       {d.strip()}")
        return True
    print("  ❌ 연결된 안드로이드 디바이스 없음")
    print("       USB 연결 + USB 디버깅 활성화 확인")
    return False


def _find_appium() -> str | None:
    """appium 또는 appium.cmd를 찾는다 (Windows 호환)."""
    for name in ("appium", "appium.cmd"):
        found = shutil.which(name)
        if found:
            return found
    return None


def check_appium() -> bool:
    appium = _find_appium()
    if appium:
        result = subprocess.run(
            [appium, "--version"],
            capture_output=True, text=True, shell=True
        )
        ver = result.stdout.strip()
        print(f"  ✅ Appium {ver}")
        return True
    print("  ❌ Appium — 설치 필요:")
    print("       npm install -g appium")
    return False


def check_appium_driver() -> bool:
    appium = _find_appium()
    if not appium:
        return False
    result = subprocess.run(
        [appium, "driver", "list", "--installed"],
        capture_output=True, text=True, shell=True,
        encoding="utf-8", errors="replace",
    )
    output = (result.stdout or "") + (result.stderr or "")
    if "uiautomator2" in output.lower():
        print("  ✅ UiAutomator2 드라이버 설치됨")
        return True
    print("  ❌ UiAutomator2 드라이버 — 설치 필요:")
    print("       appium driver install uiautomator2")
    return False


def check_daangn_app() -> bool:
    adb = shutil.which("adb")
    if not adb:
        print("  ⚠️ 당근 앱 확인 불가 (ADB 없음)")
        return False
    result = subprocess.run(
        ["adb", "shell", "pm", "list", "packages", "com.towneers.www"],
        capture_output=True, text=True
    )
    if "com.towneers.www" in result.stdout:
        print("  ✅ 당근 앱 설치됨 (com.towneers.www)")
        return True
    print("  ❌ 당근 앱 미설치 — 폰에서 설치 필요")
    return False


def check_python_packages() -> bool:
    packages = {
        "appium": "Appium-Python-Client",
        "gspread": "gspread",
        "pandas": "pandas",
        "dotenv": "python-dotenv",
    }
    all_ok = True
    for module, pkg in packages.items():
        try:
            __import__(module if module != "dotenv" else "dotenv")
            print(f"  ✅ {pkg}")
        except ImportError:
            print(f"  ❌ {pkg} — pip install {pkg}")
            all_ok = False
    return all_ok


def check_env_file() -> bool:
    env_path = Path(".env")
    if env_path.exists():
        print("  ✅ .env 파일 존재")

        # 필수 키 확인
        content = env_path.read_text(encoding="utf-8")
        required = ["GOOGLE_SA_PROJECT_ID", "GOOGLE_SHEET_ID"]
        missing = [k for k in required if k not in content or f"{k}=" not in content]
        if missing:
            print(f"  ⚠️ .env에 다음 키가 비어있을 수 있음: {missing}")
        return True
    print("  ❌ .env 파일 없음 — .env.example을 복사하여 생성:")
    print("       copy .env.example .env")
    return False


def main() -> None:
    print("=" * 60)
    print("🔍 당근마켓 수집 시스템 — 환경 점검")
    print("=" * 60)

    results = {}

    print("\n📦 기본 도구:")
    results["python"] = check_python()
    results["node"] = check_node()
    results["java"] = check_java()

    print("\n📱 안드로이드:")
    results["adb"] = check_adb()
    if results["adb"]:
        results["device"] = check_adb_devices()
        results["daangn"] = check_daangn_app()
    else:
        results["device"] = False
        results["daangn"] = False

    print("\n🤖 Appium:")
    results["appium"] = check_appium()
    if results["appium"]:
        results["uia2"] = check_appium_driver()
    else:
        results["uia2"] = False

    print("\n🐍 Python 패키지:")
    results["packages"] = check_python_packages()

    print("\n⚙️ 설정:")
    results["env"] = check_env_file()

    # 요약
    total = len(results)
    passed = sum(results.values())
    print(f"\n{'='*60}")
    print(f"📊 결과: {passed}/{total} 통과")

    if passed == total:
        print("🎉 모든 환경이 준비되었습니다!")
        print("   python main.py --dry-run  으로 테스트해보세요.")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"⚠️ 미통과 항목: {', '.join(failed)}")
        print("   위의 안내를 따라 설치/설정을 완료해주세요.")


if __name__ == "__main__":
    main()
