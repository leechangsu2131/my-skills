"""
나이스(NEIS) 동적 GUI 좌표 캘리브레이션 툴
==============================================
자유롭게 원하는 만큼 마우스 좌표를 찍고, 각각의 이름을 부여하여
`neis_gui_config.json` 형태의 설정 파일로 자동 저장해주는 스크립트입니다.

사용법:
1) python neis_apply_gui_setup.py 실행
2) 원하는 위치에 마우스를 올리고 Enter 누르기
3) 해당 좌표의 이름(용도) 입력하기
4) 완료되었으면 Ctrl+C를 눌러 종료 (자동으로 파일로 저장됨)
"""

import sys
import json
import pyautogui

def run_dynamic_calibration():
    print("=====================================================")
    print(" 나이스(NEIS) 동적 GUI 캘리브레이션 시작")
    print("=====================================================")
    print("- 마우스를 원하는 위치에 올리고 [Enter]를 누르세요.")
    print("- 누른 직후 해당 위치의 '이름(용도)'을 입력받습니다.")
    print("- 모든 좌표를 다 찍었으면 [Ctrl + C]를 눌러 종료하세요.")
    print("  (종료 시 지금까지 찍은 좌표들이 `neis_gui_config.json`에 자동 저장됩니다.)")
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

    # JSON 파일로 저장
    config_data = {"steps": []}
    
    for name, x, y in results:
        config_data["steps"].append({
            "name": name,
            "x": x,
            "y": y,
            "text": ""  # 사용자가 나중에 JSON에서 직접 채울 수 있도록 빈 칸으로 둠
        })
        
    try:
        with open("neis_gui_config.json", "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        print("\n\n" + "="*50)
        print("🎉 성공적으로 `neis_gui_config.json` 파일에 저장되었습니다!")
        print("이제 해당 파일을 열어서 `text` 항목에 입력할 텍스트 내용을 채워주세요.")
        print("입력할 텍스트가 없다면(단순 클릭) 빈칸(\"\")으로 두시면 됩니다.")
        print("스크롤이 필요한 경우 `text`에 `SCROLL_DOWN_3`을 입력하세요.")
        print("="*50 + "\n")
    except Exception as e:
        print(f"파일 저장 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    run_dynamic_calibration()
