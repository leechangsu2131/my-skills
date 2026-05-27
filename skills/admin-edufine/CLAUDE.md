# CLAUDE.md — 공문 자동화 프로젝트 핸드오프

> 이 파일은 IDE(Cursor / Windsurf / VS Code + Copilot 등)의 AI 에이전트에게
> 프로젝트 컨텍스트를 전달하기 위한 핸드오프 문서입니다.

---

## 프로젝트 개요

**목적**: 경상북도경주교육지원청 경주 화천초등학교 행정 업무 효율화
- 수신 공문(ODT 형식)을 파싱하여 핵심 메타데이터(공문번호, 일자, 제목 등)를 자동 추출
- 에듀파인(Edufine) 기안 화면에 해당 데이터를 Playwright로 자동 입력
- **사람이 직접 해야 하는 것**: 공동인증서 로그인, 기안 본문 작성·복붙, 최종 결재 상신

**운영 환경**: Windows 학교 PC / Python 3.10+

---

## 현재 완성된 코드

### `parse_gongmun.py`
ODT 공문 파싱 모듈 (완성, 테스트 통과)

**추출 가능 필드**:
| 필드 | 예시 값 | 변수명 |
|------|---------|--------|
| 시행 공문번호 | `교육지원과-15363` | `sihaeng_no` |
| 시행 일자 | `2026-04-03` | `sihaeng_date` |
| 접수 공문번호 | `화천초등학교-2813` | `jeopsu_no` |
| 접수 일자 | `2026-04-03` | `jeopsu_date` |
| 제목 | `[교부 안내] 2026년 학교 체육시설 개선 사업비 교부` | `제목` |
| 수신 | `수신자 참조` | `수신` |
| 발신처 | `경상북도경주교육지원청` | `발신처` |
| 관련 공문 | `[{번호, 일자}, ...]` | `관련공문` |

**사용법**:
```python
from parse_gongmun import parse_odt

result = parse_odt("path/to/공문.odt")
# result 예시:
# {
#   'sihaeng_no': '교육지원과-15363',
#   'sihaeng_date': '2026-04-03',
#   'jeopsu_no': '화천초등학교-2813',
#   'jeopsu_date': '2026-04-03',
#   '제목': '[교부 안내] 2026년 학교 체육시설 개선 사업비 교부',
#   '수신': '수신자 참조',
#   '발신처': '경상북도경주교육지원청',
#   '관련공문': [{'번호': '체육건강과-7694', '일자': '2026-04-02'}]
# }
```

---

## 다음 구현 목표 (IDE가 작업할 것)

### Phase 2 — `playwright_edufine.py`

에듀파인 기안 자동 입력 스크립트

**흐름**:
1. Playwright로 에듀파인 URL 열기
2. **로그인 화면에서 일시 정지** → 사용자가 공동인증서로 수동 로그인
3. 로그인 완료 감지 후 자동화 재개
4. 기안 메뉴 탐색 → 기안 양식 열기
5. 파싱된 데이터로 필드 자동 입력:
   - 제목 입력
   - 관련 공문번호 입력
   - 시행/접수 일자 입력
6. **본문 입력 필드에서 일시 정지** → 사용자가 직접 본문 붙여넣기
7. 스크립트 종료 (결재 상신은 사용자가 수동으로)

**구현 시 주의사항**:
- `playwright sync_api` 사용 (async 불필요)
- 로그인 완료 감지: `page.wait_for_url()` 또는 특정 DOM 요소 등장 감지
- 에듀파인 셀렉터는 iframe 중첩이 많으므로 `frame_locator` 적극 활용
- 입력 후 `page.wait_for_timeout(500)` 등 짧은 대기 필수 (느린 정부 시스템)
- 가상 키패드 비밀번호 입력은 자동화 대상 아님 (공동인증서 로그인은 수동)

**기본 골격**:
```python
from playwright.sync_api import sync_playwright
from parse_gongmun import parse_odt

def run(odt_path: str):
    data = parse_odt(odt_path)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://edufine.go.kr")  # 실제 경북 에듀파인 URL 확인 필요
        
        # 1. 로그인 대기 (사용자 수동 공동인증서 로그인)
        print("🔐 공동인증서로 로그인 후 Enter를 누르세요...")
        input()
        
        # 2. 기안 화면 이동
        # TODO: 실제 메뉴 셀렉터 확인 후 구현
        
        # 3. 필드 자동 입력
        # page.fill('#title', data['제목'])
        # page.fill('#ref_no', data['sihaeng_no'])
        # ...
        
        # 4. 본문 입력 대기
        print("📝 본문을 붙여넣은 후 Enter를 누르세요...")
        input()
        
        browser.close()

if __name__ == '__main__':
    import sys
    run(sys.argv[1])
```

### Phase 3 — `main.py` (통합 CLI)

```
사용법: python main.py 공문파일.odt
```

- ODT 파일 경로를 인자로 받아 파싱 → 결과 출력 → 에듀파인 자동 입력 실행
- 선택적으로 tkinter GUI로 파일 선택 다이얼로그 추가 가능

### Phase 4 (선택) — `gui_app.py`

- `tkinter` 또는 `PyQt6`로 간단한 GUI
- "ODT 파일 선택" 버튼 → 파싱 결과 미리보기 → "에듀파인 자동 입력 시작" 버튼

---

## 디렉토리 구조 (목표)

```
gongmun-auto/
├── CLAUDE.md               ← 이 파일
├── README.md
├── requirements.txt
├── parse_gongmun.py        ← ✅ 완성
├── playwright_edufine.py   ← 🚧 구현 필요
├── main.py                 ← 🚧 구현 필요
├── gui_app.py              ← 🔲 선택 구현
├── samples/
│   └── sample.odt          ← 테스트용 샘플 공문
└── tests/
    └── test_parse.py       ← 단위 테스트
```

---

## 의존성

```
# requirements.txt
playwright>=1.40.0
odfpy>=1.4.1
```

설치:
```bash
pip install playwright odfpy
playwright install chromium
```

---

## 핵심 제약사항 (절대 변경 금지)

1. **공동인증서 로그인은 자동화하지 않는다** — 사용자가 수동으로 진행
2. **결재 상신(최종 제출)은 자동화하지 않는다** — 사용자가 검토 후 수동 제출
3. **에듀파인 비밀번호를 코드에 하드코딩하지 않는다**
4. **개인정보·인증서 정보를 파일에 저장하지 않는다**

---

## 참고 URL (실제 접속 URL은 학교 환경에서 확인)

- 에듀파인: https://edufine.go.kr 또는 경북교육청 내부망 URL
- 나이스: https://nice.go.kr (현재 Phase에서는 대상 아님)

---

## 커밋 컨벤션

```
feat: 새 기능
fix: 버그 수정
refactor: 리팩토링
test: 테스트 추가
docs: 문서 수정
```
