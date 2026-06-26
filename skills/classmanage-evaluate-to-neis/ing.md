# classmanage-evaluate-to-neis 개발/실행 기록

## 2026-06-23: NEIS 성취수준 입력 1차 실험

### 목표

- `classmanage-iscream-evaluate/data/2026_1학기_성취기준별_단계배정표.md`의 성취수준을 NEIS 교과평가 화면에 자동 입력한다.
- 우선 한 과목/한 성취기준을 시험 입력한다.

### 준비 결과

- 파서 `scripts/parse_achievement_levels.py`로 원본 markdown을 JSON/CSV로 변환했다.
- 전체 결과:
  - 총 342건
  - 학생 18명
  - 추정 131건
  - 과목별: 국어 36, 도덕 36, 미술 36, 사회 54, 수학 90, 음악 36, 창체 54
- 테스트 대상:
  - 과목: 국어
  - 성취기준: `[4국01-01] 중요한 내용과 주제를 파악하며 듣고 그 내용을 요약한다.`
  - 영역: 듣기·말하기
  - 파일: `scratch/neis-achievement-levels-korean-4guk0101.json`
  - 대상 18명

### NEIS 화면 경로

사용자가 캡처로 확인해 준 경로:

1. 상단 `학급담임`
2. 펼쳐진 메뉴에서 `성적 > 학생평가`
3. 좌측 메뉴 `학생평가 > 교과평가`
4. 탭 `성취기준별 평가`
5. `교과(목)` 선택
6. `영역` 선택
7. `성취기준` 선택
8. 파란색 돋보기 `조회`
9. 아래 `학생별 성취수준 입력` 그리드에 단계 입력

현재 실험 화면:

- 화면 제목: `교과평가`
- 교과: `국어`
- 영역: `듣기·말하기`
- 성취기준: `[4국01-01] 중요한...`
- 조회 후 학생 18명 그리드 표시됨

### 환경/접속 이슈

- 처음에는 Chrome CDP 포트 `9222`가 열려 있지 않았다.
- `admin-neis-bot`과 `admin-edufine` 모두 동일하게 “사용자가 인증서/NEIS 로그인을 수동으로 완료한 Chrome에 CDP로 attach”하는 패턴을 사용한다.
- Chrome을 다음 방식으로 실행해 CDP 연결을 확보했다.

```powershell
Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  -ArgumentList "--remote-debugging-port=9222","--user-data-dir=%TEMP%\neis_chrome_profile","https://gbe.neis.go.kr/jsp/main.jsp"
```

- `http://127.0.0.1:9222/json/version` 응답으로 CDP 연결 확인.
- Python 환경에 `selenium`이 없어 설치했다.

```powershell
python -m pip install selenium
```

### 인코딩 이슈

- PowerShell 파이프/inline Python에서 한글 리터럴이 깨져 필터가 0건으로 나오는 문제가 있었다.
- 예: `subject='도덕'`을 직접 쓰면 깨져서 `0 records`.
- 해결:
  - Python 실행은 `python -X utf8 -` 사용.
  - inline 코드의 한글 상수는 가능하면 유니코드 이스케이프 사용.
  - 파일 입출력은 `encoding="utf-8"` 명시.

### DOM/입력 방식 시행착오

처음에는 Selenium/DOM 클릭으로 콤보박스 옵션을 선택하려고 했다.

확인된 화면 DOM:

- 그리드 DOM id: `uuid-1qv`
- 첫 행 단계 콤보 DOM id: `uuid-1qz`
- 첫 행 단계 셀:
  - `role="gridcell"`
  - `data-cellindex="3"`
  - `aria-label="1행 단계  콤보상자"` 또는 선택 후 `aria-label="1행 단계 "`
- 옵션 목록:
  - `data-id="1 "`: `매우 잘함`
  - `data-id="2 "`: `잘함`
  - `data-id="3 "`: `노력 요함`
  - `data-id="99"`: `임의입력`

실패한 방식:

- DOM `click()` 이벤트 직접 발화
- Selenium `element.click()`
- ActionChains 클릭
- ArrowDown/Enter 키 입력

증상:

