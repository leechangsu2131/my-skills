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
import os
import json
import pyautogui

CONFIG_FILE = "neis_gui_config.json"

def get_field_type():
    print("  [유형 선택]")
    print("  1: 단순 클릭 (click)")
    print("  2: 텍스트 입력 (text - 기존 내용 지우고 입력)")
    print("  3: 드롭다운 검색 (dropdown - 입력 후 Enter)")
    while True:
        choice = input("  → 유형 번호를 선택하세요 (기본 1): ").strip()
        if not choice or choice == "1":
            return "click"
        elif choice == "2":
            return "text"
        elif choice == "3":
            return "dropdown"
        else:
            print("  잘못된 입력입니다. 1, 2, 3 중에서 선택하세요.")

def run_new_calibration():
    print("\n=== [1] 새 캘리브레이션 만들기 ===")
    print("- 마우스를 원하는 위치에 올리고 [Enter]를 누르세요.")
    print("- 누른 직후 해당 위치의 '이름'과 '유형'을 입력받습니다.")
    print("- 모든 좌표를 다 찍었으면 [Ctrl + C]를 눌러 종료하세요.\n")

    steps = []
    
    try:
        count = 1
        while True:
            input(f"[{count}번째] 마우스를 위치시키고 Enter를 누르세요 (종료는 Ctrl+C)...")
            x, y = pyautogui.position()
            
            name = input(f"  → 방금 찍은 좌표({x}, {y})의 이름(용도)을 입력하세요: ").strip()
            if not name:
                name = f"field_{count}"
                
            field_type = get_field_type()
            
            steps.append({
                "name": name,
                "type": field_type,
                "x": x,
                "y": y,
                "text": ""
            })
            print(f"  ✅ 저장됨: {name} (유형: {field_type}) = ({x}, {y})\n")
            count += 1
            
    except KeyboardInterrupt:
        print("\n\n[입력 종료] 캘리브레이션을 마칩니다.")
    
    if not steps:
        print("입력된 좌표가 없어 취소합니다.")
        return

    save_config({"steps": steps})

def run_edit_calibration():
    print("\n=== [2] 기존 캘리브레이션 조회/수정 ===")
    if not os.path.exists(CONFIG_FILE):
        print(f"[{CONFIG_FILE}] 파일이 없습니다. 먼저 새 캘리브레이션을 진행해 주세요.")
        return
        
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception as e:
        print(f"파일을 읽는 중 오류가 발생했습니다: {e}")
        return
        
    steps = config_data.get("steps", [])
    if not steps:
        print("저장된 스텝이 없습니다.")
        return
        
    while True:
        print("\n--- 현재 저장된 스텝 목록 ---")
        for i, step in enumerate(steps):
            name = step.get('name', 'unnamed')
            ftype = step.get('type', 'click')
            text = step.get('text', '')
            x, y = step.get('x', 0), step.get('y', 0)
            print(f"[{i+1}] {name} | 유형: {ftype} | 텍스트: '{text}' | 좌표: ({x}, {y})")
            
        print("\n수정할 항목의 번호를 입력하세요.")
        print("종료하고 저장하려면 'q' 또는 '0'을 입력하세요.")
        choice = input("입력: ").strip()
        
        if choice.lower() in ['q', '0', '']:
            break
            
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(steps):
                print("잘못된 번호입니다.")
                continue
        except ValueError:
            print("숫자를 입력해 주세요.")
            continue
            
        step = steps[idx]
        print(f"\n[{idx+1}] {step['name']} 항목 수정 시작 (수동입력 시 기존값 유지)")
        
        # 이름 수정
        new_name = input(f"  새 이름 ({step['name']}): ").strip()
        if new_name:
            step['name'] = new_name
            
        # 텍스트 수정
        current_text = step.get('text', '')
        new_text = input(f"  새 텍스트 ({current_text}): ").strip()
        if new_text:
            step['text'] = new_text
            
        # 타입 수정
        current_type = step.get('type', 'click')
        print(f"  새 유형 지정 (현재: {current_type})")
        new_type = get_field_type()
        step['type'] = new_type
        
        # 좌표 재설정
        recap = input(f"  좌표를 다시 찍으시겠습니까? 현재({step['x']}, {step['y']}) (y/N): ").strip().lower()
        if recap == 'y':
            input("  마우스를 새로운 위치에 올리고 Enter를 누르세요...")
            x, y = pyautogui.position()
            step['x'] = x
            step['y'] = y
            print(f"  ✅ 새 좌표 설정 완료: ({x}, {y})")
            
        steps[idx] = step
        print("✅ 항목이 수정되었습니다.")

    config_data['steps'] = steps
    save_config(config_data)

def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        print("\n" + "="*50)
        print(f"🎉 성공적으로 `{CONFIG_FILE}` 파일에 저장되었습니다!")
        print("="*50 + "\n")
    except Exception as e:
        print(f"파일 저장 중 오류가 발생했습니다: {e}")

def main():
    while True:
        print("=====================================================")
        print(" 나이스(NEIS) 동적 GUI 캘리브레이션 툴")
        print("=====================================================")
        print(" 1. 새 캘리브레이션 만들기 (처음부터 다시 찍기)")
        print(" 2. 기존 캘리브레이션 조회 및 수정 (텍스트, 좌표, 유형 변경)")
        print(" 0. 종료")
        print("=====================================================")
        
        choice = input("선택하세요: ").strip()
        if choice == "1":
            run_new_calibration()
        elif choice == "2":
            run_edit_calibration()
        elif choice == "0" or choice.lower() == "q":
            print("종료합니다.")
            break
        else:
            print("잘못된 입력입니다.\n")

if __name__ == "__main__":
    main()
