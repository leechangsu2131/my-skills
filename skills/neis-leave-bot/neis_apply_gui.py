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
import pyautogui

# 안전 설정 (computer-use-agents 스타일)
pyautogui.FAILSAFE = True  # 화면 왼쪽 상단으로 마우스 이동 시 즉시 중단
pyautogui.PAUSE = 0.1      # 모든 동작 사이 기본 지연

class NeisGuiConfig:
    """
    동적 캘리브레이션 툴(`neis_apply_gui_setup.py`)로 얻어낸 
    (좌표, 이름) 리스트와 입력할 값을 여기에 순서대로 정의합니다.
    
    steps 포맷:
        ("용도", (x, y), "입력할 텍스트(선택)")
    """
    
    # ----------------------------------------------------
    # TODO: neis_apply_gui_setup.py 로 추출한 좌표와 
    #       입력할 내용을 여기에 순서대로 정의하세요. 
    #       텍스트가 None 이면 클릭만 하고 넘어갑니다.
    # ----------------------------------------------------
    steps = [
        ("모달 포커스 및 스크롤 내리기", (960, 200), "SCROLL_DOWN_3"),
        ("휴가 종류/근무상황 클릭", (960, 420), "특별휴가"),
        ("시작일 입력", (960, 460), "2026-03-16"),
        ("종료일 입력", (1120, 460), "2026-03-16"),
        ("사유 입력", (960, 520), "육아시간 사용"),
        ("저장/신청 버튼 클릭", (1500, 820), None),
    ]


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


def run_dynamic_steps(config: NeisGuiConfig = NeisGuiConfig()):
    """설정된 순서대로 마우스 클릭 및 키보드 입력을 수행합니다."""
    
    for idx, (name, (x, y), text) in enumerate(config.steps):
        print(f"[{idx+1}] {name} 진행 중...")
        
        # 1. 일단 해당 좌표를 클릭 (포커스 잡기)
        _click(x, y)
        
        # 2. 특별한 매크로 커맨드 처리 (예: 스크롤)
        if text == "SCROLL_DOWN_3":
            time.sleep(0.5)
            pyautogui.press("pagedown", presses=3, interval=0.1)
            time.sleep(1.0)
            continue
            
        # 3. 텍스트가 있다면 지우고 입력
        if text:
            # 기존 내용 지우기
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            time.sleep(0.1)
            
            # 새 내용 타이핑
            pyautogui.typewrite(text, interval=0.05)
            
            # 드롭다운이나 콤보박스의 경우 엔터가 필요할 때를 대비해 가볍게 딜레이 후 엔터
            # (일반 텍스트칸에 엔터를 쳐도 보통 무방함)
            time.sleep(0.2)
            pyautogui.press("enter")
            
        time.sleep(0.3)
        
    print("\n✅ 매크로 순차 실행 완료!")


if __name__ == "__main__":
    import sys

    if "--calibrate" in sys.argv:
        print("이제 캘리브레이션은 전용 도구인 `neis_apply_gui_setup.py`를 사용합니다.")
        print("터미널에 다음 명령어를 입력하세요: python neis_apply_gui_setup.py")
        sys.exit(0)
    else:
        print("==================================================")
        print(" NEIS 신청 폼 매크로 자동 실행")
        print(" (수정은 NeisGuiConfig.steps 리스트를 변경하세요)")
        print("==================================================")
        print("※ NEIS 신청 화면이 원하는 위치(예: 중앙/최대화)에 떠 있는지 확인!")
        input("준비가 되었다면 Enter를 눌러 매크로를 시작합니다... (취소: Ctrl+C)")
        run_dynamic_steps()

