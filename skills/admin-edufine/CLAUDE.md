# CLAUDE.md — K-에듀파인 실전 기안 자동화(RPA) 프로젝트 핸드오프

> 이 문서는 IDE(Cursor / Windsurf / VS Code + Antigravity 등)의 AI 에이전트와 개발자에게
> 에듀파인 실전 기안 자동화 프로젝트의 컨텍스트와 아키텍처를 전달하기 위한 핸드오프 문서입니다.

---

## 1. 프로젝트 개요 및 핵심 철학

**목적**: 경상북도경주교육지원청 경주 화천초등학교 행정 업무(K-에듀파인) 실전 자동화
- **공문 초안 작성(텍스트 생성)**은 LLM이 기본적으로 잘하므로, 본 프로젝트는 사람이 직접 하기 번거로운 **에듀파인 넥사크로 UI 상의 실제 기안/품의 조작(RPA)**을 핵심 목표로 함.
- 두 가지 기안 유형([트랙 1] 학교회계 품의 vs [트랙 2] 전자결재 공문 기안)의 시스템과 폼 구조가 완전히 다르므로 **분리된 독립 파이프라인**으로 운영.
- 넥사크로의 비동기 렌더링 및 보안 특성을 고려하여 **항시 클립보드 기반 수동 복붙 안전망(Fallback)** 유지.

**운영 환경**: Windows 학교 PC / Python 3.10+ / Chrome (CDP 포트 9222) / Flask

---

## 2. 완성된 핵심 모듈 구조

### [데이터 파싱 및 서식 엔진] `parse_gongmun.py`
- **지원 포맷**: ODT, HWPX(section xml/PrvText 파싱), TXT, 클립보드 직접 복사 텍스트
- **추출 필드**: 발신처, 시행번호/일자, 접수번호/일자, 마감일(제출기한), 관련공문 목록, 제목
- **주요 함수**:
  - `parse_document(filepath: str) -> dict`: 확장자별 자동 분기 파서
  - `parse_text_data(lined_text: str) -> dict`: 순수 텍스트 정규식 파서
  - `generate_edufine_draft(parsed_data, custom_memo="", item_list="") -> dict`: K-에듀파인 표준 규격(`1. 관련... 2. ... 끝.`) 또는 S2B 품의명세서 양식으로 기안 제목 및 본문 자동 조립

---

### [트랙 1] 학교회계 품의등록 RPA: `playwright_edufine.py`
- **목표 화면**: `[학교회계]` 시스템 $\rightarrow$ `사업관리` $\rightarrow$ `사업담당` $\rightarrow$ `품의등록`
- **핵심 메커니즘**:
  - `navigate_to_draft_page(page)`: 상단 시스템 콤보박스 타격 및 학교회계 메뉴 전환
  - `close_popups(page)`: 공지사항 팝업 프레임 순회 닫기
  - `add_item_rows(page, items)`: 품목내역 그리드(`y > 300`)의 진짜 '행추가' 버튼 타격 후 셀 편집 모드 진입, 수량·단가 자동 타이핑
  - `hover_and_click(page, selector)`: 넥사크로의 가상 접근성 노드(`x < 0`)를 배제하고 실제 화면 좌표(`x >= 0, y >= 0`)를 계산해 마우스 물리적 이동 및 클릭 수행

---

### [트랙 2] 전자결재 공문 기안 RPA: `playwright_gongmun_draft.py` (신규 완성)
- **목표 화면**: `[업무관리]` 시스템 $\rightarrow$ `문서관리` $\rightarrow$ `기안` $\rightarrow$ 공용기안문 팝업
- **핵심 메커니즘**:
  - `find_edufine_page(browser)`: 열려있는 브라우저에서 K-에듀파인 탭 감지
  - `switch_to_work_management(page)`: 업무관리 시스템 확인 및 전환
  - `navigate_to_gongmun_menu(page)`: 좌측 트리에서 [문서관리] $\rightarrow$ [기안] 클릭
  - `open_draft_popup(page)`: [공용기안문] 또는 [기안] 버튼 클릭으로 기안기 새 창 호출
  - `fill_draft_content(page, title, body)`:
    - 1) 제목 필드(`width > 250`) 탐색 및 타이핑
    - 2) 웹한글 기안기 영역을 찾아 클릭 후 `set_clipboard_text(body)` $\rightarrow$ `page.keyboard.press("Control+V")` 이벤트로 본문 주입
  - **안전망**: 봇 시작 즉시 Windows API(`ctypes`)를 통해 클립보드에 본문을 우선 복사하여, 실패 시 사용자가 `Ctrl+V`로 즉시 해결 가능

---

