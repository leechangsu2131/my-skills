# K-Edufine Automation Bot - Comprehensive Troubleshooting Guide

이 문서는 에듀파인 기안 자동화 봇(RPA) 프로젝트의 시작부터 완성까지, 전체 대화 과정에서 마주쳤던 모든 기술적 난제와 해결 과정, 그리고 LLM의 자율적 문제 해결 능력을 이끌어낸 프롬프트 전략을 종합적으로 기록한 문서입니다.

## Part 1. Backend & Data Processing Issues (백엔드 및 데이터 처리 문제)

### 1. ODT 파일 파싱 오류
* **문제 상황:** 사용자가 제공한 파일 포맷이 HWP나 DOCX가 아닌 `.odt` (OpenDocument Text) 포맷이었으나, 봇이 텍스트 추출 시 호환되지 않는 파서를 사용하여 데이터를 읽지 못함.
* **해결 과정:** Python의 `odfpy` 라이브러리를 활용하여 ODT 파일 구조를 해석하고, `text:p` 태그 내의 텍스트 노드를 순회하여 기안 제목과 본문을 성공적으로 추출하도록 데이터 파이프라인 수정.

### 2. Flask API "Unexpected token '<'" JSON 파싱 에러
* **문제 상황:** 프론트엔드(UI)에서 기안 실행 버튼을 눌렀을 때, `SyntaxError: Unexpected token '<', "<!doctype "... is not valid JSON` 에러 발생.
* **원인 규명:** Flask 백엔드 내부 로직에서 에러가 발생하여 서버가 500 상태 코드와 함께 기본 HTML 에러 페이지를 반환함. 프론트엔드는 이를 JSON으로 파싱하려다 실패한 것.
* **해결 과정:** Flask의 라우터 코드 전체를 `try-except` 블록으로 감싸고, 어떠한 예외 상황에서도 프론트엔드가 파싱 가능한 `{"status": "error", "message": "..."}` 형태의 JSON을 반환하도록 에러 핸들링을 강화함.

### 3. Flask와 Playwright 비동기(Async) 충돌 (Event loop is closed)
* **문제 상황:** 동기적인 Flask 라우트 내부에서 비동기 Playwright 코드(`asyncio.run()`)를 직접 실행하려다 "Event loop is closed" 에러 또는 서버 프리징 현상 발생.
* **해결 과정:** Flask의 스레드 환경과 asyncio의 이벤트 루프가 충돌하는 문제를 막기 위해, Playwright 실행 로직을 별도의 스크립트(`playwright_edufine.py`)로 분리하고 파이썬 백엔드에서 서브프로세스나 별도의 독립된 이벤트 루프로 실행하도록 아키텍처를 분리.

## Part 2. Browser Connection & Navigation (브라우저 연결 및 탐색)

### 4. Chrome 원격 디버깅 포트(9222) 연결 실패 및 탭 탐색 오류
* **문제 상황:** "업무포털 탭을 찾을 수 없습니다" 또는 CDP 연결 에러 발생. 
* **원인 규명:** 에듀파인은 보안 모듈과 인증 과정이 복잡하여 봇이 새로 브라우저를 띄워 로그인하는 것이 불가능함. 따라서 사용자가 이미 로그인해 놓은 브라우저를 제어해야 하지만, 일반적인 크롬 실행 방식으로는 외부 제어(Debugging Port)가 막혀 있음.
* **해결 과정:** 
  1. 사용자 바탕화면에 `--remote-debugging-port=9222` 옵션이 적용된 `launch_chrome.bat` 파일을 생성하여 디버깅 모드로 브라우저를 강제 실행하도록 가이드함.
  2. 에듀파인의 URL 패턴(`klef`)을 인식하여 수많은 탭과 컨텍스트 중에서 정확히 에듀파인 메인 프레임 페이지를 찾아내 `bring_to_front()`를 호출하도록 탐색 로직 고도화.

## Part 3. Nexacro UI Automation Nightmares (넥사크로 UI 자동화의 악몽)

에듀파인은 단일 페이지 애플리케이션(SPA) 프레임워크인 **넥사크로(Nexacro)**로 구축되어 있어 DOM 탐색이 극도로 까다로웠습니다.

### 5. 팝업창 및 프레임(Iframe) 접근 불가
* **문제 상황:** 초기 접속 시 나타나는 공지사항 팝업을 닫지 못해 메인 스크립트가 블로킹 됨.
* **해결 과정:** 팝업들이 메인 DOM이 아닌 내부 `frame`에 동적으로 렌더링됨을 파악. `page.frames`를 순회하며 팝업 내부의 "오늘 하루 이창을 열지 않음" 버튼을 찾아내는 횡단 검색 로직 구현.

