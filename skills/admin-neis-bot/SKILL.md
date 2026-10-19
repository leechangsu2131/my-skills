---
name: admin-neis-bot
description: 나이스(NEIS) 교외체험학습 신청서/보고서 및 결석신고서 일괄 접수/결재선 상신 자동화, 자율/동아리/스포츠클럽 누가기록 관리, 41조 연수 상신, 교원연수 이수등록, 학급시간표 시수 최적화(편차 0) 자동화. Chrome 원격 디버깅(9222)으로 나이스에 로그인한 브라우저에 연결하여 eXBuilder6 CPR API 및 DOM 이벤트를 제어하여 자동 처리.
---

# admin-neis-bot

## 개요

학급 담임 교사의 나이스(NEIS) 행정 업무를 자동화하는 스킬입니다. 
학부모가 제출한 **교외체험학습신청서**, **교외체험학습보고서**, **결석신고서**를 일괄 조회하여 접수 처리하고, 각 항목의 결재 요건에 맞게 결재선을 자동 지정하여 기안 및 최종 상신을 완료합니다. 
또한 **자율·동아리·스포츠클럽 누가기록**, **41조 연수 상신**, **연수 이수실적 등록**, **학급시간표 시수 최적화(편차 0 달성 및 DB 저장)** 등 반복 행정 업무를 완벽하게 자동화합니다.

---

## 📂 종합 프로젝트 파일 맵 및 관계 문서 구조

이 스킬을 구성하고 있는 주요 소스코드, 데이터 초안 및 트러블슈팅 문서의 전체적인 맵입니다. 향후 유지보수 시 이 맵을 기준으로 탐색하십시오.

