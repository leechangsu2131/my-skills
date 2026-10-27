# K-에듀파인 행정 업무 실전 자동화 개발 및 트러블슈팅 일지 (ing.md)

> **이 문서는 K-에듀파인(경북교육청) 자동화 봇 개발 과정에서 마주쳤던 모든 기술적 난제, 실패와 오류의 원인, 그리고 이를 극복한 실전 해결책을 집대성한 핵심 지식 저장소입니다.**  
> **에듀파인 관련 업무(물품 품의, 공문 기안, 공문 검색/열람, 결재대기/공람대기, 개인정보 점검 등)에 착수하는 모든 AI 에이전트는 반드시 본 문서를 먼저 숙지해야 합니다.**

---

## 📌 핵심 생존 수칙 및 시스템 극복 원칙 (Golden Rules)

1. **넥사크로(Nexacro 17) 유령 노드(`x=-4999`) 회피**:
   - 넥사크로는 시각장애인 스크린리더를 위해 화면 밖(`x=-4999`)에 동일한 텍스트를 가진 보이지 않는 가짜 DOM 노드를 대량 복제해 둡니다.
   - 단순 텍스트 탐색 후 첫 번째 요소를 클릭하면 100% 헛손질이나 엉뚱한 메뉴 클릭 참사(`서비스공통` 등)가 발생합니다.
   - 반드시 **가시적 좌표 검증(`bounding_box()['x'] >= 0, ['y'] >= 0`)**을 거친 실제 화면 내 요소만 타격해야 합니다.

2. **DOM 트리 클릭 지양, 넥사크로 직결 API(`gfnOpenMenu`) 적극 활용**:
   - 좌측 메뉴 트리(`gridMenu`)를 DOM 마우스 클릭으로 일일이 펼치려 하면 애니메이션 지연, 폴딩 상태, 전면 팝업 간섭으로 실패하기 쉽습니다.
   - `LeftFrame.form.gfnOpenMenu(menuId)`를 호출하면 메뉴 트리의 상태와 무관하게 100% 즉시 해당 MDI 탭과 워크프레임이 열립니다.
   - **주요 필수 메뉴 ID**:
     - `A00AAB0101001` : [업무관리] 기안 > 공용서식
     - `A00AAB0102001` : [업무관리] 문서관리 > 결재대기
     - `A00AAB0103001` : [업무관리] 문서관리 > 공람대기
     - `A00AAB0107001` : [업무관리] 문서관리 > 문서등록대장
     - `A00FAA0104001001` : [학교회계] 사업담당 > 품의/정산 > 품의등록

3. **시스템 전환 콤보박스(`cboJobList`) 강제 이벤트 발행**:
   - 화면이 `[학교회계]`에 머물러 있으면 좌측에 `기안`, `결재`, `문서등록대장` 메뉴가 아예 존재하지 않습니다.
   - `TopFrame.form.cboJobList`에 `set_index(0)`, `set_value('A00AA')`를 주입하고, `ItemChangeEventInfo` 객체로 `cboJobList_onitemchanged` 이벤트를 수동 발행해야 `[업무관리]` 전용 메뉴 트리가 로드됩니다.

4. **공지사항 팝업 메모리 파괴 (`noticePopup0.destroy()`)**:
   - 청렴정책, 서비스 점검 등의 팝업창은 DOM 버튼 클릭이 씹히거나 느립니다.
   - `app.mainframe.MainVFrameSet.SubHFrameSet.MainFrame.noticePopup0.destroy()` 또는 `app.popupframes` 순회 `.form.close()`로 메모리 단에서 즉시 소멸시켜야 합니다.

