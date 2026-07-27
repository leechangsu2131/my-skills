# 자율활동 누가기록 일괄 입력 자동화 작업 체크리스트

> **대상 화면**: 나이스 > 창의적체험활동 > 자율·자치활동(자율활동)관리 > 누가기록 탭
> **앱 ID**: `edu/sw/els/sdl/ce/els_sdlce00_m01`
> **시작일**: 2026-07-17
> **상태**: ✅ 최종 완료 (기존 일괄 삭제 및 학생별 18인 개별 기입 물리 저장 검증 완료)

---

## 환경 정보

| 항목 | 값 |
|------|-----|
| 학년도/학년/반 | 2026 / 3학년 / 2반 |
| 학생 수 | 18명 |
| 전입생 | 최윤채(#18) - 전입일: 2026.05.11 |
| 활동일자 총 개수 | 45건 (직접입력 6건 제외 → **39건 자동 대상**) |
| 스킬 파일 위치 | `skills/admin-neis-bot/neis_jayul_record_writer.py` (예정) |

---

## 핵심 데이터셋 구조 (분석 완료 ✅)

### dsActYmd (활동일자 리스트, 45행)
| 컬럼 | 설명 |
|------|------|
| `actYmd` | 날짜 (YYYYMMDD) |
| `actYmdNm` | 표시명 (예: "2026.03.03.(화)") |
| `comptHr` | 이수시간 |
| `direcInptYn` | 직접입력 여부 ("Y" = 전입생용 SKIP) |
| `rmkCn` | 시간표내역 (예: "[1, 2교시]", "{직접입력}") |

### dsGicRec (학생 그리드, grdMain 바인딩, 18행)
| 주요 컬럼 | 설명 |
|----------|------|
| `clsNo` | 번호 |
| `stuFlnm` | 성명 |
| `schorFlctnYmd` | 전입학 날짜 (최윤채: 20260511) |
| `speclActSpablMteCn` | 활동내용 (주간학습에서 가져온 내용) |

---

## 주요 컨트롤 ID

| 컨트롤 | ID | 용도 |
|--------|-----|------|
| 날짜 그리드 | `grdActYmd` | 좌측 활동일자 리스트 |
| 학생 그리드 | `grdMain` | 중앙 학생 체크/내용 표시 |
| 전체 체크 | `grdMain.checkAllRow(true)` | 학생 전체 선택 |
| 개별 체크 해제 | `grdMain.setCheckRowIndex(idx, false)` | 전입생 해제 |
| 주간학습 가져오기 | `btnWeek` | 주간학습 팝업 호출 |
| 일괄등록 | `btnBndeSave` | 일괄등록 |
| 저장 | `btnSave` | 저장 |
| 삭제 | `btnDelete` | 삭제 |
| 출결현황조회 | `btnAttePnsta` | 출결현황 |

---

## 작업 순서 체크리스트

### Phase 1: UI 구조 조사 ✅
- [x] 나이스 화면 스크린샷 캡처
- [x] 앱 ID 확인 (`els_sdlce00_m01`)
- [x] dsActYmd 데이터셋 구조 분석 (45건, 컬럼 5개)
- [x] dsGicRec 데이터셋 구조 분석 (18명, 전입생 1명)
- [x] 전입생 정보 파악: 최윤채 #18, 전입일 20260511
- [x] 직접입력(direcInptYn=Y) 날짜 6건 식별

### Phase 2: 인터랙션 탐색 🔄
- [x] 날짜 선택 메커니즘 확인 (`grdActYmd.selectRows()`)
- [x] 학생 전체 체크 메서드 확인 (`checkAllRow`, `setCheckRowIndex`)
- [ ] 주간학습 가져오기 팝업 구조 분석
  - [x] 학생 미선택 시 "선택된 학생이 없습니다" 알림 확인
  - [x] 학생 체크 후 팝업 앱 ID/컨트롤/데이터셋 분석
  - [x] "주간학습내용적용하기" 버튼 ID 확인
  - [x] 여러 교시 존재 시 컨텐츠 선택 방법 확인
- [x] 저장 플로우 확인 (confirm/alert 모달 처리)

### Phase 3: 자동화 스크립트 작성
- [x] `neis_jayul_record_writer.py` 메인 스크립트 작성
  - [x] 날짜 순회 루프 (직접입력 SKIP)
  - [x] 학생 전체 체크 + 전입생 조건부 해제
  - [x] 주간학습 가져오기 + 적용
  - [x] 저장 + 모달 처리
- [x] `--limit N` 옵션 (테스트용 N건만)
- [x] `--apply` 옵션 (실제 저장)

### Phase 4: 테스트 실행
- [x] 드라이런 1-2건 테스트
- [x] 전입생(05.11 이전 날짜) 체크 해제 검증
- [x] 전입생(05.11 이후 날짜) 체크 유지 검증
- [x] 주간학습 적용 결과 캡처 검증

### Phase 5: 전체 실행 & 검증
- [x] 39건 전체 일괄 실행 (`--apply`)
- [x] 완료 후 스크린샷 검증
- [x] SKILL.md, ing.md 최종 업데이트

---

## 발견된 문제 & 해결 현황

| # | 문제 | 상태 | 해결 |
|---|------|------|------|
| 1 | `setSelectedRowIndex` 메서드 없음 | ✅ 해결 | `selectRows([idx])` + `dispatchEvent("selection-change")` 사용 |
| 2 | `checkAll` / `setCheckedAll` 메서드 없음 | ✅ 해결 | `checkAllRow(true)` 메서드 확인 |
| 3 | 주간학습 가져오기 전 학생 체크 필수 | ✅ 해결 | 순서: 학생체크 → 주간학습가져오기 |
| 4 | 주간학습 팝업 구조 미분석 | ✅ 해결 | 셀 DOM mousedown/mouseup/click 정밀 클릭 시뮬레이션 적용 |
| 5 | `JS_CLOSE_ALERT`에서 널 참조 에러 | ✅ 해결 | 다이얼로그 닫기 함수 널가드 및 try-catch 루프 보강 완료 |

---

## eXBuilder6 그리드 API 레퍼런스 (이 화면 한정)

> 이 화면(`els_sdlce00_m01`)에서 확인된 그리드 체크 관련 메서드 목록 (메서드 열거 조사 완료)

```javascript
// 체크박스 관련
grdMain.setCheckRowIndex(rowIndex, true/false)  // 개별 행 체크/해제
grdMain.getCheckRowIndices()                     // 체크된 행 인덱스 배열 반환
grdMain.isCheckedRow(rowIndex)                   // 특정 행 체크 여부
grdMain.checkAllRow(true/false)                  // 전체 체크/해제
grdMain.clearAllCheck()                          // 전체 체크 해제

// 선택 관련
grdMain.selectRows([idx])                        // 행 선택
grdMain.getSelectedRowIndices()                  // 선택된 행 인덱스
grdMain.clearSelection()                         // 선택 해제

// 알림창 닫기 (널가드 필수)
try {
    var alertApp = cpr.core.Platform.INSTANCE.getAllRunningAppInstances()
        .find(function(ai) { return ai && ai.app && ai.app.id === "app/cmn/alert"; });
    if (alertApp) {
        var btn = alertApp.lookup("btnConfirm");
        if (btn) btn.click();
    }
} catch(e) { /* 인스턴스 소멸 대비 */ }
```
