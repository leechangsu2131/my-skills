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

9. **Playwright `connect_over_cdp` 전체 브라우저 락 회피**:
   - Chrome 9222에 Playwright를 직접 붙이면 메인 프로세스 락으로 수십 초~무한 대기가 발생할 수 있습니다.
   - `http://127.0.0.1:9222/json`에서 `type==page`(및 필요 시 `type==iframe`)의 `webSocketDebuggerUrl`로 경량 WebSocket 통신을 하거나 Selenium 디버거 주소 매핑을 활용합니다.

10. **결재대기 HTML 경로 (`viw`, 포털 Nice 위젯)**:
    - 결재대기 본화면: `https://klef.gbe.kr/bms/cz/cb/viw/retrieveSanctnWaitDocList.do?leftMenu=1` (`wrt/` 경로는 404).
    - 업무포털 위젯은 교차출처 OOPIF `retrieveSanctnWaitDocListNice.do`이며, 위젯 목록과 본화면 조회 결과가 어긋날 수 있습니다. 최종 건수는 본화면 `fncSearch()` 결과를 따릅니다.
    - 공람대기: `https://klef.gbe.kr/bms/cz/cb/viw/retrieveCnrsWaitDocList.do?MENU_ID=A00AAB0103001&FILE_ID=AABCnrsWaitDocList&alimZon=alimZon`

11. **결재대기 수신문서 본문(ODT) 직접 다운로드 및 고품질 PDF 변환 파이프라인**:
    - 결재대기(`retrieveSanctnWaitDocList`) 하단의 `apprInfoWnd` -> `docInfoFrame` 콘텍스트에서 `/bms/cz/cb/viw/retrieveViwAtchmnfl.do`에 `POST`로 `USERID, APPLID, APPRDEPTID, DOCID, OBJID=aid[:-3]+'001', FILENAME='결재문서본문.odt', FTYPE='01', ORDER='1'`를 전송하면 원본 규격 ODT 파일을 직결 다운로드할 수 있습니다.
    - 다운로드한 ODT 파일은 Windows COM 자동화(`Word.Application` 또는 `HWPFrame.HwpObject`)를 통해 서식 손실 없이 즉시 고품질 PDF로 변환 보관할 수 있습니다.
    - 다중 문서 팝업 순회 시 `driver.close()` 직후 반드시 `driver.switch_to.window(main_handle)`를 호출해야 연속 창 생성 시 `NoSuchWindowException` 에러를 원천 방지할 수 있습니다.


12. **개산금정산 그리드 셀 입력 순서 및 확정 스펙 (playwright_gaisan_jungsan.py)**:
    - 에듀파인 개산금정산등록 확정 메뉴 ID: A00FAA0104001004 (프로그램 ID: A00FAD0050002001).
    - 콤보박스 시스템 전환: TopFrame.form.cboJobList에서 인덱스 2번(A00FA, 학교회계) 선택 후 cboJobList_onitemchanged 이벤트 발행.
    - 시작일자: divWork.form.divSearch.form.calRecptDteFrom.set_value('YYYYMMDD') 후 tnAuthS01.click()으로 조회.
    - 하단 정산내역 그리드(grdDetail) 데이터셋: dsDetail.
    - 하단 행추가: divWork.form.divAuth3.form.btnAddRow.click().
    - 컬럼 구조:
      - pymntDte: 사용일자 (YYYYMMDD)
      - usePlaceNm: 사용업체명
      - pymntAmt: 사용금액 (정수)
      - prufSeCd: 증빙구분코드 ('3': 전산자료/신용카드, '4': 현금영수증, '1': 세금계산서)
      - useCn: 사용내역
    - [저장]: divWork.form.divAuth.form.btnAuthR01.click().
    - [정산서제출]: divWork.form.divAuth2.form.btnPrsnt.click().
    - 브라우저 메인 프로세스 락을 우회하기 위해 WebSocket CDP JSON-RPC 직접 통신 표준 적용.

