with open('troubleshooting.md', 'r', encoding='utf-8') as f:
    content = f.read()

addition = """

### 9. 엉뚱한 '행추가' 버튼 클릭 및 sys 참조 에러
* **문제 상황:** 기안 폼에서 예산 선택 후 '행추가'를 시도했으나 `name 'sys' is not defined` 에러 발생. 에러 해결 후에도 엉뚱한 위치(상단 예산내역 그리드 근처)를 클릭하여 실제 품목내역에 행이 추가되지 않음.
* **원인 규명:** 
  1. `playwright_edufine.py` 내 동적 변수 참조를 위해 `sys.modules`를 썼으나 상단에 `import sys`가 누락됨.
  2. `page.locator("text='행추가'")`로 버튼을 찾을 때, 화면에 숨겨져 있거나 상단 그리드에 속한 더미 요소(y 좌표가 약 250인 요소)가 먼저 매칭되어, 실제 하단 품목내역 그리드(y 좌표 > 300)의 '행추가' 버튼을 누르지 못함.
* **해결 과정:**
  1. `import sys` 추가.
  2. `bounding_box()['y'] > 300` 조건을 추가하여, 상단의 오탐지 요소를 무시하고 실제 하단(품목내역)에 위치한 진짜 '행추가' 버튼만 정확하게 타격하도록 보완.
"""

with open('troubleshooting.md', 'w', encoding='utf-8') as f:
    f.write(content.replace('---', addition + '\n---'))