### [트랙 3] 에듀파인 수신공문 검색 & 새창 열람 RPA: `playwright_gongmun_search.py` (신규 완성)
- **목표 화면**: `[업무관리]` $\rightarrow$ `문서관리` $\rightarrow$ `문서함` $\rightarrow$ `문서등록대장`
- **핵심 메커니즘**:
  - `ensure_edufine_opened(browser)`: K-에듀파인 탭이 닫혀있으면 포털에서 새 탭으로 자동 호출
  - `dismiss_notices_and_popups(page)`: 공지사항 팝업(`noticePopup0`) 및 확인 다이얼로그 자동 감지 및 닫기
  - `navigate_to_doc_register(page)`: 좌측 LNB 트리에서 `문서함` 폴더 클릭(확장) $\rightarrow$ `문서등록대장` 클릭
  - `search_gongmun(page, target_frame, keyword)`: 검색어 필드(`#basicSj`)에 키워드 주입 후 조회(`#searchDocBtn`) 클릭, 결과 테이블(`#tbList`) 실시간 파싱
  - `open_gongmun_popup(page, target_frame, row_index)`: 검색된 문서의 제목 링크를 트리거하여 WXSClient(네이티브 전자문서 뷰어 새창) 즉시 호출
- **철학**: "기안문 작성은 LLM이 하고, 에듀파인 공문 검색/열람은 봇이 전담"하는 역발상 자동화 파이프라인

---

### [웹 제어 대시보드] `app.py` & `templates/index.html` (Edufine Flow V5)
- 포트 `5030`에서 구동되는 다크 테마 글래스모피즘 웹 인터페이스.
- **주요 엔드포인트**:
  - `POST /api/upload-and-parse`: 파일 업로드 또는 텍스트 수신 $\rightarrow$ 즉시 파싱 & 초안 반환
  - `POST /api/start-gongmun-draft`: **[트랙 2]** 전자결재 공문 기안 봇 백그라운드 구동
  - `POST /api/start`: **[트랙 1]** 학교회계 품의등록 봇 백그라운드 구동
  - `GET /api/stream`: 작업 진행 로그 실시간 SSE 전송
  - `POST /api/fetch-s2b`: S2B 장바구니 품목 자동 스크래핑
- **프론트엔드 기능**:
  - 파일 드래그 앤 드롭 업로드 영역 (ODT / HWPX)
  - 공문 핵심 메타데이터 칩 (발신처, 공문번호, 일자, 마감일) 실시간 렌더링
  - `[트랙 2 기안 실행 ▶]` 및 `[트랙 1 품의 실행 ▶]` 분리 버튼
  - 상시 노출되는 `[📋 본문 복사 (안전망)]`, `[📋 전체 복사]` 버튼
  - 창 복귀 시 클립보드 자동 분석 (Auto-watch) 모드 지원

---

## 3. 실행 및 연동 규칙

### Chrome 원격 디버깅 (포트 9222)
- 에듀파인은 공인인증서 및 KCaseAgent/MarkAny DRM이 상시 실행되어야 하므로, 봇이 크롬을 임의로 새로 띄우면 보안 모듈이 차단됨.
- 따라서 반드시 **사용자의 실제 프로필을 연동하는 `launch_chrome_default.bat`**으로 크롬을 실행해야 함.
- CDP 접속 주소는 반드시 `http://127.0.0.1:9222` 사용 (`localhost` 사용 시 Windows IPv6 `::1` 바인딩 거부 에러 주의).

### 에듀파인 넥사크로(Nexacro) 다룰 때의 원칙
1. 합성 이벤트(`.click()`) 대신 반드시 실제 화면 좌표(`bounding_box()`)를 찾아 `page.mouse.move()` $\rightarrow$ `page.mouse.click()` 사용.
2. `x < 0` 또는 `y < 0`인 시각장애인 접근성 유령 노드는 무조건 필터링.
3. 콤보박스나 드롭다운 메뉴는 1회 클릭 시 씹힐 수 있으므로 최소 2~3회 재시도 루프(Retry Loop) 적용.
4. 웹한글 기안기 내부 입력은 DOM 조작보다 **클립보드 복사 후 `Control+V` 키 전송** 방식이 서식 깨짐 없이 가장 안전함.
5. **WXSClient 호출 원칙**: 공문 뷰어나 기안 팝업(`fncFormDraft`, `doCallClientAppExtra`)은 iframe 보안 제약으로 `.click()` 대신 반드시 **`targetWin.eval(onclickCode)`**를 통해 프레임 컨텍스트에서 직접 호출해야 100% 프로세스가 기동됨.
6. **CDP 초고속 통신**: 브라우저 레벨 웹소켓 연결이 지연될 경우, `http://127.0.0.1:9222/json`에서 `type == 'page'`인 메인 탭 WebSocket URL을 찾아 `websockets` 라이브러리로 직접 JSON-RPC(`Runtime.evaluate`)를 쏘는 직결 방식을 사용 (지연시간 0.01초).
7. **시스템 전환(`학교회계` $\leftrightarrow$ `업무관리`)**: `TopFrame.form.cboJobList`의 `set_index()`, `set_value()` 주입 후 `ItemChangeEventInfo` 객체로 `cboJobList_onitemchanged` 핸들러를 수동 발행하여 화면 리로드 없이 즉시 전환.
8. **메뉴 직접 오픈**: LeftFrame의 `gfnOpenMenu(menuId)` (예: 공용서식 `A00AAB0101001`, 문서등록대장 `A00AAB0107001`)를 호출하면 복잡한 트리 메뉴 탐색 없이 화면 탭을 즉시 오픈 가능.