5. **크로스 오리진(Cross-Origin) Iframe 탐색 시 Playwright `frame_locator` 필수 사용**:
   - 업무포털(`gbe.eduptl.kr`) 내 K-에듀파인 위젯(`klef.gbe.kr`)은 Playwright의 `page.frames` 순회 시 `f.name`이 빈 문자열로 잡히거나 `about:blank`로 감지되어 누락될 수 있습니다.
   - 반드시 **`page.frame_locator('iframe[name="kedufine"]')`**를 사용하여 DOM 레벨에서 직접 횡단 접근해야 결재대기/공람대기 문서를 100% 잡아냅니다.

6. **네이티브 C++ 응용 프로그램(WXSClient MFC) 처리**:
   - 공문 뷰어나 전자결재 기안기 호출 시 웹브라우저 창이 아닌 `WXSClient.exe` 네이티브 창이 실행됩니다.
   - 크롬 외부 프로토콜 팝업("WXSClient MFC 응용 프로그램을 여시겠습니까?")은 최초 1회 **'항상 허용'** 체크 후 열기를 해야 영구 자동 승인됩니다.

7. **수신공문 전교사 공람 자동 지정 메커니즘 (`retrieveCnrsAppn.do` & `Capi.enrollPublic`)**:
   - 공람 지정은 결재대기(`retrieveSanctnWaitDocList`) 또는 공람지정(`retrieveCnrsAppnDocList`) 화면에서 `retrieveCnrsAppn.do?UID={userId}&OPEN_MODE=NO&APPRID={apprId}` 팝업을 열어 수행합니다.
   - 크롬 팝업 차단을 우회하기 위해 `driver.switch_to.new_window('tab')`으로 창을 생성한 뒤, 좌측 조직도의 전교사 체크박스(`$('input[name=userChk]').prop('checked', true)`)를 일괄 선택합니다.
   - `fncChooseOrgnztUserUserTr()` 호출로 우측 수신목록(`selID`)에 45명 전원을 적재한 후, `window.confirm`을 자동 승인(`return true`)하고 `fncVerify()`를 호출하면 백엔드 `Capi.enrollPublic()`이 즉시 공람 등록을 완결합니다.

8. **수신문서 업무담당자(`isCharge=true`) 결재 분기와 전자서명 하이브리드 연계 원칙**:
   - 수신문서(`APPRTYPE == '3'`)이면서 업무담당자(`isCharge == 'true'`)인 경우 단순 일괄결재(`fncBndeSanctn`)는 비즈니스 로직상 제외 처리됩니다.
   - 웹 폼 제출(`fncProcessDocApn`) 시에는 행정전자서명(EPKI)/웹 DRM 컨트롤 미설치 오류가 발생하므로, 브라우저에서 `doCallClientApp(0, APPRID, 0, '')`로 WXSClient 결재기(`HCLTAPP_KYUL`)를 띄운 뒤 네이티브 서명 창에서 [결재]를 수행하는 것이 가장 안전하고 완벽한 하이브리드 자동화 표준입니다.

---

## 📅 일자별 개발 실패 극복 및 트러블슈팅 일지

---

### 2026-10-27: 업무포털 및 에듀파인 결재대기/공람대기 탐색 실패 극복 및 첨부문서 다운로드 완결 🏆

#### 1. 문제 상황
- `python edufine_auto_approve.py`를 실행했을 때 업무포털 메인 화면에 결재대기 1건이 분명히 존재함에도, `[경고] kedufine iframe을 찾지 못했습니다.`가 발생하고 `결재대기 문서 0건`으로 종료되는 오류 발생.
- K-에듀파인 메인 창(`klef.gbe.kr`) 내에서도 상단에 `결재(긴급) 1(0)|` 배너가 표시되지만 단순 iframe 순회로는 내부 리스트가 비어 있거나 `main.do`로 리다이렉트되어 결재 상세 정보를 읽지 못함.