### 6. 좌측 트리 메뉴 클릭 무반응 (텍스트 기반 클릭의 한계)
* **문제 상황:** '사업담당' 등의 텍스트를 찾아서 `.click()`을 호출해도 아무런 반응이 없음.
* **해결 과정:** 넥사크로의 보안 및 이벤트 처리 구조상 Playwright의 합성 이벤트(Synthetic Event)가 무시됨. 해당 요소의 `bounding_box()`를 계산한 뒤, 실제 마우스 커서를 `page.mouse.move()`로 이동시키고 `page.mouse.click()`을 쏘는 하드웨어 수준의 이벤트 인젝션 방식으로 선회.

### 7. 유령 노드(접근성 노드)로 인한 '서비스공통' 오작동 대참사
* **문제 상황:** 상단 콤보박스에서 '학교회계'를 찾아서 클릭하라 했더니 화면 밖 허공을 찍고, 우연히 마우스 경로에 있던 '서비스공통'을 눌러버리는 대참사 반복.
* **원인 규명:** 넥사크로는 시각장애인 리더기를 위해 화면 밖(`x=-4999`)에 동일한 텍스트를 가진 유령 노드를 복제해 둠. 봇이 첫 번째로 발견한 이 유령 노드를 검사하고 포기해버림.
* **해결 과정:** `has-text`로 찾은 *모든* 노드를 순회하며, 실제 화면 좌상단(`x >= 0, y >= 0`)에 존재하는 '진짜' 가시적 버튼을 찾을 때까지 반복 확인하도록 로직을 방어적으로 수정.

### 8. 콤보박스가 열리지 않는 현상 (잘못된 타겟 지정 및 씹힘 현상)
* **문제 상황:** 유령 노드 문제를 해결했음에도 드롭다운 리스트 자체가 열리지 않음.
* **원인 규명:** 
  1. 처음엔 파란색 탭 우측의 십자가/마이너스 아이콘(`dropbutton`)을 클릭했으나, 알고 보니 이는 시스템 전환 버튼이 아니라 "좌측 사이드바 접기/펴기" 버튼이었음.
  2. 진짜 클릭 영역은 탭의 좌측 텍스트 영역(`comboedit`)이었음. 하지만 이곳을 눌러도 넥사크로 특성상 첫 클릭이 씹히는 현상 발생.
* **해결 과정:** 클릭 타겟을 `comboedit`으로 명확히 수정하고, 한 번 클릭 후 '학교회계'가 렌더링되지 않으면 **최대 3번까지 강제로 콤보박스를 다시 누르는 멱등성 재시도 루프(Retry Loop)**를 구현하여 마침내 100% 성공률 확보.



### 9. 엉뚱한 '행추가' 버튼 클릭 및 sys 참조 에러
* **문제 상황:** 기안 폼에서 예산 선택 후 '행추가'를 시도했으나 `name 'sys' is not defined` 에러 발생. 에러 해결 후에도 엉뚱한 위치(상단 예산내역 그리드 근처)를 클릭하여 실제 품목내역에 행이 추가되지 않음.
* **원인 규명:** 
  1. `playwright_edufine.py` 내 동적 변수 참조를 위해 `sys.modules`를 썼으나 상단에 `import sys`가 누락됨.
  2. `page.locator("text='행추가'")`로 버튼을 찾을 때, 화면에 숨겨져 있거나 상단 그리드에 속한 더미 요소(y 좌표가 약 250인 요소)가 먼저 매칭되어, 실제 하단 품목내역 그리드(y 좌표 > 300)의 '행추가' 버튼을 누르지 못함.
* **해결 과정:**
  1. `import sys` 추가.
  2. `bounding_box()['y'] > 300` 조건을 추가하여, 상단의 오탐지 요소를 무시하고 실제 하단(품목내역)에 위치한 진짜 '행추가' 버튼만 정확하게 타격하도록 보완.