- 옵션 hover/active 상태는 바뀌지만 실제 콤보 값이 확정되지 않음.
- 화면 셀의 `innerText`가 빈칸으로 남거나, 열린 상태가 유지됨.

판단:

- NEIS 교과평가 화면은 단순 HTML form이 아니라 CPR/eXBuilder 계열 커스텀 컴포넌트이다.
- DOM 클릭보다 CPR 내부 컨트롤/데이터셋 API를 사용하는 것이 안정적이다.

### CPR/eXBuilder 단서

전역 객체:

- `window.cpr`
- `window.app`
- `cpr.core.Platform.INSTANCE`

실행 중 앱 인스턴스 중 실제 교과평가 화면:

- `edu/sw/els/scr/es/els_scres00_m00`

유용한 컨트롤 id:

- `cmbRelm01`: 영역 콤보
- `cmbSccesCtr`: 성취기준 콤보
- `btnSearch`: 조회 버튼
- `btnSave`: 저장 버튼
- `cmbEvlCn`: 일괄적용 평가기준 선택 콤보
- `grdMain`: 학생별 입력 그리드
- `cmbLvl`: 현재 편집 중인 단계 콤보
- `txa1`: 현재 편집 중인 평가결과 textarea

유용한 데이터셋:

- `dsMain`: 학생별 입력 그리드 데이터
- `dsEvlCn`: 단계 코드별 평가문 데이터
- `dsSccesCtr`: 현재 성취기준 데이터
- `dmSearch`: 검색 조건

`dsMain` 주요 컬럼:

- `stuFlnm`: 학생명, 예: `강시우(전입학)`
- `clsNo`: 번호
- `sbjtNm`: 교과명
- `relmNm`: 영역명
- `sccesCtrCd`: 성취기준 코드 내부값
- `sccesCtrCn`: 성취기준 문장
- `evlCtrCd`: 단계 코드
- `evlCtrNm`: 단계명
- `evlCtrCn`: 평가결과 문장

`dsEvlCn` 단계 매핑:

- `evlCtrCd="1 "`: `매우 잘함`
- `evlCtrCd="2 "`: `잘함`
- `evlCtrCd="3 "`: `노력 요함`
- `evlCtrCd="99"`: `임의입력`

### 성공한 입력 방식

`dsMain`에 직접 값을 넣고 `grdMain.redraw()`를 호출했다.

핵심 JS 패턴:

```javascript
const inst = cpr.core.Platform.INSTANCE
  .getAllRunningAppInstances()
  .find(ai => ai.app && ai.app.id === "edu/sw/els/scr/es/els_scres00_m00");

const ds = inst.lookup("dsMain");
const evl = inst.lookup("dsEvlCn");
const grid = inst.lookup("grdMain");

// dsEvlCn에서 코드별 평가결과 문장 조회
const evlByCd = {};
for (let i = 0; i < evl.getRowCount(); i++) {
  const cd = evl.getValue(i, "evlCtrCd");
  evlByCd[String(cd).trim()] = {
    nm: evl.getValue(i, "evlCtrNm"),
    cn: evl.getValue(i, "evlCtrCn")
  };
}

// 예: 첫 행을 잘함으로 세팅
ds.setValue(0, "evlCtrCd", "2 ");
ds.setValue(0, "evlCtrNm", evlByCd["2"].nm);
ds.setValue(0, "evlCtrCn", evlByCd["2"].cn);

grid.redraw();
```

실제 18명 전체에 대해 데이터셋 값 세팅 성공:

- `ds.isModified()`가 `true`
- `scratch/after-fill-korean-4guk0101.json`에 세팅 결과 저장
- `unmatched: []`

국어 `[4국01-01]` 입력값:

| 번호 | 학생 | 단계 |
| --- | --- | --- |
| 1 | 강시우 | 잘함 |
| 2 | 김가을 | 노력 요함 |
| 3 | 김동규 | 노력 요함 |
| 4 | 김주안 | 노력 요함 |
| 5 | 박민서 | 매우 잘함 |
| 6 | 박서우 | 잘함 |
| 7 | 박현규 | 매우 잘함 |
| 8 | 백다온 | 매우 잘함 |
| 9 | 오지윤 | 노력 요함 |
| 10 | 이서우 | 잘함 |
| 11 | 이예나 | 잘함 |
| 12 | 이윤슬 | 잘함 |
| 13 | 정두영 | 노력 요함 |
| 14 | 조주아 | 잘함 |
| 15 | 천선율 | 잘함 |
| 16 | 한예기 | 매우 잘함 |
| 17 | 황보검 | 매우 잘함 |
| 18 | 최윤채 | 잘함 |

### 국어 과목 완료 상태 (2026-06-23)

| 영역 | 성취기준 | 상태 | 비고 |
| --- | --- | --- | --- |
| 듣기·말하기 | [4국01-01] 중요한 내용과 주제를 파악하며 듣기 | ✅ 저장 완료 | 18/18명 |
| 문학 | [4국05-04] 감각적 표현/시 낭송 | ✅ 저장 완료 | 17/18명 (박서우 미응시→빈칸) |
| 읽기 | [4국02-04] 글에... | ⏸ 수동 처리 예정 | 배정표에 데이터 없음 |

**국어 과목 NEIS 입력 완료** (읽기 영역은 배정표에 없어 수동 처리).

### 기술 노트

- CPR 콤보박스 API: `setValue()`가 아니라 `selectItemByValue()`를 사용해야 한다.
- `getSelection()` 반환값은 circular reference 발생 → `getSelectionFirst().label`로 확인.
- 저장 확인: `ds.isModified() === false` + `ds.getRowState(i) === 1` (unchanged)이면 서버 저장 완료 상태.
- 미응시 학생은 NEIS에 별도 코드 없음 (`99`=임의입력). 교사 수동 처리.

### 다음 과목

남은 과목: 도덕, 수학, 사회, 음악, 미술, 창체

## 2026-06-24: 남은 과목 실전 입력 및 문제 해결

### 기술적 문제 및 해결 과정

1. **과목 자동 전환 블로커 해결**
   - NEIS의 과목 선택기 `udcSbjt`는 커스텀 UDC 컨트롤로서 직접적인 변경이 차단되었으나, 내부 구성 컴포넌트를 스캔한 결과 `cmbUdcAuth`라는 실제 콤보박스가 존재함을 발견했습니다.
   - `cmb.selectItemByValue(osuCd, true)`를 호출함으로써 자동으로 과목이 전환되도록 수정에 성공했습니다.

2. **이벤트 미발화로 인한 영역/성취기준 갱신 누락 해결**
   - 단순히 `selectItemByValue(value)`만 호출하면 eXBuilder6의 하위 콤보박스들이 갱신 이벤트를 받지 못해 이전 영역의 성취기준이 그대로 노출되는 버그가 있었습니다.
   - `selectItemByValue(value, true)`와 같이 두 번째 인자로 `true`(emitEvent)를 넘겨주도록 코드를 수정하여 해결했습니다.

3. **저장 모달(confirm/alert) 자동 닫기 해결**
   - 저장 시 뜨는 "저장하시겠습니까?", "자료의 저장이 완료되었습니다" 모달창은 HTML 표준 버튼이 아니라 eXBuilder의 공통 다이얼로그(`app/cmn/confirm`, `app/cmn/alert`) 컴포넌트였습니다.
   - 전역 Platform 인스턴스에서 해당 다이얼로그를 룩업한 후, 내부의 `btnConfirm` 등 확인 컨트롤을 직접 `.click()` 시켜서 팝업창을 완전히 자동으로 닫도록 뚫어냈습니다.

4. **저장 완료 후 데이터 증발 현상(revert 충돌) 해결**
   - 저장 후 검증을 위해 '재조회'를 실행할 때, 이전에 추가했던 UI 잠금 해제용 `revert()` 로직이 발동하여 서버 반영 완료 전에 데이터를 강제로 날려버리는 현상이 있었습니다.
   - 저장 실행 후 **7초간 충분한 대기 시간**을 주고, **재조회를 수행하지 않은 채** 현재 그리드의 수정 여부(`ds.isModified() === false`)를 즉시 검증함으로써 데이터 보존에 성공했습니다.

