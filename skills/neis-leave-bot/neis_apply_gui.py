"""
나이스(NEIS) 신청창 GUI 매크로 (pyautogui)
==========================================
전제:
  - 해상도: 1920 x 1080
  - NEIS 창: 항상 최대화
  - `neis_apply.py` 등으로 이미 '신청' 화면(특별휴가/육아시간 신청 폼)이 떠 있는 상태

역할:
  - 사람처럼 마우스/키보드를 사용해서 신청 폼에 값을 채우고,
    마지막에 저장/신청 버튼까지 눌러준다.

주의:
  - 좌표는 각 환경에 따라 다르므로, 최초 1~2회는 "캘리브레이션 모드"로
    좌표를 화면에 찍어보고, 아래 CONFIG를 수정한 뒤 사용하는 것을 권장한다.
"""

import time
from dataclasses import dataclass
from typing import Tuple

import pyautogui


# 안전 설정 (computer-use-agents 스타일)
pyautogui.FAILSAFE = True  # 화면 왼쪽 상단으로 마우스 이동 시 즉시 중단
pyautogui.PAUSE = 0.1      # 모든 동작 사이 기본 지연


@dataclass
class FieldCoords:
    """신청 폼 내 주요 필드 좌표."""

    # 예시: 특별휴가 / 육아시간 신청 폼 기준 (1920x1080, 창 최대화)
    leave_type_dropdown: Tuple[int, int]   # '근무상황' 또는 휴가 종류 드롭다운
    date_start_field: Tuple[int, int]      # 시작일
    date_end_field: Tuple[int, int]        # 종료일
    reason_field: Tuple[int, int]          # 사유 텍스트
    save_button: Tuple[int, int]           # 저장/신청 버튼


class NeisGuiConfig:
    """
    한 번만 본인 화면에 맞게 좌표를 맞추면,
    이후에는 그대로 재사용 가능한 설정 컨테이너.
    """

    # TODO: 최초 사용 시 이 좌표들을 실제 값으로 바꿔주세요.
    #   1) python neis_apply_gui.py --calibrate 실행
    #   2) 표시되는 안내에 따라 마우스를 원하는 칸 위에 올리고 Enter
    #   3) 출력된 좌표를 아래에 복사/붙여넣기
    fields = FieldCoords(
        leave_type_dropdown=(960, 420),
        date_start_field=(960, 460),
        date_end_field=(1120, 460),
        reason_field=(960, 520),
        save_button=(1500, 820),
    )

    # 기본 입력값 (예시: 특별휴가 / 육아시간)
    leave_type_text = "특별휴가"     # 혹은 콤보박스 검색 키워드
    start_date = "2026-03-16"
    end_date = "2026-03-16"
    reason = "육아시간 사용"


def _focus_and_type(x: int, y: int, text: str, clear: bool = True):
    """지정 좌표를 클릭하고 텍스트를 입력한다."""
    pyautogui.click(x, y)
    time.sleep(0.2)
    if clear:
        # ctrl+a, delete로 기존 내용 삭제
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("backspace")
        time.sleep(0.1)
    if text:
        pyautogui.typewrite(text, interval=0.05)


def _click(x: int, y: int):
    pyautogui.click(x, y)
    time.sleep(0.2)


def calibrate():
    """
    간단한 좌표 캘리브레이션 도우미.

    사용법:
      1) 나이스 신청 화면을 띄워둔 상태에서 이 스크립트를

         python neis_apply_gui.py --calibrate

         형태로 실행합니다.

      2) 프롬프트가 나오면, 안내에 맞는 필드 위에 마우스를 올려두고 Enter를 누릅니다.
      3) 마지막에 찍힌 좌표들을 NeisGuiConfig.fields에 그대로 복사/붙여넣습니다.
    """
    items = [
        "휴가/근무상황 드롭다운",
        "시작일 입력칸",
        "종료일 입력칸",
        "사유 입력칸",
        "저장/신청 버튼",
    ]
    results = []
    print("=== NEIS GUI 좌표 캘리브레이션 ===")
    print("마우스를 해당 위치에 올려두고 Enter를 누르세요. (취소: Ctrl+C)")
    for name in items:
        input(f"\n[대상] {name} 위치에 마우스를 올려두고 Enter...")
        x, y = pyautogui.position()
        print(f"  → {name} 좌표: ({x}, {y})")
        results.append((name, x, y))

    print("\n=== 복사해서 설정에 반영하세요 ===")
    print("FieldCoords(")
    print(f"    leave_type_dropdown=({results[0][1]}, {results[0][2]}),")
    print(f"    date_start_field=({results[1][1]}, {results[1][2]}),")
    print(f"    date_end_field=({results[2][1]}, {results[2][2]}),")
    print(f"    reason_field=({results[3][1]}, {results[3][2]}),")
    print(f"    save_button=({results[4][1]}, {results[4][2]}),")
    print(")")


def run_special_leave(config: NeisGuiConfig = NeisGuiConfig()):
    """
    특별휴가/육아시간 신청 폼에 값을 채우는 메인 루틴.

    전제:
      - 신청 화면이 이미 떠 있고,
      - 창이 최대화되어 있으며,
      - CONFIG의 좌표가 실제 화면과 맞다.
    """
    f = config.fields

    print("[1] 휴가 종류/근무상황 선택")
    _click(*f.leave_type_dropdown)
    time.sleep(0.3)
    # 콤보박스에 바로 타이핑해서 항목 검색 후 Enter 하는 패턴
    pyautogui.typewrite(config.leave_type_text, interval=0.05)
    time.sleep(0.3)
    pyautogui.press("enter")

    print("[2] 시작/종료일 입력")
    _focus_and_type(*f.date_start_field, config.start_date)
    _focus_and_type(*f.date_end_field, config.end_date)

    print("[3] 사유 입력")
    _focus_and_type(*f.reason_field, config.reason)

    print("[4] 저장/신청 버튼 클릭")
    _click(*f.save_button)

    print("\n✅ GUI 기반 특별휴가/육아시간 신청 매크로 동작 완료 (화면에서 결과를 확인하세요).")


if __name__ == "__main__":
    import sys

    if "--calibrate" in sys.argv:
        calibrate()
    else:
        print("NEIS 신청 화면이 최대화된 상태인지 확인해 주세요. (해상도 1920x1080 가정)")
        input("준비가 되었다면 Enter를 눌러 매크로를 시작합니다... (취소: Ctrl+C)")
        run_special_leave()

