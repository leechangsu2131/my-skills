---
name: classmanage-evaluate-to-neis
description: Parse classmanage-iscream-evaluate achievement-level markdown tables and prepare or run safe NEIS achievement-level entry automation for gbe.neis.go.kr. Use when the user wants to enter 성취기준별 성취수준/단계(매우잘함, 잘함, 노력요함, 미응시) from 2026_1학기_성취기준별_단계배정표.md or similar class evaluation tables into NEIS, especially by reusing admin-neis-bot browser automation patterns.
---

# Classmanage Evaluate To NEIS

## Purpose

Use this skill to move 성취기준별 단계 배정표 data from `classmanage-iscream-evaluate` into NEIS (`https://gbe.neis.go.kr/`) with a guarded workflow: parse first, inspect the NEIS screen, dry-run, then enter only after explicit confirmation.

## Source Skills

- Read `skills/classmanage-iscream-evaluate/SKILL.md` when the source file format or i-scream evaluation context is unclear.
- Reuse `skills/admin-neis-bot/launch_chrome.bat` to open Chrome with remote debugging on port `9222`.
- Reuse the NEIS frame/field discovery style from `skills/admin-neis-bot/neis_modal_map.py` when selectors do not match the current NEIS screen.

## Standard Workflow

1. Parse the markdown table.

```powershell
python skills/classmanage-evaluate-to-neis/scripts/parse_achievement_levels.py `
  --input skills/classmanage-iscream-evaluate/data/2026_1학기_성취기준별_단계배정표.md `
  --json scratch/neis-achievement-levels.json `
  --csv scratch/neis-achievement-levels.csv `
  --summary
```

2. Ask the user to open NEIS with `skills/admin-neis-bot/launch_chrome.bat`, log in manually, and navigate to the 성취기준별 평가/성취수준 입력 screen.

3. Diagnose the current NEIS screen before any entry.

```powershell
python skills/classmanage-evaluate-to-neis/scripts/neis_achievement_entry.py `
  --records scratch/neis-achievement-levels.json `
  --diagnose `
  --dump scratch/neis-fields.json
```

4. Build or update a selector config from the diagnostic dump. Start from `references/selector-config.example.json`.

5. Run a dry-run.

```powershell
python skills/classmanage-evaluate-to-neis/scripts/neis_achievement_entry.py `
  --records scratch/neis-achievement-levels.json `
  --selector-config scratch/neis-selector-config.json `
  --dry-run
```

6. Apply only after the user has reviewed the dry-run summary and explicitly approves real NEIS entry.

```powershell
python skills/classmanage-evaluate-to-neis/scripts/neis_achievement_entry.py `
  --records scratch/neis-achievement-levels.json `
  --selector-config scratch/neis-selector-config.json `
  --apply `
  --confirm APPLY_NEIS
```

## 교과학습발달상황 평어 입력 Workflow

평어 수정안 파일들(`2026_1학기_국어수학사회도덕_평어_수정안.md`, `2026_1학기_음악_평어_수정안.md`, `2026_1학기_미술_평어_수정안.md` 등)을 분석하여 NEIS 교과학습발달상황 입력 화면에 자동 입력하는 절차와 핵심 로직입니다.

### 1. 화면 및 데이터셋 구조
- **대상 화면**: `edu/sw/els/scr/es/els_scres20_m00` (교과학습발달상황)
- **왼쪽 학생 목록 그리드**: `grdStdnt`, 바인딩 데이터셋 `dsStdnt` (컬럼: `stdntNm` 또는 `stuFlnm` 학생명, `stuInvlNo` 식별자)
- **오른쪽 교과별 평어 그리드**: `grdCurrByRec` (또는 `grdMain`), 바인딩 데이터셋 `dsGnrlzOpinListByYear` (컬럼: `sbjtNm` 과목명, `gnrlzOpiCn` 종합의견내용)
- **기타 컨트롤**: 조회(`btnSearch`), 저장(`btnSave`)

### 2. 표준 입력 로직 및 팁
1. **탭 활성화 및 조회**: 
   - 화면 하단 탭바에서 `교과학습발달상황` 탭이 활성화되어 있는지 확인하고, 비활성 상태인 경우 visible한 탭 요소를 찾아 클릭하여 전환합니다.
   - 학년, 반 등의 필터를 확인하고 `btnSearch`를 클릭하여 학생 목록을 로드합니다.