5. **시스템 경고창(Alert) 자동 무시 처리**
   - NEIS 보안 세션 만료 경고나 공동인증서 암호 입력 안내 창 등 브라우저 기본 Alert이 뜰 때 프로그램이 죽지 않도록, 모든 동작 전후에 `dismiss_alerts`를 가동하여 자동으로 '확인'을 누르며 진행하도록 보강했습니다.

### 과목별 저장 현황 (2026-06-24)

| 과목 | 성취기준 | 상태 | 비고 |
| --- | --- | --- | --- |
| **국어** | [4국01-01] 중요한 내용 듣기<br>[4국05-04] 감각적 표현 | ✅ 완료 | 18명 입력 완료 / 박서우 미응시(빈칸) |
| **도덕** | [4도01-03] 성실한 생활<br>[4도02-01] 효 실천 | ✅ 완료 | 18명 입력 완료 |
| **사회** | [4사01-01] 장소 소개<br>[4사01-02] 살기 좋은 곳 토의<br>[4사02-02] 과거 살펴보기 | ✅ 완료 | 18명 입력 완료 |
| **수학** | [4수01-03] 세 자리 수 곱셈<br>[4수01-04] 두 자리 수 곱셈<br>[4수03-10] 길이와 시간<br>[4수03-14] 실생활 측정 단위 | ✅ 완료 | 18명 입력 완료 (배정표 4단원, 5단원 매핑) |
| **음악** | [4음01-01] 노래·연주<br>[4음02-01] 신체 표현 | ⏸ 진행 중 | 데이터 입력 후 저장 대기 중 |
| **미술** | [4미02-03] 색·선·형 표현<br>[4미01-01] 감각 도구 | ⏸ 진행 중 | 데이터 입력 후 저장 대기 중 |
| **창체** | 자율, 동아리, 진로 | ❌ 제외 | 교과평가 화면에 없어 수동 입력 대상 |

## 2026-06-26: 교과학습발달상황 평어 (학기말 종합의견) 입력 완료

### 목표
- `data/2026_1학기_국어수학사회도덕_평어_수정안.md` (수정 대상 학생)
- `data/2026_1학기_음악_평어_수정안.md` (전체 18명)
- `data/2026_1학기_미술_평어_수정안.md` (전체 18명)
- 위 세 파일의 평어 수정안을 NEIS 교과학습발달상황(학기말 종합의견) 화면(`edu/sw/els/scr/es/els_scres20_m00`)에 반영 및 저장 완료한다.

### 진행 결과 및 이슈 해결
1. **비활성 탭 및 데이터 로드 문제 해결**:
   - **문제**: dry-run 실행 시 `강시우` 등 학생 선택 클릭이 0건 매칭되어 실패함.
   - **원인**: Chrome 브라우저에 `결석신고서관리` 탭이 활성화되어 있었고, 목적지 탭인 `교과학습발달상황`은 비활성 상태로 백그라운드에 열려 있었음. 이로 인해 `dsStdnt` 데이터셋은 메모리에 존재했으나 DOM 요소가 화면에 없어 XPath 탐색이 실패했고, `조회`가 되지 않아 목록이 빈 상태였음.
   - **해결**: 브라우저 하단 탭 영역에서 visible 상태인 `교과학습발달상황` 탭 요소를 검출하여 클릭하고, `btnSearch`를 호출하여 18명의 학생 목록이 정상적으로 렌더링되게 뚫어냄.
2. **가상화 그리드로 인한 미노출 행 탐색 실패 및 스크롤 폴백 구현**:
   - **문제**: 1차 실반영(`--apply`) 시, 3~18번 학생은 성공했으나 1, 2번 학생(`강시우`, `김가을`)은 `No elements found` 오류로 실패함.
   - **원인**: 이전 dry-run 실행 결과로 그리드 스크롤바가 최하단(`최윤채` 행)에 머물러 있었음. eXbuilder6 Grid는 화면을 벗어난 행을 DOM에서 실제로 탈거(Virtualization)하기 때문에 최상단에 있는 1, 2번 학생은 DOM에 없었음.
   - **해결**: `click_student_row` 함수에 DOM 스크롤 폴백 로직을 이식함. 요소를 찾지 못할 경우 그리드 컨테이너(`.cl-grid`)를 찾아서 자식 요소 중 scrollHeight > clientHeight를 만족하는 모든 영역의 `scrollTop = 0`을 대입하여 최상단으로 복귀하도록 조치함.