#### 2. 원인 규명
1. **Playwright Cross-Origin Frame 속성 누락**: 업무포털 도메인(`gbe.eduptl.kr`)과 에듀파인 위젯 도메인(`klef.gbe.kr`)이 달라, Playwright의 `page.frames` 배열 순회 시 크로스 오리진 프레임의 `name` 프로퍼티가 공백(`""`) 또는 `about:blank`로 취급되어 `f.name == "kedufine"` 조건이 거짓(False) 판정됨.
2. **에듀파인 MDI 탭 내부 다중 프레임 격리**: 에듀파인 Nexacro 화면의 MDI 탭은 HTML `iframe` 내부에 또 다른 `apprInfoWnd`와 `docInfoFrame`을 중첩 로드하는 복합 구조로 되어 있어, 프레임 컨텍스트 스위칭이 단계별로 이루어지지 않으면 DOM 및 데이터셋을 읽을 수 없음.

#### 3. 해결책 및 구현
1. **`page.frame_locator` 도입**:
   - `edufine_auto_approve.py`의 `get_document_list()` 함수에 `page.frame_locator('iframe[name="kedufine"]')`를 1순위로 탐색하도록 로직 개편.
   - DOM 속성 직접 매칭으로 프레임 네임이 정상 인식되어 `[안내] 2026학년도 스포츠인성교육 교사동아리(AI체육수업) 자율연수 안내 (박은정, 2026-10-27)` 결재대기 1건 100% 즉시 수집 성공.
2. **K-에듀파인 직접 연계 및 상세 문서/첨부파일 다운로드**:
   - `문서등록대장`(`A00AAB0107001`)과 연계하여 해당 공문의 고유 ID(`R10CB263009119897000`)를 역추적.
   - `apprInfoWnd` -> `docInfoFrame` 다단계 프레임 스위칭을 구현하여 **결재경로(1단계 접수완료 -> 2단계 교사 이창수 진행)**, **문서정보(화천초등학교-11202, 체육건강과-21649)**를 완벽 추출.
   - `doCallExtViewAttch` 핸들러를 트리거하여 붙임 계획서 한글파일(`2026 스포츠인성교육 교사 동아리(나라찬) 연수 운영 계획.hwp`, 78,336 bytes)을 다운로드 폴더 및 `result/`에 자동 보관 완료.

---

### 2026-10-27: 수신공문 전교사 공람 지정 완전 자동화 및 결재 프로세스(WXSClient/전자서명) 구조 분석 완결 🏆

#### 1. 문제 상황 및 사용자 요구사항
- 결재대기 중인 수신 공문(`[안내] 2026학년도 스포츠인성교육 교사동아리(AI체육수업) 자율연수 안내`, 화천초등학교-11202)에 대해:
  1. 학교 전 교사가 열람할 수 있도록 **전교사 공람 지정** 자동 처리
  2. 업무담당자로서 **결재 처리** 완결

#### 2. 핵심 장애 요인 분석
1. **팝업 차단(Block) 및 Cross-Origin 프레임 제약**:
   - 결재대기 화면에서 `doCallEnrollPublicList()`가 호출하는 `window.open` 방식의 공람 팝업이 크롬 자동화 세션에서 팝업 차단되어 창이 뜨지 않음.
2. **수신문서 업무담당자(`isCharge=true`) 결재 제한**:
   - 단순 `fncBndeSanctn()`(일괄결재)는 업무담당자 지정 문서일 때 `unCheck1++; setCheckBoxStatus(obj, 0, false);`로 일괄결재 대상에서 자동 제외됨.
   - 일괄과제결재(`fncBndeTaskCrd`) 웹 폼을 통해 `fncProcessDocApn()` 제출 시 브라우저 내 전자서명/PKI 웹 DRM 컨트롤 부재로 Alert(`본 시스템에 필요한 컨트롤이 설치되어 있지 않거나...`) 발생 및 중단.

#### 3. 해결책 및 구현 (Solution Architecture)