13. **OZ Report ExeViewer 무인 자동 PDF 일괄 저장 (`start_OZUtil.createViewer` 후킹)**:
    - K-에듀파인 지출결의서/품의서 출력 시 OZ 뷰어는 로컬 C++ 에이전트(`start_OZUtil` / `ozexeviewer`)를 호출하여 인쇄/저장을 수행함.
    - 기본 상태에서는 Windows 파일 저장 대화상자(Save As dialog)가 매번 팝업되어 사용자가 경로와 파일명을 일일이 지정해야 하는 치명적 병목 발생.
    - 해결책: `common::commonReport.xfdl`을 `popuptype: 'modal'`로 띄우고 `iframe[src*="ozhviewer.jsp"]` 내의 `win.start_OZUtil.createViewer`를 후킹하여 `export.confirmsave = "false"`, `export.mode = "silent"`, `export.path`, `export.filename`을 주입한 뒤 `_callSavePdf()`를 호출하면 화면 팝업 없이 백그라운드에서 완전 무인 PDF 저장이 완결됨.
    - 렌더링 완료는 `win.OZViewer.GetInformation("TOTAL_PAGE") > 0` 폴링으로 판정.
    - 품의목록(`FADMANGECLI001M01`)의 상태 열 돋보기 클릭 시 호출되는 `FADMANGECLI003P01`(지출진행상태)에서 `dsDecis`(지출결의)와 `dsDetl`(세부 품목 내역)을 읽어와 품목별 산출내역 CSV와 총괄 대조표 CSV를 동시 자동 생성.

14. **1품의 N결의(다중 분할 지출결의) 전수 순회 및 리포트 모달 수명주기 관리**:
    - 대규모 예산(자투리공간 2,000만 원, 수영 654만 원, 운동회 459만 원 등)은 단일 품의에 대해 조달청(G2B), 학교장터(S2B), 온라인 쇼핑몰, 일반업체 등으로 계약이 쪼개져 **다수의 원인행위 및 지출결의(`dsDecis`)**가 발생함.
    - `dsDecis`의 `row 0`만 단일 인덱스로 참조하면 첫 번째 결의(예: 선반 222만원)만 다운로드되고, 축구골대(495만원), 이동식 농구대(492.6만원) 등 대형 핵심 결의가 누락되는 치명적 왜곡 발생.
    - **해결 패턴**: `FADMANGECLI003P01` 팝업 내부의 `dsDecis.rowcount`를 전수 순회(`for nRow in range(...)`)하여 각 결의마다 `reportPopupModal`을 modal로 띄워 PDF 저장 후, 반드시 `reportPopupModal.form.close()`로 모달을 닫고 다음 행으로 넘어가야 넥사크로 UI 락 및 웹소켓 타임아웃 없이 전건 무인 저장 완결됨.
    - **PDF 2페이지 「물품명세서」 PyMuPDF 파싱**: 결의서 PDF 2페이지의 블록/라인 텍스트를 파싱하여 개별 물품명, 규격, 수량, 단위, 단가, 결의금액을 품의 데이터와 1:1 결합한 `2026학년도_품목별_실제지출결의_정밀대조표.csv`를 산출.


---

## 📅 일자별 개발 실패 극복 및 트러블슈팅 일지

---


### 2026-11-11: [트랙 8] 품의 문서 지출결의서 PDF 일괄 무인 다운로드 및 세부 품목 대조 봇

#### 1. 업무 현황 및 요구사항
- 교사가 품의한 에듀파인 문서에서 실제 지급된 **지출결의서 PDF를 일괄 다운로드**하고, 품의 금액과 실제 지출결의 금액의 차이를 검증하고자 함.
- 여러 물품을 묶어서 품의한 경우 개별 물품별 실제 구입 금액(단가, 수량, 품목별 차액)을 지출결의서 및 세부 내역으로 대조해야 함.

#### 2. 기술적 난제 및 해결책
1. **품의 vs 지출결의 분기 파악**:
   - 품의목록(`FADMANGECLI001M01`)의 `상태` 열(8번 셀) 돋보기를 누르면 `FADMANGECLI003P01`(지출진행상태) 팝업이 호출됨.
   - 실제 돈이 지급되지 않은 미결재/진행 중 품의는 결의(`dsDecis`) 데이터가 0행이므로 결의출력 불가.
   - 원인행위 및 지출결의가 완료된 건만 `dsDecis`가 존재하며 `btnDecisOutpt` 및 `fnPrintExres("N")`로 결의출력 가능.
