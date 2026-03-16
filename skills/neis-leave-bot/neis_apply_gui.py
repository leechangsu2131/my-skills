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
import sys
import os
import json
import pyautogui

# 안전 설정 (computer-use-agents 스타일)
pyautogui.FAILSAFE = True  # 화면 왼쪽 상단으로 마우스 이동 시 즉시 중단
pyautogui.PAUSE = 0.1      # 모든 동작 사이 기본 지연


def load_config(filename="neis_gui_config.json"):
    """JSON 파일에서 동적 캘리브레이션 설정을 불러옵니다."""
    if not os.path.exists(filename):
        print(f"[{filename}] 설정 파일을 찾을 수 없습니다.")
        print("먼저 `python neis_apply_gui_setup.py` 를 실행하여 캘리브레이션을 진행해 주세요.")
        sys.exit(1)
        
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"설정 파일({filename})을 읽는 중 오류가 발생했습니다: {e}")
        sys.exit(1)


def _click(x: int, y: int):
    pyautogui.click(x, y)
    time.sleep(0.2)



def run_dynamic_steps(config_data: dict):
    """설정된 순서대로 마우스 클릭 및 키보드 입력을 수행합니다."""
    
    steps = config_data.get("steps", [])
    if not steps:
        print("실행할 step이 없습니다. 설정을 확인해 주세요.")
        return
        
    for idx, step in enumerate(steps):
        name = step.get("name", f"Step {idx+1}")
        x = step.get("x")
        y = step.get("y")
        text = step.get("text", "")
        ftype = step.get("type", "click")
        
        print(f"[{idx+1}] {name} 진행 중... (유형: {ftype})")
        
        # 1. 일단 해당 좌표를 클릭 (포커스 잡기)
        if x is not None and y is not None:
            _click(x, y)
        
        # 2. 특별한 매크로 커맨드 처리 (예: 스크롤)
        if text == "SCROLL_DOWN_3":
            time.sleep(0.5)
            pyautogui.press("pagedown", presses=3, interval=0.1)
            time.sleep(1.0)
            continue
            
        # 3. 유형별 동작 처리
        if ftype == "text" and text:
            # 기존 내용 지우기
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            time.sleep(0.1)
            
            # 새 내용 타이핑
            pyautogui.typewrite(text, interval=0.05)
            time.sleep(0.2)
            
        elif ftype == "dropdown" and text:
            # 드롭다운은 선택지를 펼친 상태에서 타이핑 후 Enter 로 선택하는 패턴
            pyautogui.typewrite(text, interval=0.05)
            time.sleep(0.2)
            pyautogui.press("enter")
            time.sleep(0.2)
            
        elif text and ftype == "click":
            # click 이지만 텍스트가 있는 경우 무시하거나 그냥 타이핑
            pass
            
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
        print(" (수정은 `neis_gui_config.json` 파일을 변경하세요)")
        print("==================================================")
        config_data = load_config()
        print(f"👉 총 {len(config_data.get('steps', []))}개의 스텝을 불러왔습니다.")
        print("※ NEIS 신청 화면이 원하는 위치(예: 중앙/최대화)에 떠 있는지 확인!")
        input("준비가 되었다면 Enter를 눌러 매크로를 시작합니다... (취소: Ctrl+C)")
        run_dynamic_steps(config_data)