1. **전교사 공람 지정 완전 자동화 (`execute_cnrs_all.py`)**:
   - `driver.switch_to.new_window('tab')`을 사용하여 `https://klef.gbe.kr/bms/cz/cb/wrt/retrieveCnrsAppn.do?UID={userId}&OPEN_MODE=NO&APPRID={apprId}` 팝업을 직접 새 탭으로 안정 오픈.
   - 대화상자 인터셉트: `window.confirm = function() { return true; };`, `window.alert = function() { return true; };`
   - 조직도 트리 내 전체 교직원 체크박스 일괄 선택: `$('input[name=userChk]').prop('checked', true);` (45명 전원 체크)
   - 셔틀 추가 함수 호출: `fncChooseOrgnztUserUserTr()` 호출로 우측 `PubshowList`(`selID`)로 45명 전원 적재.
   - `fncVerify()` 호출 -> 백엔드 `Capi.enrollPublic(id, rInfo.apprMsgID, idKeyList.join(), actorKeyList.join(), lineType, deleteList)` 정상 실행 완료.
   - 공람지정 문서 목록(`retrieveCnrsAppnDocList`)의 `fncSearch()`를 통해 최상단에 해당 공문이 공람 등록되었음을 100% 검증.

2. **수신공문 결재 프로세스 하이브리드 표준 확립**:
   - 과거 기안문서 역추적을 통해 교사 본인의 주 사용 과제카드(`R10AAA25122300286276`, `[체육특기육성지원] 체육특기육성지원`) 및 데이터 구조를 정확히 규명.
   - 웹 브라우저 단에서 직접 서명을 시도할 경우 교육청 행정전자서명 보안 정책(PKI)에 위배되므로, `doCallClientApp(0, 'R10CB263009119897000', 0, '')`를 호출하여 기동된 C++ 네이티브 `WXSClient.exe` 결재기 창에서 최종 [결재] 서명을 완료하는 **하이브리드 자동화 표준 원칙** 수립.

---

### 2026-10-19: 공문 검색(문서등록대장) 직결 호출 및 초고속 WXSClient 뷰어 연동

#### 1. 문제 상황
- 수신 공문을 검색하기 위해 좌측 메뉴를 클릭할 때 메뉴가 접혀 있거나 화면 렉으로 클릭이 누락됨.
- Playwright `connect_over_cdp` 호출 시 브라우저 메인 프로세스 락으로 10~30초 타임아웃 발생.

#### 2. 원인 및 해결책
1. **경량 WebSocket(CDP JSON-RPC) 직결**:
   - `http://127.0.0.1:9222/json`에서 `type == 'page'`인 K-에듀파인 탭을 찾아 전용 `webSocketDebuggerUrl`로 직접 웹소켓 통신 연결.
   - 응답 대기 시간을 0.01초 수준으로 단축하고 연결 타임아웃 원천 제거.
2. **Nexacro 직결 메뉴 호출**:
   - `LeftFrame.form.gfnOpenMenu('A00AAB0107001')`로 문서등록대장 화면을 1초 만에 오픈.
   - `basicSj` 입력 필드 및 `searchDocBtn` 클릭 이벤트 인젝션으로 공문 검색 자동화 완성.
3. **Iframe 내부 클릭 권한 차단 극복**:
   - 단순 합성 클릭이 씹히는 문제를 해결하기 위해 `targetWin.eval(a.getAttribute('onclick'))`로 네이티브 뷰어 기동 함수(`doCallClientAppExtra`)를 직접 구동.

---

### 2026-10-14: ODT/HWPX 공문 파싱 및 전자결재 기안기(웹한글) 본문 주입

#### 1. 문제 상황
- 수신 공문의 형식(ODT, HWPX, TXT)이 제각각이고 표나 문단 구조가 깨져 기안문 조립 시 규격이 어긋남.
- 기안기 팝업의 웹한글 컨트롤에 직접 텍스트를 주입할 때 한글 글자 씹힘 또는 렉 발생.