2. **가상화 그리드 스크롤 처리 (중요)**:
   - 학생 그리드는 가상화(Virtualized Grid)되어 있어 화면 밖의 행은 DOM에서 제거됩니다.
   - 첫 번째 학생부터 클릭 시, 그리드가 아래로 스크롤되어 있으면 상단 학생(`강시우`, `김가을` 등)이 DOM에 없어 XPath 탐색이 실패합니다.
   - **해결책**: 학생 클릭 실패 시 그리드 DOM 요소(`.cl-grid`)를 찾아 자식 중 스크롤 가능한 요소의 `scrollTop = 0`을 재귀적으로 실행하여 최상단으로 강제 스크롤 시킨 후 1초 대기하고 다시 탐색합니다.
3. **성명 부분 일치 매칭**:
   - 그리드 DOM에는 이름이 `강시우(전입학)` 형태로 렌더링될 수 있으므로, XPath `//*[contains(text(), '강시우')]` 형식의 부분 일치 패턴을 사용하여 탐색합니다.
   - 셀 탐색 후 `scrollIntoView({block: 'center'})` 및 JS 강제 클릭(`arguments[0].click()`)을 적용해 브라우저의 선택 인터랙션을 트리거합니다.
4. **학생별 개별 저장 루프**:
   - 학생 한 명을 클릭하고 디테일 로드를 위해 2초 대기합니다.
   - 디테일 데이터셋 `dsGnrlzOpinListByYear`를 순회하며 수정 대상 과목의 기존 값과 목표 수정안을 비교합니다.
   - 변경 사항이 있을 경우 데이터셋 값을 갱신(`ds.setValue()`)하고 `btnSave`를 클릭합니다.
   - 저장 시 호출되는 eXBuilder 공통 모달 창(`app/cmn/confirm` 및 `app/cmn/alert`)을 자동 룩업하여 `확인` 버튼을 클릭 처리합니다.
   - 서버 트랜잭션 대기(7초) 후 `ds.isModified() === false`로 최종 성공 여부를 확인하며 순회합니다.

## 학기말 종합의견 입력 Workflow

평어 수정안 파일들(`2026_1학기_국어수학사회도덕_평어_수정안.md`, `2026_1학기_음악_평어_수정안.md`, `2026_1학기_미술_평어_수정안.md` 등)을 분석하여 NEIS 학기말 종합의견 입력 화면에 자동 입력하는 절차와 핵심 로직입니다.

### 1. 화면 및 데이터셋 구조
- **대상 화면**: `edu/sw/els/scr/es/els_scres10_m00` (학기말종합의견)
- **그리드 구조**: `grdMain`, 바인딩 데이터셋 `dsMain` (모든 학생 18명이 단일 그리드 상에 리스트 형태로 노출됨)
  - 컬럼: `stdntNm` (성명), `gnrlzOpiCn` (학기말 종합의견 내용), `sbjtCdNm` (교과목명)
- **과목 선택 UDC**: `udcSbjt` (내부에 `cmbUdcAuth` 콤보박스를 포함하고 있어 과목 코드 값으로 전환 제어)
- **기타 컨트롤**: 조회(`btnSearch`), 저장(`btnSave`)

### 2. 표준 입력 로직 및 팁
1. **탭 활성화 및 조회**:
   - 하단 탭바에서 `학기말종합의견` 탭을 찾아 활성화합니다. (중요: 모달 팝업이 활성화되어 있을 경우 탭 전환이 불가능하므로, 열려 있는 모달을 먼저 종료해야 합니다.)
2. **과목 순차 전환**:
   - `udcSbjt` 내부의 `cmbUdcAuth.selectItemByValue(osuCd, true)`를 호출하여 대상 과목(`국어`, `수학`, `사회`, `도덕`, `음악`, `미술`)을 차례로 전환합니다.
   - 과목 전환 후 `btnSearch.click()`을 눌러 학생 18명의 종합의견 데이터를 조회합니다.
3. **데이터셋 직접 수정 및 일괄 저장**:
   - 화면 클릭을 순회할 필요 없이, `dsMain` 데이터셋을 직접 돌며 `dsMain.setValue(rowIndex, "gnrlzOpiCn", targetValue)`로 의견 텍스트를 직접 변경하고 `grid.redraw()`를 호출하여 화면을 갱신합니다.
