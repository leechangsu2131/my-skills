"""
나이스(NEIS) 동적 GUI 좌표 캘리브레이션 툴
==============================================
자유롭게 원하는 만큼 마우스 좌표를 찍고, 각각의 이름을 부여하여
neis_apply_gui_config.py 형태로 저장해주는 도우미 스크립트입니다.

사용법:
1) python neis_apply_gui_setup.py 실행
2) 원하는 위치에 마우스를 올리고 Enter 누르기
3) 해당 좌표의 이름(용도) 입력하기
4) 완료되었으면 Ctrl+C를 눌러 종료 (자동으로 파일로 저장됨)
"""

import sys
import pyautogui

def run_dynamic_calibration():
    print("=====================================================")
    print(" 나이스(NEIS) 동적 GUI 캘리브레이션 시작")
    print("=====================================================")
    print("- 마우스를 원하는 위치에 올리고 [Enter]를 누르세요.")
    print("- 누른 직후 해당 위치의 '이름(용도)'을 입력받습니다.")
    print("- 모든 좌표를 다 찍었으면 [Ctrl + C]를 눌러 종료하세요.")
    print("  (종료 시 지금까지 찍은 좌표들이 파이썬 코드로 출력됩니다.)")
    print("=====================================================\n")

    results = []
    
    try:
        count = 1
        while True:
            input(f"[{count}번째] 마우스를 위치시키고 Enter를 누르세요 (종료는 Ctrl+C)...")
            x, y = pyautogui.position()
            
            name = input(f"  → 방금 찍은 좌표({x}, {y})의 이름(용도)을 입력하세요: ").strip()
            if not name:
                name = f"field_{count}"
                
            results.append((name, x, y))
            print(f"  ✅ 저장됨: {name} = ({x}, {y})\n")
            count += 1
            
    except KeyboardInterrupt:
        print("\n\n[입력 종료] 캘리브레이션을 마칩니다.")
    
    if not results:
        print("입력된 좌표가 없습니다. 프로그램을 종료합니다.")
        return

    # 파이썬 클래스 형태로 출력
    print("\n\n" + "="*50)
    print("아래 코드를 복사해서 `neis_apply_gui.py` 의 설정(또는 별도 파일)에 사용하세요.")
    print("="*50 + "\n")
    
    print("from dataclasses import dataclass")
    print("from typing import Tuple\n")
    
    print("@dataclass")
    print("class FieldCoords:")
    for name, _, _ in results:
        # 변수명으로 쓰기 좋게 띄어쓰기를 언더바로 변환
        safe_name = name.replace(" ", "_").replace("/", "_").replace("-", "_")
        print(f"    {safe_name}: Tuple[int, int]")
        
    print("\n\nclass NeisGuiConfig:")
    print("    fields = FieldCoords(")
    for name, x, y in results:
        safe_name = name.replace(" ", "_").replace("/", "_").replace("-", "_")
        print(f"        {safe_name}=({x}, {y}),  # {name}")
    print("    )")

if __name__ == "__main__":
    run_dynamic_calibration()