3. **실제 저장 및 검증 완료**:
   - 수정본 스크립트를 재구동하여 `강시우`, `김가을`을 포함한 18명 학생 전체의 국어, 수학, 사회, 도덕, 음악, 미술 과목 평어를 성공적으로 입력 및 저장 완료함.
   - 각 학생의 입력 후 `btnSave` 클릭 및 다이얼로그(`app/cmn/confirm`, `app/cmn/alert`) 자동 승인 처리 후 `ds.isModified() === false` 상태를 완벽히 검증함.

## 2026-06-26: 학기말종합의견 평어 입력 완료

### 목표
- `data/2026_1학기_국어수학사회도덕_평어_수정안.md` (수정 대상 학생)
- `data/2026_1학기_음악_평어_수정안.md` (전체 18명)
- `data/2026_1학기_미술_평어_수정안.md` (전체 18명)
- 위 세 파일의 평어 수정안을 NEIS 학기말종합의견 화면(`edu/sw/els/scr/es/els_scres10_m00`)에 반영 및 저장 완료한다.

### 진행 결과 및 이슈 해결
1. **화면 및 데이터셋 구조 파악**:
   - 대상 화면: `edu/sw/els/scr/es/els_scres10_m00` (학기말종합의견)
   - 그리드: `grdMain`, 바인딩 데이터셋 `dsMain` (모든 학생 18명이 단일 그리드 상에 리스트 형태로 노출됨)
   - 과목 선택 UDC: `udcSbjt` (내부에 `cmbUdcAuth` 콤보박스를 포함하고 있어 과목 코드 값으로 전환 제어)
2. **과목 순차 전환 및 데이터셋 일괄 수정**:
   - `udcSbjt` 내부의 `cmbUdcAuth.selectItemByValue(osuCd, true)`를 호출하여 대상 과목(`국어`, `수학`, `사회`, `도덕`, `음악`, `미술`)을 차례로 전환하고, `btnSearch.click()`을 눌러 학생 데이터를 조회함.
   - `dsMain` 데이터셋을 직접 순회하며 `setValue(rowIndex, "gnrlzOpiCn", targetValue)`로 의견 텍스트를 직접 변경하고 `grid.redraw()`를 호출하여 화면을 갱신함.
3. **누적 모달 대피 및 일괄 승인**:
   - 저장 시 eXbuilder6의 확인 모달 다이얼로그(`app/cmn/confirm`, `app/cmn/alert`)가 작동함.
   - 브라우저 백그라운드에 stale(숨겨진/만료된) confirm/alert 앱 인스턴스들이 다수 누적되어 등록되어 있어 첫 번째 모달만 룩업하면 숨겨진 인스턴스를 건드릴 수 있음.
   - 전체 인스턴스 목록을 `filter` 하여 `"app/cmn/confirm"` 및 `"app/cmn/alert"`로 매칭되는 모든 인스턴스를 순회하면서 버튼(`확인`, `btnOk`, `btnConfirm` 등)을 병렬로 직접 트리거하여 닫아줌.
   - 저장 요청 후 7초 대기하며 트랜잭션을 끝내고 `ds.isModified() === false` 상태를 성공적으로 검증함.
4. **실제 저장 및 검증 완료**:
   - `neis_opinion_writer.py` 자동화 스크립트를 사용하여 국어(9명), 수학(10명), 사회(8명), 도덕(6명), 음악(18명), 미술(18명)의 평어를 성공적으로 입력 및 일괄 저장 완료함.
   - 저장 후 다시 dry-run 모드로 확인한 결과, 모든 과목에 대해 `Modifications: 0 students updated`로 이미 나이스 서버에 완벽하게 반영되어 있음이 최종 검증됨.