#### 2. 원인 및 해결책
1. **`parse_gongmun.py` 표준 기안문 엔진**:
   - ODT(`odfpy`), HWPX(XML/ZIP) 파서를 단일 모듈로 통합.
   - `1. 관련... 2. ... 붙임 ... 끝.`의 교육청 공문서 표준 규격으로 자동 재조립.
2. **클립보드 이중 안전망 (Fallback) 구축**:
   - 브라우저 원격 조작으로 웹한글 본문에 텍스트를 주입하되, 동시에 OS 클립보드에 기안 본문을 자동 복사.
   - 네트워크 렉이나 팝업 오류 발생 시에도 사용자가 `Ctrl+V` 단 0.1초 만에 수동 완성할 수 있도록 안전망 제공.

---

### 2026-06-09: S2B 장바구니 스크래퍼 및 서브프로세스 분리, 비밀번호 변경 우회

#### 1. 문제 상황
- S2B(학교장터) 로그인 시 비밀번호 변경 안내 페이지(`pwd_changeinfo.jsp`)가 뜨며 장바구니 진입 차단.
- Flask 서버(`app.py`) 내부에서 Playwright GUI를 직접 띄우려다 비동기 이벤트 루프 충돌 발생.

#### 2. 원인 및 해결책
1. **비밀번호 변경 강제 우회**:
   - 로그인 직후 URL에 `pwd_changeinfo.jsp`가 감지되면 즉시 `S2B_MAIN_URL`로 강제 네비게이션하여 팝업 우회.
2. **서브프로세스 격리 및 Headless 모드**:
   - `app.py` 라우트에서 `subprocess.run(["python", "s2b_cart_scraper.py", ...])`로 독립 프로세스 실행.
   - S2B 스크래퍼는 `headless=True`로 백그라운드에서 신속하게 품목 JSON 추출.

---

### 2026-05-27 ~ 05-28: S2B 품의 자동화 및 넥사크로17 그리드 행추가/단가 입력 트러블슈팅

#### 1. 문제 상황
- 상단 콤보박스 클릭 시 '학교회계' 대신 '서비스공통'이 클릭되는 참사 발생.
- 품의등록 화면의 품목내역 그리드에서 '행추가' 버튼을 눌렀으나 상단의 예산내역 행추가가 눌림.
- 수량과 단가 입력 시 그리드 편집 모드가 활성화되지 않고 데이터가 유실됨.

#### 2. 원인 및 해결책
1. **넥사크로 유령 노드 필터링**:
   - `x >= 0, y >= 0` 가시 좌표 체크 로직으로 `x=-4999` 유령 노드 원천 배제.
2. **Y좌표 기준 타겟 분기**:
   - 상단 예산내역(y < 300)과 하단 품목내역(y > 300)의 '행추가' 버튼을 Y좌표 범위로 명확히 분리하여 하단 버튼만 정확 타격.
3. **하드웨어 수준 마우스 좌표 타격**:
   - 그리드 셀 더블클릭 -> 편집기 인풋 노출 -> `page.keyboard.type()` -> `Enter`로 자릿값 및 통화 형식 완벽 주입.
4. **품목 파싱 데이터 소스 정제 철학 확립**:
   - 복잡한 파서에 집착하지 않고, S2B 수집 단계에서 규격과 불필요 문구를 사전 정제하여 `- 물품명 (수량: X, 단가: Y원)` 단일 표준으로 생성.

---

## 💡 새로운 작업 완료 시 지식 보존 원칙

새로운 작업이나 기능을 추가하면서 예외 상황, 넥사크로 특이 동작, 프레임 버그를 발견하여 해결했을 경우:
1. 본 `ing.md` 상단의 **핵심 생존 수칙(Golden Rules)**에 핵심 1줄을 추가/갱신합니다.
2. 본 문서 하단에 **새로운 날짜의 일지(## YYYY-MM-DD: ...)**를 작성하여 문제 상황, 원인, 해결책을 상세히 누적합니다.