4. **누적 모달 대피 및 일괄 승인 (중요)**:
   - 저장 시 eXbuilder6의 확인 모달 다이얼로그(`app/cmn/confirm`, `app/cmn/alert`)가 작동합니다.
   - **주의**: 세션 만료 및 여러 원인으로 인해 브라우저 백그라운드에 stale(숨겨진/만료된) confirm/alert 앱 인스턴스들이 다수 누적되어 등록될 수 있습니다.
   - **해결책**: 단순히 첫 번째 모달만 룩업하면 숨겨진 인스턴스를 건드릴 수 있어 실반영 및 닫기가 누락됩니다. 따라서 전체 인스턴스 목록을 `filter` 하여 `"app/cmn/confirm"` 및 `"app/cmn/alert"`로 매칭되는 모든 인스턴스를 순회하면서 버튼(`확인`, `btnOk`, `btnConfirm` 등)을 병렬로 직접 트리거하여 닫아줍니다.
   - 저장 요청 후 7초 대기하며 트랜잭션을 끝내고 `ds.isModified() === false` 상태를 검증합니다.

## 행동특성 및 종합의견 입력 Workflow

행동특성 초안 파일(`2026_1학기_행동특성_창체v2.md` 등)을 분석하여 NEIS 행동특성 및 종합의견 입력 화면에 자동 입력하는 절차와 핵심 로직입니다.

### 1. 화면 및 데이터셋 구조
- **대상 화면**: `edu/sw/els/sdl/bg/els_sdlbg00_m00` (행동특성및종합의견)
- **그리드 구조**: `grdMain`, 바인딩 데이터셋 `dsScrgRec` (모든 학생 18명이 단일 그리드 상에 리스트 형태로 노출됨)
  - 컬럼: `stdntNm` 또는 `stuFlnm` (성명), `gnrlzOpiCn` (행동특성 및 종합의견 내용)
- **기타 컨트롤**: 조회(`btnSearch`), 저장(`btnSave`)

### 2. 표준 입력 로직 및 팁
1. **화면 활성화**:
   - 브라우저에 `행동특성및종합의견` 화면이 활성화되어 있는지 확인하고 조회(`btnSearch`)를 클릭하여 학생 목록을 그리드에 로드합니다.
2. **데이터셋 직접 수정 및 일괄 저장**:
   - `dsScrgRec` 데이터셋을 직접 순회하며 `dsScrgRec.setValue(rowIndex, "gnrlzOpiCn", targetValue)`로 의견 내용을 대입하고, `grid.redraw()`를 호출해 화면을 갱신합니다.
3. **Dry-run과 Revert의 처리 (중요)**:
   - 만약 dry-run 등을 실행하여 데이터셋이 client-side에서 이미 변경된 상태라면, 실제 반영(`--apply`)을 위해 다시 실행할 때 변경 상태가 감지되지 않을 수 있습니다.
   - 따라서 실반영을 시작하기 전, `dsScrgRec.isModified()` 상태를 검사하여 변경 사항이 있다면 `dsScrgRec.revert()`를 호출해 롤백한 후 `btnSearch.click()`으로 원본 데이터를 다시 조회하고 수행해야 충돌을 피할 수 있습니다.
4. **저장 및 확인 모달 닫기**:
   - 저장 시 `btnSave.click()`을 호출하고, eXbuilder6의 확인 모달(`app/cmn/confirm`, `app/cmn/alert`)을 자동 탐색하여 닫습니다.
   - 저장 후 7초 이상 대기하며 트랜잭션을 처리하고, `dsScrgRec.isModified() === false` 상태를 검증합니다.

## 창의적 체험활동 및 진로활동 입력 Workflow

창체 초안 파일(`2026_1학기_행동특성_창체v2.md` 등)을 분석하여 NEIS 학생부자료기록/창의적체험활동 입력 화면에 자동 입력하는 절차와 핵심 로직입니다.

### 1. 화면 및 데이터셋 구조
- **대상 화면**: `edu/sw/els/sdl/ce/els_sdlce06_m00` (학생부자료기록 목록)
- **그리드 구조**: `grdMain`, 바인딩 데이터셋 `dsScrgRec` (한 학생당 자율·동아리활동, 진로활동, 청소년단체 등 복수의 행이 생성되어 목록 형태로 노출됨)
  - 컬럼: `stuFlnm` (성명), `actScCd` (활동영역 코드), `speclActSpablMteCn` (특기사항 내용)