### 1. 트러블슈팅 및 작업 추적 문서 (필독 📝)
- **[ing.md](file:///C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/admin-neis-bot/ing.md)**: **[문제 저장 및 장애 대응 로그]** 크롬 디버깅 포트 충돌, 세션 격리(Session 0 to Session 1), 보안 프로그램 프로필(User Data) 락 및 EVPN 단절 등의 원인 분석과 우회 성공 프로세스를 기술한 상세 디버깅 기록지. 자율활동·스포츠클럽·학급시간표 편차 0 최적화 등 후속 작업의 이슈 & 해결도 이 파일에 추가 기록됨.
- **[task-jayul.md](file:///C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/admin-neis-bot/task-jayul.md)**: **[자율활동 누가기록 작업 체크리스트]** 데이터셋 구조, 컨트롤 ID, 전입생 정보, 작업 순서, 발견된 문제 & 해결 현황을 기록한 작업 추적 문서.
- **[semester-start-timetable-exploration.md](file:///C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/admin-neis-bot/semester-start-timetable-exploration.md)**: **[학기초 시간표 업무 탐색 및 최적화 기록]** `학급시간표관리` 앱 ID(`edu/sw/els/edc/tm/els_edctm00_m00`), 주요 컨트롤, 데이터셋 구조, 2학기 27개 전 주차 시수 편차 0 최적화 해법 및 저장 검증 문서.
- **[walkthrough.md](file:///C:/Users/user/.gemini/antigravity/brain/7f7c27a6-86a3-4c4d-9a53-93acfde9b71c/walkthrough.md)**: **[최종 수행 결과 리포트]** 누가기록 및 2학기 시간표 12개 전 과목 편차 0 실전 서버 저장 완료 내역 및 검증 증명서.

### 2. 데이터 초안 (Data Source)
- **[독서동아리_누가기록_초안 (1).md](file:///C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/admin-neis-bot/data/%EB%8F%85%EC%84%9C%EB%8F%99%EC%95%84%EB%A6%AC_%EB%88%84%EA%B0%80%EA%B8%B0%EB%A1%9D_%EC%B4%88%EC%95%88%20%281%29.md)**: 3학년 2반 독서동아리 18명 학생의 4개 회차별 누가기록 맞춤 내용 및 학생부용 종합 특기사항 한 문장 초안 텍스트.
- **[timetable_optimization_plan_final.json](file:///C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/admin-neis-bot/timetable_optimization_plan_final.json)**: 2학기 전 과목 편차 0 달성을 위한 5, 18, 19, 20주차 60개 셀 최적화 교환 데이터셋.

### 3. 나이스 연동 자동화 스크립트 맵 (Scripts)
- **[neis_club_individual_playwright.py](file:///C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/admin-neis-bot/neis_club_individual_playwright.py)**: 동아리활동 18인 개별 누가기록 순차 주입 및 저장 스크립트.
- **[neis_club_opinion_writer.py](file:///C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/admin-neis-bot/neis_club_opinion_writer.py)**: 동아리활동 종합 특기사항 대입 및 서버 저장 스크립트.
- **[neis_sports_club_writer.py](file:///C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/admin-neis-bot/neis_sports_club_writer.py)**: 학교스포츠클럽(줄넘기) 18세션 일괄 등록 자동화.
- **[neis_jayul_record_writer.py](file:///C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/admin-neis-bot/neis_jayul_record_writer.py)**: 자율활동 누가기록 일괄 등록 스크립트.
- **[neis_collect_semester_timetable.py](file:///C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/admin-neis-bot/neis_collect_semester_timetable.py)**: `cell-click` 이벤트 직접 호출을 통해 1~27주차 전체 시간표 및 과목별 시수표(`dsHcntList`), 개설과목을 전수 수집하는 도구.
- **[neis_execute_save_final.py](file:///C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/admin-neis-bot/neis_execute_save_final.py)**: 플로팅 메뉴 핸들러를 통한 `mbIsModified = true` 활성화 및 타겟 주차별 시간표 저장/모달 자동 처리 마스터 실행기.

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

6. **자율활동 누가기록 기존 데이터 삭제 및 개별 맞춤 기입** (`neis_jayul_delete_all.py`, `neis_jayul_individual_writer.py`)
   - **대상 화면**: 창의적체험활동 > 자율·자치활동(자율활동)관리 > 누가기록 탭 (앱 ID: `edu/sw/els/sdl/ce/els_sdlce00_m01`)
   - **Phase 1: 일괄 삭제**:
     ```bash
     python skills/admin-neis-bot/neis_jayul_delete_all.py --apply
     ```
   - **Phase 2: 개별 맞춤 기입**:
     ```bash
     python skills/admin-neis-bot/neis_jayul_individual_writer.py --apply
     ```

7. **방학 중 41조 연수 자동 상신 (Playwright CDP 모듈)**
   - **실행**:
     ```bash
     python skills/admin-neis-bot/neis_article41_leave.py --apply --confirm APPLY_NEIS --navigate
     ```

8. **교원연수 이수실적 등록 (이수등록) 자동화** (`neis_training_completion.py`)
   - **대상 화면**: `edu/ga/tps/hrd/mm/tps_hrdmm01_p14` (개인정보변경신청 > 연수 탭 > 연수 변경신청 상세 팝업)
   - **기능**: 원격/집합 교육형태(`format_code`: B/C), 법정의무교육(`statutory_category`), 연수기관 직접입력(`btnEduInstCd`), 16개 폼 필드 및 `dsMain` 데이터셋 정밀 바인딩.
   - **안전 모드 (`--fill-only`)**: 저장 버튼을 누르지 않고 필드 채우기만 수행하여 증빙자료 첨부 전 최종 검토 가능.
   - **실행**:
     ```bash
     # 모의 실행 (드라이런)
     python skills/admin-neis-bot/neis_training_completion.py --dry-run --data skills/admin-neis-bot/data/cpr_training_2026.json

     # 폼 필드 자동 채우기만 수행 (검토 후 파일 직접 첨부 및 저장용)
     python skills/admin-neis-bot/neis_training_completion.py --fill-only --data skills/admin-neis-bot/data/cpr_training_2026.json

     # 실제 자동 주입 및 저장/연쇄 모달 확인 완결
     python skills/admin-neis-bot/neis_training_completion.py --apply --confirm APPLY_NEIS --data skills/admin-neis-bot/data/cpr_training_2026.json
     ```

9. **학기초 업무 메뉴 탐색 및 화면 구조 덤프** (`neis_semester_start_explorer.py`, `neis_click_control_dump.py`)
   - **실행**:
     ```bash
     python skills/admin-neis-bot/neis_semester_start_explorer.py
     ```

10. **학급시간표 시수 최적화 및 편차 0(ALL ZERO) 저장 자동화** (`neis_collect_semester_timetable.py`, `neis_execute_save_final.py`)
    - **대상 화면**: 교육과정 > 시간표관리 > 학급시간표관리 (앱 ID: `edu/sw/els/edc/tm/els_edctm00_m00`)
    - **특징**:
      - 27개 전체 주차의 시간표와 기준시수표(`dsHcntList`)를 전수 수집 (`grdWeek._eventListenerList['cell-click'][0]` 호출).
      - 추석 주간(5주차) 체육 9칸 집중 편성, 20주차(조정기 주간 23시간) 완충 편성 및 18~19주차 최소 맞교환으로 12개 전 과목 편차 0 달성.
      - 플로팅 폼 핸들러를 트리거하여 `mbIsModified = true` 활성화 후 `btnSave` 클릭 및 confirm/alert 연쇄 모달 자동 닫기로 실제 DB 저장 완료.
    - **실행 방법**:
      ```bash
      # 1. 2학기 27개 주차 전체 시간표 전수 수집
      python skills/admin-neis-bot/neis_collect_semester_timetable.py

      # 2. 5, 18, 19, 20주차 최적화 시간표 실제 DB 저장 및 모달 자동 처리
      python skills/admin-neis-bot/neis_execute_save_final.py
      ```

---

## 사전 요건 및 웹 자동화 접속 철칙 (필독 ⚠️)

### 1. Chrome 원격 디버깅 실행 (실제 사용자 프로필 필수)
에듀파인/나이스 등 보안 프로그램 및 공동인증서가 탑재되는 국가 교육망 자동화는 임시 프로필을 사용하면 **보안 설치 루프**에 빠지게 됩니다. 반드시 **실제 사용자 기본 프로필** 또는 독립 디버깅 프로필(`C:\neis_chrome_profile`)을 사용하여 실행해야 합니다.
또한 기존 실행된 크롬 인스턴스 점유 및 Singleton 락으로 인해 디버깅 포트 활성화가 차단되는 것을 막기 위해, 다음 **파워쉘 전처리 명령어**를 실행한 뒤 크롬을 띄워야 합니다.

> [!IMPORTANT]
> **크롬 접속 및 런처 트러블슈팅 트라이아드 (핵심수칙)**:
> 1. **학교 내부망 접속**: EVPN 미사용 환경에서는 `https://gbe.neis.go.kr`로 직접 접속합니다.
> 2. **세션 격리 (Session Isolation)**: 터미널 백그라운드(`Session 0`)에서 띄운 Chrome은 사용자 데스크톱 화면에 보이지 않습니다. 반드시 바탕화면 배치 런처(`나이스_학교크롬.bat`)를 사용자가 **더블클릭**하여 사용자 데스크톱 세션(`Session 1`)에서 화면에 띄우도록 합니다.
> 3. **배치 파일 인코딩 (Pure ASCII)**: 윈도우 CMD(CP949)와 UTF-8 간 한글/따옴표 깨짐으로 인해 구문 에러가 나며 튕기는 것을 방지하기 위해, 바탕화면 배치 파일(`.bat`)은 **Pure ASCII (영문 고정)**로 작성해야 합니다.

**[권장] 마스터 크롬 런처 실행 스크립트 (바탕화면 배포용 - Pure ASCII)**:
```bat
@echo off
echo Closing existing Chrome processes...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'name = ''chrome.exe''' | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak > nul

echo Preparing debugging profile directory...
if not exist "C:\neis_chrome_profile" mkdir "C:\neis_chrome_profile"
powershell -NoProfile -Command "Remove-Item -Path 'C:\neis_chrome_profile\SingletonLock' -Force -ErrorAction SilentlyContinue"

echo Launching Chrome with port 9222 on https://gbe.neis.go.kr ...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir="C:\neis_chrome_profile" --no-first-run --no-default-browser-check --start-maximized "https://gbe.neis.go.kr"

pause
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

---

## eXBuilder6 플랫폼 자동화 노하우 (중요)

나이스 시스템은 eXBuilder6 플랫폼 기반이므로 표준 Selenium 제어와 다릅니다. 다음 가이드를 준수해야 에러 없이 자동화가 완료됩니다:

### 1. 그리드 가상화 스크롤 한계 극복 (시간표 주차 선택 등)
- 화면에 보이지 않는 스크롤 하단 행(예: 19~27주차)은 DOM 요소가 생성되지 않아 일반 클릭이 불가합니다.
- **해결**: 그리드 컴포넌트의 내부 이벤트 핸들러(`grid._eventListenerList['cell-click'][0]`)를 대상 행 인덱스로 직접 `.call()` 하여 스크롤 가상화에 구애받지 않고 100% 데이터를 로드합니다:
  ```javascript
  const listeners = grid._eventListenerList && grid._eventListenerList["cell-click"];
  const handler = listeners && (listeners[0].func || listeners[0].handler || listeners[0]);
  handler.call(grid, {control: grid, rowIndex: targetRow, cellIndex: 0, target: grid}, targetRow);
  ```

### 2. 화면 클로저 `mbIsModified` 락 해제 및 실제 DB 저장
- 단순 데이터셋 `setValue()`만으로는 클로저 변수 `mbIsModified`가 `false`로 남아 `btnSave` 실행 시 "저장할 내역이 없습니다" 경고가 발생합니다.
- **해결**: 우클릭 핸들러(`onGrdWeekByClsByTiMousedown`)로 생성되는 플로팅 메뉴의 버튼 핸들러를 임시 실행하여 `mbIsModified = true`를 활성화한 뒤, 데이터셋 변경 및 `commit()`, `btnSave.click()`을 순차 실행합니다.

### 3. 컨펌/알림 모달 닫기
- 컨펌창/알림창은 Selenium Alert가 아닌 eXBuilder6 앱 인스턴스로 뜹니다.
- **해결**: 플랫폼 인스턴스를 순회하여 모달 앱(`app/cmn/confirm`, `app/cmn/alert`)의 확인/예 버튼(`btnConfirm`, `btnOk`)을 찾아 `.click()` 합니다:
  ```javascript
  var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
  apps.forEach(function(ai) {
      if (ai && ai.app && /alert|confirm|cmn/i.test(ai.app.id)) {
          var btn = ai.lookup && (ai.lookup("btnConfirm") || ai.lookup("btnOk"));
          if (btn) btn.click();
      }
  });
  ```

### 4. 그리드 체크박스 제어
- 단순히 데이터셋의 `chk` 값을 `"1"` 로 변경하는 것만으로는 결재 버퍼에 등록되지 않습니다.
- **해결**: 그리드 DOM 요소 ID(`uuid-` 접두사 + `grid.uuid`)를 구하고, 각 행의 체크박스 요소를 직접 찾아 `.click()`을 전송하거나 `grdMain.setCheckRowIndex(rowIndex, true)` API를 사용합니다.

### 5. 봉사활동 실적 자동 연동 트리거
- 봉사활동실적입력 체크박스의 HTML DOM 요소를 구한 뒤 브라우저 고유의 `.click()` 이벤트를 쏘아주면 나이스 내부 이벤트 핸들러가 돌아가면서 장소(예: `(학교)화천초등학교`) 및 시간(`1시간`) 정보가 내부 규칙에 따라 자동으로 정확히 채워집니다.