### 미술 과목 평어 수정안 재입력 및 저장 완료 (2026-06-26)
- **요청**: `2026_1학기_미술_평어_수정안.md` 파일이 업데이트되어 미술 평어만 다시 저장 요청.
- **수행**:
  1. `parse_comment_revisions.py`를 재구동하여 `comment-revisions.json` 갱신.
  2. `neis_opinion_writer.py`에 특정 과목만 필터링하여 실행할 수 있도록 `--subjects` 옵션을 추가하는 개량을 적용.
  3. `python neis_opinion_writer.py --subjects 미술 --apply` 명령으로 미술 과목(18명)에 대한 평어 업데이트 및 일괄 저장 실행.
  4. 저장 후 재차 dry-run 검증 결과 `Modifications: 0`으로 성공적으로 서버 반영 완료를 확인.

## 2026-06-26: 행동특성 및 종합의견 입력 완료

### 목표
- `data/2026_1학기_행동특성_창체v2.md` 파일에 기록된 18명의 학생별 행동특성 및 종합의견 내용을 NEIS 행동특성및종합의견 화면(`edu/sw/els/sdl/bg/els_sdlbg00_m00`)에 반영 및 저장 완료한다.

### 진행 결과 및 이슈 해결
1. **화면 및 데이터셋 구조 파악**:
   - 대상 화면: `edu/sw/els/sdl/bg/els_sdlbg00_m00` (행동특성및종합의견)
   - 그리드: `grdMain`, 바인딩 데이터셋 `dsScrgRec` (모든 학생 18명이 단일 그리드 상에 리스트 형태로 노출됨)
   - 입력 컬럼: `gnrlzOpiCn` (행동특성 및 종합의견 내용)
2. **자동화 스크립트 작성**:
   - `scratch/neis_behavioral_opinion_writer.py`를 작성하여 `dsScrgRec` 데이터셋을 직접 돌며 `setValue(rowIndex, "gnrlzOpiCn", targetValue)`로 행동특성 텍스트를 대입하고 `grid.redraw()`로 갱신함.
3. **Dry-run 및 Revert 충돌 해결**:
   - Dry-run 실행 시 브라우저 내 grid 데이터셋이 수정되었으나 저장되지 않은 채 메모리에 남아, 실반영(`--apply`) 실행 시 변경 사항이 감지되지 않는 문제 발생.
   - `revert_and_search.py` 스크립트를 임시 작성하여 `dsScrgRec.revert()`를 호출해 클라이언트 측의 임시 변경 사항을 롤백한 후 `btnSearch`를 재클릭하여 서버 원본 데이터를 리로드하고 다시 실행함으로써 해결함.
4. **저장 및 검증 완료**:
   - `python neis_behavioral_opinion_writer.py --apply` 명령을 구동하여 18명에 대한 행동특성 텍스트 입력, `btnSave` 클릭 및 모달(`app/cmn/confirm`, `app/cmn/alert`) 자동 확인을 병렬 실행하여 저장을 승인함.
   - 이후 dry-run 모드로 확인한 결과, `Modifications: 0`으로 정상적으로 나이스 서버에 반영 완료됨을 확인 및 검증함.
5. **docx (수정본) 재반영**:
   - 사용자로부터 `2026학년도 3학년 1학기 행동특성 및 종합의견(수정본).docx` 파일을 전달받아 재수정 요청을 처리함.
   - `python-docx` 라이브러리를 이용하여 단일 문단 내에서 개행(`\n`)으로 구분되어 있는 `번호. 이름` 과 `의견 내용`을 분리해 내는 파싱 코드를 `neis_behavioral_opinion_writer.py`에 이식함.
   - `python neis_behavioral_opinion_writer.py --input "skills/classmanage-evaluate-to-neis/data/2026학년도 3학년 1학기 행동특성 및 종합의견(수정본).docx" --apply` 명령을 실행하여 18명 전원의 종합의견 수정본을 재입력 및 저장 완료함.
   - 저장 후 다시 한번 `revert()` 및 `Search` 이후 dry-run 검증 결과 `Modifications: 0`으로 나이스 서버에 완벽하게 최종 저장되었음을 교차 확인 완료함.