- **주요 영역 구분 코드 (actScCd)**:
  - `20`: 자율·자치활동 및 동아리활동 (통합 입력)
  - `14`: 진로활동 (개별 입력)
- **기타 컨트롤**: 조회(`btnSearch`), 저장(`btnSave`), 특기사항 텍스트 영역(`txaSpeclActSpablMteCn`)

### 2. 표준 입력 로직 및 팁
1. **조회 및 목록 로드**:
   - 학년, 반 등의 검색 조건을 확인하고 `btnSearch`를 클릭하여 학생별 영역 목록을 로드합니다.
2. **동일 그리드 내 복수 영역 매핑 처리**:
   - `dsScrgRec` 데이터셋은 학생당 여러 개의 행을 가지므로, 단순 성명 매칭 외에도 `actScCd` 값을 분석해 알맞은 텍스트를 대입해야 합니다.
   - 데이터셋을 루프 돌며 `actScCd === "20"`인 행에는 자율·동아리 의견을, `actScCd === "14"`인 행에는 진로활동 의견을 매칭하여 `speclActSpablMteCn` 컬럼에 대입합니다.
3. **저장 및 확인 모달 닫기**:
   - `btnSave.click()`을 호출하고, eXbuilder6의 확인 모달(`app/cmn/confirm`, `app/cmn/alert`)을 자동 탐색하여 순차적으로 승인 및 닫기 처리합니다.
   - 저장 후 7초 이상 대기하며 서버 트랜잭션을 끝내고 `dsScrgRec.isModified() === false` 상태를 확인합니다.

## Safety Rules

- Default to `--dry-run` or `--diagnose`; never use `--apply` without the user's explicit approval for the current run.
- Do not store NEIS credentials. The teacher logs in manually in the remote-debugging Chrome window.
- Do not click final 저장/제출/반영 buttons unless the selector config intentionally names that button and the run uses `--apply --confirm APPLY_NEIS`.
- If the NEIS screen structure has changed, stop after `--diagnose` and update selectors rather than guessing.
- Preserve `(추정)` in the parsed records as `inferred: true`; show inferred counts in previews so the teacher can review them before entry.

## EVPN 환경(가정 접속) 주의사항

- **인터넷 차단 제약**: EVPN 접속 후에는 외부 인터넷이 완전히 차단되고 오직 나이스 접속만 가능해집니다. 이로 인해 셀레늄(Selenium)이 드라이버 정보를 체크하거나 ChromeDriver를 새로 다운로드해야 하는 경우 네트워크 오류가 발생합니다.
- **사전 조치 필수**: EVPN 연결을 완료하기 전에 다음 작업을 먼저 수행하여 인터넷 통신이 필요한 준비 단계를 끝내야 합니다:
  1. 원격 디버깅용 크롬 실행(`launch_chrome.bat`) 및 필요시 구글 계정 로그인.
  2. 일반 인터넷 상태에서 자동화 스크립트의 `--dry-run` 명령을 최소 1회 수행하여 크롬 버전에 매칭되는 **ChromeDriver의 자동 다운로드 및 로컬 캐싱** 완료하기.
  3. 드라이버 다운로드가 정상 완료(또는 나이스 화면이 없어 `els_sdlbg00_m00 not found` 등이 발생하는 단계 진입)된 것을 확인한 후 EVPN 로그인/접속 진행하기.
- **로컬 포트 통신**: EVPN 연결 후 외부 인터넷이 차단되더라도 `localhost:9222`를 통한 파이썬-크롬 간의 로컬 제어 통신은 루프백 주소이므로 영향받지 않고 정상 작동합니다.


## Data Shape

The parser emits records like:

```json
{
  "subject": "국어",
  "student": "강시우",
  "standard_code": "4국05-04/05",
  "assessment": "1단원: 시 낭송",
  "level": "잘함",
  "inferred": false,
  "raw_level": "잘함"
}
```

Valid levels are `매우잘함`, `잘함`, `노력요함`, and `미응시`. Keep unknown values in the output and surface them during review instead of silently converting them.

## Selector Config

Read `references/selector-config.example.json` before creating a real selector config. The automation script supports simple field filling and is intentionally conservative. If the live NEIS screen requires row-specific grid editing, first use `--diagnose` to capture the DOM and extend the script/config for that screen.

## Debug Notes

Read `ing.md` when continuing NEIS automation work. It records the live-screen path, CPR/eXBuilder control IDs, dataset fields, errors encountered, and the working approach for filling `dsMain` rows.
