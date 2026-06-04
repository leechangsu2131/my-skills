"""
appium_driver.py
────────────────
Appium 서버 연결 및 드라이버 관리.
안드로이드 폰에 연결하여 당근 앱을 자동 조작할 수 있는 드라이버를 제공한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from appium import webdriver
from appium.options.android import UiAutomator2Options

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def load_config() -> dict:
    """config.json을 로드한다."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def create_driver(
    *,
    host: str | None = None,
    port: int | None = None,
    visible: bool = True,
) -> webdriver.Remote:
    """
    Appium Remote 드라이버를 생성한다.

    Parameters
    ----------
    host : str
        Appium 서버 호스트 (기본: config.json의 값)
    port : int
        Appium 서버 포트 (기본: config.json의 값)
    visible : bool
        True면 앱 화면 표시 (항상 True — 실제 디바이스이므로)

    Returns
    -------
    webdriver.Remote
        Appium 드라이버 인스턴스
    """
    cfg = load_config()
    appium_cfg = cfg.get("appium", {})

    _host = host or appium_cfg.get("host", "127.0.0.1")
    _port = port or appium_cfg.get("port", 4723)

    options = UiAutomator2Options()
    options.platform_name = appium_cfg.get("platform", "Android")

    # 디바이스 이름 — "Auto"면 자동 감지
    device_name = appium_cfg.get("device_name", "Auto")
    if device_name and device_name.lower() != "auto":
        options.device_name = device_name

    # 당근 앱 패키지
    options.app_package = appium_cfg.get("app_package", "com.towneers.www")
    options.app_activity = appium_cfg.get("app_activity", "com.towneers.www.MainActivity")

    # 앱 초기화하지 않음 (로그인 유지)
    options.no_reset = appium_cfg.get("no_reset", True)

    # 권한 자동 승인
    if appium_cfg.get("auto_grant_permissions", True):
        options.auto_grant_permissions = True

    # 타임아웃 설정
    options.new_command_timeout = 300  # 5분

    server_url = f"http://{_host}:{_port}"

    print(f"[Appium] 서버 연결 중: {server_url}")
    print(f"[Appium] 앱: {options.app_package}")

    try:
        driver = webdriver.Remote(server_url, options=options)
        print("[Appium] ✅ 연결 성공!")
        return driver
    except Exception as e:
        print(f"[Appium] ❌ 연결 실패: {e}")
        print()
        print("확인사항:")
        print("  1. Appium 서버가 실행 중인지  (appium)")
        print("  2. 안드로이드 폰이 USB로 연결되었는지  (adb devices)")
        print("  3. USB 디버깅이 활성화되어 있는지")
        print("  4. 당근 앱이 설치되어 있는지")
        sys.exit(1)


def quit_driver(driver: Optional[webdriver.Remote]) -> None:
    """드라이버를 안전하게 종료한다."""
    if driver:
        try:
            driver.quit()
            print("[Appium] 드라이버 종료 완료")
        except Exception:
            pass