2. **OZ ExeViewer Windows 파일 저장 팝업 완전 우회**:
   - 에듀파인 OZ 뷰어는 로컬 C++ 프로그램(`ozexeviewer`)을 호출하면서 `export.confirmsave = true` 상태이므로 Windows '다른 이름으로 저장' 대화상자가 매번 화면에 뜸.
   - `commonReport.xfdl` 팝업을 modal로 열고, `iframe[src*="ozhviewer.jsp"]`의 `win.start_OZUtil.createViewer` 메서드를 런타임 후킹하여 `export.confirmsave = "false"`, `export.mode = "silent"`, `export.path`, `export.filename`을 주입.
   - `win._callSavePdf()` 호출 시 아무런 팝업 창 없이 지정 경로에 PDF가 100% 무인 저장됨.
3. **1품의 N결의(다중 분할결의) 누락 버그 해결 (핵심 돌파구)**:
   - **문제**: 자투리공간 2,000만 원 예산 품의(`00582`)에서 선반 222만 원 1건만 다운로드되고, 축구골대(495만 원), 이동식 농구대(492.6만 원) 등 1,600만 원 상당의 대형 결의서 4건이 누락됨.
   - **원인**: 단일 품의당 1건의 결의만 존재할 것이라 가정하고 `dsDecis.getColumn(0, ...)`으로 고정 접근함.
   - **해결**: `dsDecis.rowcount`를 전수 순회하도록 스크립트를 재설계하고, 동일 `FADMANGECLI003P01` 팝업 안에서 각 행별로 `reportPopupModal`을 열고 닫는 수명주기 분리.
   - **결과**: 자투리공간 5건(총 1,848만 4,560원) 전건 및 수영(3건), 육상(3건), 어울림한마당(각 2건) 등 2026학년도 전체 30건의 지출결의서 PDF를 100% 누락 없이 다운로드 완결.
4. **PDF 2페이지 「물품명세서」 PyMuPDF 파싱을 통한 개별 품목 단가/차액 정밀 대조**:
   - 단순 품의 총액 대조에서 한 걸음 더 나아가, 각 지출결의서 PDF 2페이지의 `물 품 명 세 서` 테이블에서 `품명, 규격, 수량, 단위, 단가, 결의금액`을 PyMuPDF로 자동 파싱.
   - 축구골대, 농구골대, 네트, 지주, 공 등 총 74개 세부 품목별 실제 결의단가와 품목별 차액, 실거래처가 매칭된 `2026학년도_품목별_실제지출결의_정밀대조표.csv` 자동 생성 성공.
