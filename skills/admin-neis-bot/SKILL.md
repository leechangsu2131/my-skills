---
name: admin-neis-bot
description: 나이스(NEIS) 교외체험학습 신청서/보고서 및 결석신고서 일괄 접수/결재선 상신 자동화. Chrome 원격 디버깅(9222)으로 나이스에 로그인한 브라우저에 연결하여 eXBuilder6 CPR API 및 DOM 이벤트를 제어하여 자동 처리.
---

# admin-neis-bot

## 개요

학급 담임 교사의 나이스(NEIS) 행정 업무를 자동화하는 스킬입니다. 
학부모가 제출한 **교외체험학습신청서**, **교외체험학습보고서**, **결석신고서**를 일괄 조회하여 접수 처리하고, 각 항목의 결재 요건에 맞게 결재선을 자동 지정하여 기안 및 최종 상신을 완료합니다.

---

## 📂 종합 프로젝트 파일 맵 및 관계 문서 구조

이 스킬을 구성하고 있는 주요 소스코드, 데이터 초안 및 트러블슈팅 문서의 전체적인 맵입니다. 향후 유지보수 시 이 맵을 기준으로 탐색하십시오.

### 1. 트러블슈팅 및 작업 추적 문서 (필독 📝)
- **[ing.md](file:///C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/admin-neis-bot/ing.md)**: **[문제 저장 및 장애 대응 로그]** 크롬 디버깅 포트 충돌, 세션 격리(Session 0 to Session 1), 보안 프로그램 프로필(User Data) 락 및 EVPN 단절 등의 원인 분석과 우회 성공 프로세스를 기술한 상세 디버깅 기록지. 자율활동·스포츠클럽 등 후속 작업의 이슈 & 해결도 이 파일에 추가 기록됨.
- **[task-jayul.md](file:///C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/admin-neis-bot/task-jayul.md)**: **[자율활동 누가기록 작업 체크리스트]** 데이터셋 구조, 컨트롤 ID, 전입생 정보, 작업 순서, 발견된 문제 & 해결 현황을 기록한 작업 추적 문서. 세션이 중단되어도 이 파일을 보고 이어 작업할 수 있음.
- **[walkthrough.md](file:///C:/Users/lee21/.gemini/antigravity/brain/b857c57b-5e64-4b7d-bb6c-7a63cf5605b2/walkthrough.md)**: **[최종 수행 결과 리포트]** 18명 전원의 맞춤형 누가기록과 동아리활동 특기사항의 실전 서버 저장 완료 내역 및 검증 캡처 증명서.

### 2. 데이터 초안 (Data Source)
- **[독서동아리_누가기록_초안 (1).md](file:///C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/admin-neis-bot/data/%EB%8F%85%EC%84%9C%EB%8F%99%EC%95%84%EB%A6%AC_%EB%88%84%EA%B0%80%EA%B8%B0%EB%A1%9D_%EC%B4%88%EC%95%88%20%281%29.md)**: 3학년 2반 독서동아리 18명 학생의 4개 회차별 누가기록 맞춤 내용 및 학생부용 종합 특기사항 한 문장 초안 텍스트.

### 3. 나이스 연동 자동화 스크립트 맵 (Scripts)
- **[neis_club_individual_playwright.py](file:///C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/admin-neis-bot/neis_club_individual_playwright.py)**: Playwright를 통해 9222 포트 크롬에 원격 연결한 후 3개 일자별(7/9, 7/16, 7/24) 18명 맞춤형 누가기록을 순차 주입하고 저장을 수행하는 메인 스크립트.
- **[neis_club_opinion_writer.py](file:///C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/admin-neis-bot/neis_club_opinion_writer.py)**: `학생부자료기록` 탭의 `dsScrgRec` 데이터셋을 타겟으로 하여, 초안 (1).md에 적힌 18명 학생별 종합 특기사항을 대입하고 confirm/alert 모달을 자동 닫으며 서버 저장을 완결하는 스크립트.
- **[neis_diagnose_club_detail.py](file:///C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/admin-neis-bot/neis_diagnose_club_detail.py)**: 현재 활성화된 나이스 화면 상의 모든 eXBuilder6 인스턴스, 데이터셋 컬럼 및 샘플 값을 백그라운드에서 덤프하여 컴포넌트 구조를 규명해주는 진단 도구.
- **[neis_test_entry.py](file:///C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/admin-neis-bot/neis_test_entry.py)**: 실물 조종성 검증을 위해 7/9 일자 조회 화면 상에서 2명(강시우, 김가을)에 대해서만 텍스트를 임시 주입하고 verification 스크린샷을 찍는 테스트 전용 드라이런 스크립트.
- **[neis_sports_club_writer.py](file:///C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/admin-neis-bot/neis_sports_club_writer.py)**: 학교스포츠클럽 누가기록(줄넘기 3-2) 18세션 일괄 등록 자동화. 결석/지각 학생 필터링, 활동내용 순환 입력, 얼럿 모달 핸들링 포함.
- **[neis_jayul_record_writer.py](file:///C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/admin-neis-bot/neis_jayul_record_writer.py)**: 자율활동 누가기록 39건(직접입력 6건 제외) 일괄 등록 완료. 주간학습 가져오기 → 학생 전체 체크 → 전입생 조건부 해제 → 내용 적용 → 저장 및 연쇄 모달 자동 해제.

---

## 제공 기능 및 실행 방법


1. **교외체험학습신청서 자동화** (`neis_experiential_learning.py`)
   - **결재라인**: 교무(강동휘) -> 교감(김경영)
   - **실행**:
     ```bash
     python skills/admin-neis-bot/neis_experiential_learning.py --apply --confirm APPLY_NEIS
     ```

2. **교외체험학습보고서 자동화** (`neis_experiential_report.py`)
   - **결재라인**: 교무(강동휘) 단독 상신 (교감 제외)
   - **실행**:
     ```bash
     python skills/admin-neis-bot/neis_experiential_report.py --apply --confirm APPLY_NEIS
     ```

3. **결석신고서 자동화** (`neis_absence_report.py`)
   - **결재라인**: 교무(강동휘) -> 교감(김경영)
   - **특이사항**: 조회 기간을 1~2개월 이전 범위로 강제 확장하고, 상세 팝업에서 결석구분("질병결석") 및 접수상태("접수")를 선행 설정한 뒤 저장 및 승인요청을 수행합니다.
   - **실행**:
     ```bash
     python skills/admin-neis-bot/neis_absence_report.py --apply --confirm APPLY_NEIS
     ```

4. **동아리활동 누가기록 복구 및 관리**
   - **주요 스크립트**:
     - `neis_club_delete_dups.py`: 특정 일자의 중복 등록 행을 `stuInvlNo` 기준으로 탐색하여 삭제 및 저장하는 스크립트.
     - `neis_club_volunteer_redo.py`: 나이스 시스템 고유의 체크박스 클릭 핸들러를 트리거하여 장소명(`(학교)화천초등학교`)과 최대이수시간을 자동으로 정합성 있게 입력하는 일괄 등록 스크립트.
     - `neis_club_verify_final.py`: 각 일자별 데이터셋 행 개수와 봉사활동 여부를 재조회하여 검증하는 모니터링 스크립트.

5. **학교스포츠클럽 누가기록 일괄 등록** (`neis_sports_club_writer.py`)
   - 줄넘기(3-2) 18세션(수요일 아침/점심 20분씩 → 9시간 분량)을 7/24 역산 기준으로 일괄 등록.
   - 결석/지각 학생 자동 필터링, `스포츠클럽활동내용.txt` 내용 순환 입력.
   - **실행**:
     ```bash
     python skills/admin-neis-bot/neis_sports_club_writer.py --apply
     ```

6. **자율활동 누가기록 기존 데이터 삭제 및 개별 맞춤 기입** (`neis_jayul_delete_all.py`, `neis_jayul_individual_writer.py`) _(완료 🏆)_
   - **대상 화면**: 창의적체험활동 > 자율·자치활동(자율활동)관리 > 누가기록 탭 (앱 ID: `edu/sw/els/sdl/ce/els_sdlce00_m01`)
   - **원칙**: 기존 반별 일괄 등록(주간학습 가져오기)된 데이터를 **완전히 삭제한 뒤(Phase 1)**, 비동기 충돌이 없도록 개별 학생에게만 **맞춤형 문장을 기입(Phase 2)**하는 순서의 원칙 준수.
   - **Phase 1: 일괄 삭제**
     - 각 날짜(39개 일자)에 대해 모든 학생 행 체크 (`grdMain.checkAllRow(true)`) ➡️ 공식 삭제 버튼 (`btnDelete.click()`) ➡️ 저장 (`btnSave.click()`) 및 모달 닫기 순으로 완전히 빈 칸으로 복구.
     - **실행**:
       ```bash
       python skills/admin-neis-bot/neis_jayul_delete_all.py --apply
       ```
   - **Phase 2: 개별 맞춤 기입**
     - 삭제 로직이 배제된 순수 개별 기입 (`JS_APPLY_INDIVIDUAL_WRITE_ONLY`) 적용.
     - 15개 날짜 그룹을 순회하며 초안에 지정된 오지윤, 이서우, 최윤채 등 18인 맞춤 자율활동 문장을 각 날짜에 대입하고 즉시 저장 (`btnSave.click()`).
     - **실행**:
       ```bash
       python skills/admin-neis-bot/neis_jayul_individual_writer.py --apply
       ```
   - **검증**: `verify_individual.py`를 실행하여 특정 일자(예: 3.17, 5.15)의 화면을 캡처하고 지정 학생 외 다른 학생들은 깨끗이 공란으로 유지된 채 저장 완료되었음을 최종 확인.

7. **방학 중 41조 연수 자동 상신 (Playwright CDP 모듈)**

- **EVPN 접속 방식 및 가이드**:
  1. 경북교육청 EVPN 올바른 주소: **`https://evpn.gbe.kr`** (go.kr 아님!)
  2. 크롬 디버거 론처: `launch_playwright_browser.py` 구동 (`no_viewport=True`, `--start-maximized` 옵션 적용으로 사용자 화면 전체에 100% 꽉 차도록 구동).
  3. 전용 프로필 `--user-data-dir="%TEMP%\neis_chrome_profile_9222"` 사용으로 기존 Chrome 백그라운드 프로세스와 충돌 없이 9222 포트 100% 바인딩 보장.
  - 목적지 작성 원칙: `경주 화천` (지명 중심 표기)
  - 일반복 (일 반복): **오후만 반일 복무인 경우에만 `ddRpatYn = "Y"` 대입**, **종일 복무인 경우 `ddRpatYn = "N"` 대입**.
  - 비상연락처: `ipbEmgCnctTelno.value = "01042330844"` 및 `dsMain[0].emgCnctTelno = "01042330844"` 100% 자동 채움 필수.
  - 기안 결재선 팝업 앱 ID: `edu/cm/wam/woapm07_p00` (기안 제목: `근무상황신청 [교육공무원법제41조연수]`, `btnSelectSancr.enabled === true` 될 때까지 최대 12초 폴링 대기 후 클릭)
  - 결재선 선택 팝업 앱 ID: `edu/cm/wam/woa/pm/wam_woapm07_p04` (버튼 클릭 후 3초 + 10초 폴링 대기 보장)
  - 결재선 구성원 (실제 학교 DB 확인): 교무(`강동휘`) -> 교감(`김경영`) -> 교장(`박순현`) (3-level approval)
  - **상신 후 [확인] 클릭 철저 보장**: 상신 클릭 후 화면에 뜨는 `app/cmn/alert`, `app/cmn/confirm` 완료 팝업의 [확인] 버튼(`btnOk`, `btnConfirm`, `val="확인"`)을 루프 탐색으로 100% 닫기까지 완수.
  - **상신 이력**:
    - **1차 (7.28~7.31 오후)**: 2026-07-21 상신 완료 ⭕ (목적지: 경주 화천)
    - **2차 (8.3~8.7 오후)**: 2026-07-21 상신 완료 ⭕ (목적지: 경주 화천)
    - **3차 (8.10~8.14 종일)**: 2026-07-21 상신 완료 ⭕ (목적지: 경주 화천)
- **단일 단계 수행 및 검증 수칙**:
  - 일괄 처리 금지. 반드시 1건(또는 1단계)씩 실행 -> 결과 스캔/리뷰 -> md 기록 프로세스 준수.
  - eXBuilder6 인풋 필드 값 설정 시 `cpr.events.CValueChangeEvent` 및 DOM level native event(`input`, `change`, `blur`) 동시 발화 필수.
   - **사유**: 교육연극을 활용한 국어수업 연구
   - **목적지**: 화천 자택 (기본값, `--destination` 으로 변경 가능)
   - **특이사항**: Playwright CDP 연결 방식 사용 (EVPN 환경 대응)
   - **실행**:
     ```bash
     # 진단 (화면 구조 파악)
     python skills/admin-neis-bot/neis_article41_leave.py --diagnose --navigate
     # 실반영
     python skills/admin-neis-bot/neis_article41_leave.py --apply --confirm APPLY_NEIS --navigate
     ```


---

> [!NOTE]
> 개발 과정에서 `scratch` 디렉토리 하위에 생성된 모든 임시/테스트용 파이썬 스크립트 및 JSON 데이터 파일은 현재 이 폴더(`skills/admin-neis-bot/`) 내에 전부 병합 이전되어 영구 자산화되었습니다.


## 사전 요건 및 웹 자동화 접속 철칙 (필독 ⚠️)

### 1. Chrome 원격 디버깅 실행 (실제 사용자 프로필 필수)
에듀파인/나이스 등 보안 프로그램 및 공동인증서가 탑재되는 국가 교육망 자동화는 임시 프로필을 사용하면 **보안 설치 루프**에 빠지게 됩니다. 반드시 **실제 사용자 기본 프로필**을 사용하여 실행해야 합니다.
또한 기존 실행된 크롬 인스턴스 점유 및 Singleton 락으로 인해 디버깅 포트 활성화가 차단되는 것을 막기 위해, 다음 **파워쉘 전처리 명령어**를 실행한 뒤 크롬을 띄워야 합니다.

**[권장] 마스터 크롬 런처 실행 스크립트 (바탕화면 배포용)**:
```bat
@echo off
chcp 65001 > nul

echo 기존 크롬 프로세스 및 싱글톤 락을 제거합니다...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'name = ''chrome.exe''' | Where-Object { $_.CommandLine -like '*User Data*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
powershell -NoProfile -Command "Remove-Item -Path '$env:LOCALAPPDATA\Google\Chrome\User Data\SingletonLock' -Force -ErrorAction SilentlyContinue"

echo 크롬 원격 디버깅(9222 포트) 모드를 실제 프로필로 실행합니다...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data" --new-window "https://evpn.gbe.kr"
```

### 2. EVPN 인터넷 차단망 내 접속 설계 (Playwright + no_proxy)
- 가상사설망(EVPN) 연결 상태에서는 외부 통신망이 제한되므로 Selenium의 드라이버 업데이트 아웃바운드 핀이 락에 걸립니다.
- 따라서 원격 연결 시 **Playwright**의 다이렉트 소켓 접속(`connect_over_cdp`)을 기본으로 채택합니다.
- 에이전트 터미널(`Session 0`)과 사용자 화면 크롬(`Session 1`) 간의 세션 격리 오류(`ECONNREFUSED`) 및 IPv6 루프백 해석 오류(`::1`)를 피하기 위해, 코드 최상단에 **no_proxy 지정** 및 **IPv4 명시 고정**을 구현해야 합니다.

**[표준 파이썬 연결 스니펫]**:
```python
import os
# 가상 어댑터 필터 우회를 위한 로컬 루프백 프록시 강제 예외 처리
os.environ["no_proxy"] = "localhost,127.0.0.1"

# IPv6 ::1 주소 매핑 꼬임을 차단하기 위해 http://127.0.0.1:9222 로 직접 CDP 연결
browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
```

### 3. Python 의존성 설치
```bash
pip install playwright
playwright install chromium
```


---

## eXBuilder6 플랫폼 자동화 노하우 (중요)

나이스 시스템은 eXBuilder6 플랫폼 기반이므로 표준 Selenium 제어와 다릅니다. 다음 가이드를 준수해야 에러 없이 자동화가 완료됩니다:

### 1. 그리드 체크박스 제어
- 단순히 데이터셋의 `chk` 값을 `"1"` 로 변경하는 것만으로는 결재 버퍼에 등록되지 않습니다.
- **해결**: 그리드 DOM 요소 ID(`uuid-` 접두사 + `grid.uuid`)를 구하고, 각 행의 체크박스 요소를 직접 찾아 `.click()`을 전송해야 합니다:
  ```javascript
  var gridEl = document.getElementById("uuid-" + grid.uuid);
  var chkBox = gridEl.querySelector('[data-rowindex="' + r + '"] .cl-grid-checkbox');
  if (chkBox) chkBox.click();
  ```
- 메인 화면 그리드(`grdMain`) 등에서는 특정 행의 체크 상태를 개별 제어하기 위해 **`grdMain.setCheckRowIndex(rowIndex, true/false)`** API를 사용하여 체크 처리를 수행할 수 있습니다.

### 2. 그리드 간 데이터 추가 (결재선 지정 등)
- 행을 선택하고 [추가] 버튼을 누르는 API는 작동 딜레이 등으로 씹힐 수 있습니다.
- **해결**: 그리드 행 내부에서 이름 텍스트(예: "강동휘")가 들어간 `span` 요소를 직접 찾아 **`dblclick` (더블클릭) 마우스 이벤트**를 시뮬레이션 전송하면 결재선 목록으로 정확히 추가됩니다:
  ```javascript
  var dblEvent = new MouseEvent('dblclick', { bubbles: true, cancelable: true, view: window });
  targetSpan.dispatchEvent(dblEvent);
  ```

### 3. 결석신고서 접수상태 및 구분 변경
- 결석계는 접수대기 상태 그대로 저장을 누르면 경고창과 함께 실패합니다.
- **해결**: 저장 버튼을 누르기 전, 결석구분 콤보박스(`cmbAbeDclrScCd`)와 처리상태코드 콤보박스(`cmbEduActPrcsStsCd`)의 값을 자바스크립트로 세팅하고 `.redraw()` 해야 저장이 성공합니다:
  ```javascript
  cmbAbeDclrScCd.value = "01"; // 질병결석
  cmbEduActPrcsStsCd.value = "02"; // 접수
  ```

### 4. 컨펌/알림 모달 닫기
- 컨펌창 닫기 중 `ai.app` 객체가 `null` 인 경우가 있으므로 널가드(null guard) 처리를 해야 자바스크립트 토큰 오류를 예방할 수 있습니다:
  ```javascript
  var appId = (target.app && target.app.id) ? target.app.id : "unknown";
  ```
- **해결 (성공 기법)**: 일반 DOM 클릭이 작동하지 않을 경우, eXbuilder6 플랫폼 API를 통해 모달 내의 버튼 컨트롤에 직접 접근하여 `.click()` 메서드를 호출합니다.
  ```javascript
  var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
  apps.forEach(function(ai) {
      if (ai && ai.app && (ai.app.id.indexOf("confirm") !== -1 || ai.app.id.indexOf("alert") !== -1 || ai.app.id.indexOf("cmn") !== -1)) {
          var container = ai.getContainer ? ai.getContainer() : null;
          if (container && container.getAllRecursiveChildren) {
              container.getAllRecursiveChildren().forEach(function(c) {
                  if (c && c.type === "button" && (c.value === "예" || c.value === "확인")) {
                      c.click(); // 컴포넌트 API click 호출
                  }
              });
          }
      }
  });
  ```

### 5. 봉사활동 실적 자동 연동 트리거
- 봉사활동 입력 여부(`cbxServActYn`) 및 주관기관명(`ipbPlaceMngtInstNm`)을 자바스크립트 변수로 직접 때려 박아 저장하면 나이스 고유 코드 연동이 생략되어 데이터 정합성 에러가 발생할 수 있습니다.
- **해결**: 봉사활동실적입력 체크박스의 HTML DOM 요소를 구한 뒤 브라우저 고유의 `.click()` 이벤트를 쏘아줍니다. 이렇게 하면 나이스 내부 이벤트 핸들러가 돌아가면서 장소(예: `(학교)화천초등학교`) 및 시간(`1시간`) 정보가 내부 규칙에 따라 자동으로 정확히 채워집니다.
  ```javascript
  var dom = cbxServActYn.getHtmlElement ? cbxServActYn.getHtmlElement() : null;
  if (dom) {
      dom.click();
  }
  ```