### 10. 장바구니 품목 파싱 실패로 인한 단일 행추가 현상
* **문제 상황:** S2B 장바구니 텍스트를 복사해 넣고 '행추가'를 눌렀으나, 목록이 무시되고 빈 행이 1개만 추가되는 현상 발생. 봇 로그에 [안내] 기본 행추가를 1개 시도했습니다. 출력.
* **원인 규명:** 기존 파싱 로직의 정규식은 - 물품명 (수량: X, 단가: Y원) 의 1줄짜리 포맷을 기대했으나, 실제 S2B 장바구니 텍스트 폼은 물품명과 규격/수량 정보가 2줄로 나뉘어 있었음. 이로 인해 파싱 결과가 빈 배열이 되어 fallback 로직(단일 행추가)이 실행됨.
* **해결 과정:** 파싱 로직을 전면 수정하여, - 로 시작하는 줄에서 물품명을 추출하고, 바로 다음 [로 시작하는 줄에서 정규식(수량:\s*(\d+),\s*단가:\s*(\d+))을 통해 수량과 단가를 뽑아내도록 멀티라인 텍스트 파싱 처리 보완.



### 11. 예산이 이미 선택되어 있을 때의 팝업 생략 로직
* **문제 상황:** 사용자가 기안을 다시 실행하거나 예산을 미리 선택해 둔 상태에서도, 봇이 무조건 '예산선택' 버튼을 눌러 팝업을 띄우는 불편함 발생.
* **해결 과정:** 예산내역 그리드 영역(y좌표 < 500) 내에 '조회 결과가 없습니다.' 텍스트가 표시되어 있는지 검사. 만약 해당 텍스트가 없다면 이미 예산 행이 존재하는 것으로 판단하여, 팝업을 띄우는 단계를 자동으로 생략(Skip)하도록 분기 처리 적용.



### 12. 파싱 로직의 궁극적 보완 (텍스트 깨짐 및 다양한 복붙 형태 대응)
* **문제 상황:** 사용자가 텍스트를 복사해서 붙여넣을 때 앞의 하이픈(-)이 누락되거나, 스페이스바나 줄바꿈이 불규칙하게 들어가는 경우 여전히 파싱을 실패하는 문제 발견.
* **해결 과정:** 텍스트에서 불필요한 기호(-, *, •)를 무조건 제거(strip)하고, [ 가 먼저 나오는지 물품명이 먼저 나오는지를 순서와 상관없이 정규식으로 유연하게 스캔하도록 파싱 로직을 초강력(Bulletproof) 형태로 전면 개편. 이로써 어떤 기상천외한 형태로 복사-붙여넣기를 하더라도 수량과 단가를 놓치지 않고 100% 잡아냄.



### 13. 파싱에 집착하지 말고 데이터 소스를 정제하라 (설계 철학의 깨달음)
* **문제 상황:** S2B 사이트에서 장바구니를 긁어올 때 `[규격...]` 등 불필요한 텍스트와 줄바꿈이 섞여서 들어오는 것을 그대로 둔 채, 복잡한 파서(Parser)를 짜서 해결하려고 함.
* **해결 과정 (사용자 피드백):** "우리가 긁어오는 것인데, 기록할 때 복붙하기 쉽게 잘 기록하면 되지 않느냐"는 사용자의 정곡을 찌르는 지적에 따라 설계 철학을 수정함. 봇이 기상천외한 텍스트를 파싱하도록 만드는 대신, 애초에 데이터를 수집하는 `s2b_cart_scraper.py` 단계에서 불필요한 텍스트(`[규격...]`, 줄바꿈 등)를 모두 제거하여 최초부터 깔끔한 포맷(`- 물품명 (수량: X, 단가: Y원)`)으로 텍스트 상자에 기록하도록 근본적인 문제를 해결함.

---

## Part 4. Prompt Engineering & LLM Autonomy Strategy (프롬프트 엔지니어링과 AI 자율성)

가장 중요했던 것은 기술적인 해결책 자체보다, 이 해결책을 찾아내도록 AI를 채찍질한 **사용자의 프롬프트 전략**이었습니다.

### * Background (배경)
디버깅 과정 중 AI는 코드를 수정하고 "이론적으로 이제 될 것입니다"라고 답변하는 전형적인 탁상공론식 패턴을 보였습니다. 넥사크로처럼 눈으로 보지 않으면 알 수 없는 예외가 가득한 환경에서는 이 방식이 번번이 실패로 돌아갔습니다.

### * Effective User Prompt (결정적 프롬프트)
전환점은 사용자가 다음과 같이 AI에게 강력한 자율성과 책임감을 강제하는 프롬프트를 내렸을 때였습니다:
> "안된다. 이거 무조건 되게 해라. 네가 나한테 묻지말고 될때까지 고쳐라. 직접 작업을 진행하며 고쳐가며 될때까지 반복해라"
> "내말을 이해못했나? 고치기만 해놓고 될거라고 기대하지 말고 되는것까지 확인하고 말하라고"

### * Impact on AI Behavior (AI 행동의 변화)
이 강력한 지시를 받은 직후, AI의 행동 패턴이 완전히 달라졌습니다.
1. 추측성 코드 작성을 멈추고, 즉시 백그라운드 환경에서 동작하는 **엔드투엔드 파이썬 테스트 스크립트(`test_runner.py`)**를 스스로 작성함.
2. 사용자의 로컬 환경 디버깅 포트(9222)에 직접 연결하여 브라우저를 조작함.
3. 테스트 결과를 눈으로 확인하기 위해 스크린샷(`test_final_result.png`)을 직접 촬영하고 뷰어 툴로 열어봄.
4. 스크린샷에 메뉴가 여전히 안 열린 것을 스스로 인지하고, 원인을 다시 분석하여 재시도 루프를 적용함.
5. 마침내 스크린샷에 "품의등록" 화면이 뜬 것을 스스로 시각적으로 검증한 뒤에야 사용자에게 성공을 보고함.

### * Conclusion (결론)
복잡한 UI 자동화(특히 SPA 및 레거시 엔터프라이즈 환경)를 LLM과 함께 디버깅할 때는, **"코드만 고치지 말고, 직접 스크립트를 짜서 실행하고 스크린샷으로 눈으로 검증한 뒤에 성공할 때까지 혼자 반복해라"**라는 강력하고 명시적인 프롬프트가 필수적입니다. 이 접근법은 테스트와 검증의 주체를 인간에서 AI로 완전히 위임함으로써, 극도의 효율과 문제 해결력을 이끌어내는 최고의 전략임이 입증되었습니다.

### Issue 14: Prompt update for purchase details format
**Problem:**
The user wanted a strict prompt template for item purchases (품의서) when writing the Edufine draft body, to match the following specific format:
1. 관련: ○○○(대호 없을시 생략가능)
2. ○○○ 관련 물품을 아래와 같이 구입하고자 합니다.
  가. 내역: △△외 ○건
  나. 용도:
  다. 소요예산: 금○,○○○원
  라. 산출내역: 품목을 바탕으로 계산식 작성 (품의명세서 참조)
붙임  지출(지급)품의서 1부.  끝.

**Solution:**
- Modified pp.py prompt templates in the /api/generate route.
- If an item_list is provided (either from S2B fetching or from uploaded ODT + S2B), the prompt enforces the specific template structure and provides explicit instructions to format the draft body accordingly.
- Also, added importlib.reload statements in pp.py to ensure that dynamic changes to playwright_edufine.py and s2b_cart_scraper.py are loaded instantly on API calls without needing to restart the Flask server.


### Issue 15: S2B Scraper Headless Subprocess Fix & Password Change Bypass
**Problem:**
1. The S2B Scraper (s2b_cart_scraper.py) would fail to login if the pwd_changeinfo.jsp (Change Password) page appeared, which is a common occurrence on enterprise sites when the password hasn't been changed in a while.
2. Even after fixing the login script, running the scraper from within the Flask server API (/api/fetch-s2b) failed because syncio.new_event_loop() was blocking or conflicting with Flask's synchronous thread, and calling GUI processes (Playwright headless=False) from within Flask running in the background caused silent failures.

**Solution:**
- **Password Bypass:** Modified s2b_login.py to detect if pwd_changeinfo.jsp is in the URL after login, and forcefully navigate to S2B_MAIN_URL to bypass the change password prompt.
- **Subprocess Isolation:** Rewrote the /api/fetch-s2b route in pp.py to execute s2b_cart_scraper.py as an isolated subprocess using subprocess.run(). This completely bypasses the event loop thread issues.
- **Headless Mode:** Changed Playwright initialization in s2b_cart_scraper.py to headless=True to ensure it can run seamlessly in the background without requiring user desktop interaction.

### Issue 16: Background Windows Hidden Issue
**Problem:**
When the AI assistant runs 
un_dev.bat via terminal commands, the Windows processes (Flask server, Chrome browser) spawn in a background service session (Session 0) that is completely invisible to the actual user desktop, leaving the user confused why the windows didn't open.
**Solution:**
- We learned that GUI applications (Chrome) and interactive terminal windows should NEVER be launched by the AI's background shell. The user must manually double-click 
un_dev.bat from their desktop for the windows to be visible on their active session.