5. **결과 산출물**:
   - 다운로드 완료 지출결의서 원본 PDF: **30건** (`C:\Users\user\Downloads\지출결의\`)
   - 지출결의 총괄 대조표 CSV: `2026학년도_지출결의_총괄대조표.csv` (총 30건)
   - 품목별 실제 지출결의 정밀 대조표 CSV: `2026학년도_품목별_실제지출결의_정밀대조표.csv` (총 74개 품목)

---


### 2026-11-10: [트랙 7] 학급 자율 운영비 개산금정산 자동화 구현 🏆

#### 1. 업무 현황 및 요구사항
- **근거 문서**: 경상북도 공립학교회계 규칙 제39조(개산급), 화천초 2026학년도 학급운영비 집행 안내
- **업무 흐름**:
  1. 행정실이 담임교사 계좌로 개산급(학생 1인당 20,000원) 지급
  2. 담임교사가 개인 신용카드로 집행 (생일잔치, 상담 다과, 사제동행 등)
  3. 집행 완료 후 5일 이내 에듀파인 `개산금정산등록`에 영수증별 행추가 입력 → 저장 → 정산서 제출
  4. 출력한 정산서에 서명날인 후 증빙서와 함께 출납원(행정실장)에게 제출
- **자동화 대상**: 3번 단계 — 에듀파인 화면 진입~행추가~입력~저장까지

#### 2. 구현 내역

| 파일 | 역할 |
|---|---|
| `playwright_gaisan_jungsan.py` | 개산금정산 RPA 메인 모듈 |
| `app.py` → `/api/gaisan-jungsan` | Flask API 엔드포인트 추가 |
| `templates/index.html` | 대시보드 `💰 [트랙 7] 개산금정산` 탭 추가 |
| `SKILL.md` | [트랙 7] 항목 및 집행 규정표 추가 |

#### 3. 기술적 설계 포인트

1. **메뉴 ID 추정 (`A00FAA0104001004`)**:
   - `A00FAA0104001001` = 품의등록, `001002` = 정산 등록 등의 패턴에서 `001003`을 개산금정산등록으로 추정.
   - gfnOpenMenu 직결 실패 시 텍스트 클릭 fallback 2단계 적용.

2. **그리드 셀 입력 순서**: 사용일자 → 사용업체명 → 사용금액 → 증빙구분(콤보) → 사용내역
   - 넥사크로 그리드는 셀 `Enter` → 타이핑 → `Enter`로 편집 완료 후 `Tab`으로 다음 셀 이동.
   - 증빙구분 콤보박스는 `Enter`로 드롭다운 열기 → 텍스트 클릭 fallback.

3. **행추가 Y좌표 필터**: 기존 품의등록 봇의 `y > 300` 로직 그대로 적용. 상단 개산급 목록 그리드와 하단 정산내역 그리드가 분리되어 있어 하단 행추가만 타격.

4. **auto_submit 옵션**: `False`(기본) = 저장까지만 → 사람이 화면 확인 후 제출. `True` = 저장 + 정산서 제출 자동 클릭. SKILL.md 보안 정책 2번(최종 상신 사람이 직접)과 동일 원칙.

5. **UI 대시보드 통합**:
   - `switchTab('gaisan')` 탭 전환 함수 확장.
   - 행 단위 동적 입력 테이블 (날짜/업체명/금액/증빙구분/내역).
   - 합계 실시간 계산 표시.
   - `startLogStream()` 호출로 기존 SSE 로그 패널 재활용.

#### 4. 실전 주의사항 (추후 작업자에게)
- **개산급 지급 전 집행은 정산 불가**: 조회 결과 없음이 나오면 행정실 확인 필요.
- **메뉴 ID `A00FAA0104001004` 미확인**: 실제 에듀파인 접속 후 gfnOpenMenu 반환값으로 검증 필요. 실패 시 텍스트 fallback이 작동하므로 현장 테스트 후 ing.md에 확정 ID 업데이트 요망.
- **증빙구분 콤보 선택**: 넥사크로 콤보는 Enter 후 드롭다운 아이템 텍스트 클릭. 아이템 텍스트가 다르면 `JEUNGBIG_MAP` 딕셔너리 조정 필요.
- **포인트 적립 금지**: 개인 카드와 학급비 항목을 같이 결제하지 말 것(봇 외 주의사항).

---

### 2026-11-10: 결재대기 공문 3건 전교사 공람 일괄 지정 및 본문 ODT 직결 추출/PDF 변환 다운로드 완결 🏆

#### 1. 업무 현황 및 요구사항
- 결재대기 중인 수신 공문 3건 확인:
  1. `화천초등학교-11905`: `[안내, 참가] 2026 경북 학교 체육 한마당(도전! 체력 인증왕 선발 대회) 참가 안내`
  2. `화천초등학교-11907`: `[안내] 제5회 경주 초등학생 축구페스티벌 개최 안내 및 참가 신청`
  3. `화천초등학교-11915`: `[추천] 2026학년도 학교체육활성화 유공 표창 계획 안내`
- 요구사항:
  - 3건 모두 화천초 전교사 대상 공람 지정
  - 각 공문의 본문 문서를 PDF로 변환하여 다운로드 폴더 내 `공문` 폴더(`C:\Users\user\Downloads\공문\`)에 보관

#### 2. 기술적 난제 및 트러블슈팅

1. **결재대기 문서의 본문 PDF 다운로드 엔드포인트 규명**:
   - `retrieveViwAtchmnflDirect.do`는 `APPLID === '8010'`(문서등록대장/열람함) 환경에서만 뷰어 저장을 지원하며, 결재대기(`APPLID === '2010'`)에서는 HTML 파일저장 팝업이 반환되어 직접 다운로드 불가.
   - `retrieveAtchmnfl.do` 화면의 `goSubmit()` 소스 분석 결과:
     일반 첨부 및 본문 파일은 `/bms/cz/cb/viw/retrieveViwAtchmnfl.do`에 `POST`로 `FTYPE='01'`, `OBJID = aid[:-3] + '001'`, `FILENAME = '결재문서본문.odt'`를 요청하면 원본 ODT 바이너리가 그대로 반환됨을 확인.
2. **ODT 원본의 무손실 PDF 변환 구현**:
   - 에듀파인은 ODT(OpenDocument Text) 표준을 사용하므로 폰트/표 깨짐 없이 PDF로 변환하기 위해 Windows 로컬에 설치된 `Word.Application` COM 인스턴스(`ExportAsFixedFormat`) 및 `HWPFrame.HwpObject`를 연동하여 고품질 PDF를 생성하는 파이프라인(`odt_to_pdf.py`) 구축.
3. **다중 문서 공람 팝업 루프 시 `NoSuchWindowException` 극복**:
   - 첫 번째 공람 팝업 탭을 처리하고 `driver.close()`를 수행한 뒤, 활성 핸들이 메인 윈도우로 복원되지 않은 상태에서 `driver.switch_to.new_window('tab')`을 호출하면 브라우저 컨텍스트 유실로 에러 발생.
   - 루프 시작 전 `main_handle`을 기록해두고 팝업 닫기 직후 반드시 `driver.switch_to.window(main_handle)`를 명시적으로 실행하여 3건 모두 연속 공람 지정 완결.

#### 3. 최종 결과
- **공람 지정**: 11905, 11907, 11915 공문 3건 모두 화천초 교직원 43명 전원에 대해 공람 등록 완료.
- **파일 저장**: `C:\Users\user\Downloads\공문\` 폴더에 각 공문의 본문 ODT, 고품질 변환 PDF, 붙임 파일(xlsx, hwp, hwpx, 포스터 pdf 등 총 12개 파일) 일괄 보관 완료.

---

### 2026-10-28: 결재대기 조회 — Playwright CDP 행과 위젯/본화면 불일치 극복

#### 1. 문제 상황
- `python edufine_auto_approve.py`가 Chrome 9222 `connect_over_cdp`에서 출력 없이 무한 대기.
- 업무포털 `kedufine` iframe은 교차출처라 포털 페이지 JS에서 DOM을 읽지 못함.
- 결재대기 iframe `src`를 `.../wrt/retrieveSanctnWaitDocList.do`로 바꾸면 오류 페이지. 공람대기 화면이 덮어씌워짐.

#### 2. 원인 및 해결
1. 탭 전용 `webSocketDebuggerUrl` + `Runtime.evaluate`로 수집.
2. `/json`의 `type=iframe` 타겟 `retrieveSanctnWaitDocListNice.do`에 직접 접속해 위젯 목록 수집.
3. 결재대기 본화면은 `viw/retrieveSanctnWaitDocList.do?leftMenu=1`에서 `fncSearch()` 후 건수 확인.
4. 작업 후 공람대기 iframe `src`를 원래 `retrieveCnrsWaitDocList.do`로 복구.

#### 3. 조회 결과 (2026-10-28 12:13)
- 에듀파인 결재대기 본화면: **0건**.
- 포털 위젯: `[안내] 제26회 경상북도교육감기 초등학교 수영대회 개최 참가요강 알림` (박은정, 2026-10-27) 1건 — 본화면과 불일치, 위젯 미갱신 가능.
- 어제 결재대기였던 스포츠인성교육 자율연수 안내는 결재대기에서 사라짐.
- 공람대기: 23건 (오늘 도착 포함).

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
