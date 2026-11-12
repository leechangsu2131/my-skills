# NEIS 주간학습 데이터 계약

## 확인된 원본 화면

- NEIS 앱 ID: `edu/sw/els/edc/tm/els_edctm06_m00` (`주간학습안내작성`)
- 주차 목록: `dsWeekList` (`weekCntNm`, `weekCnt`, `weekBgngYmd`, `weekEndYmd`)
- 수업 데이터: `dsWikLrn`, 행마다 교시가 있고 요일별 값은 월~금 접두사 `mon`, `tue`, `wed`, `thu`, `fri`로 구성
- 확인된 조회 제출: `/els_edc_tm06_003.do`
- 조회 응답 데이터: `dsWikLrn`

조회 응답/인증 본문은 이 저장소에 복사하지 않습니다. 학기/월간 자료는 전용 기간 API가 아니라 `dsWeekList`의 주차를 반복 조회합니다. 최초 정상 조회 뒤 자동 학기 조회를 시작하고, 같은 주는 12시간 캐시를 사용합니다. 구현 흐름은 `docs/auto-sync.md`에 기록합니다.

## 필드 매핑

| 정규 필드 | NEIS 필드 |
|---|---|
| `date` | `<day>AllTiYmd` |
| `period` | `pirNm`, 없으면 `pir` |
| `subject` | `<day>EtbSbjtNm` |
| `unit` | `<day>WikLrnUitNm` |
| `content` | `<day>WikLrnCn` |
| `lessonNumber` | `<day>WikLrnRlvtTmsValue` |
| `totalLessons` | `<day>WikLrnAllTmsValue` |
| `textbookPage` | `<day>WikLrnPgeValue` |
| `additionalPage` | `<day>WikLrnAtaPgeValue` |

날짜와 교시는 JavaScript 쪽에서 `YYYY-MM-DD`와 숫자 문자열로 정규화합니다. 날짜+교시+과목으로 중복을 제거하며, 빈 과목/단원/내용/쪽수/차시의 행은 표시하지 않습니다.

## 자동 감지, 보관과 전송

확장 프로그램은 Performance API에서 `/els_edc_tm06_003.do` 조회 완료를 확인한 뒤 앱의 `dsWikLrn`만 읽습니다. `dsWeekList`의 주차 선택과 Cpr 제출 객체를 통해 현재 학기 미캐시 주차도 읽기 조회합니다. 모든 NEIS 데이터셋의 수정 상태를 검사하지 않습니다. 수업내용 데이터셋 자체에 미저장 변경이 있을 때만 동기화를 보류합니다.

필요한 필드만 정규 레코드로 바꿔 Chrome `storage.local`과 `http://127.0.0.1:5101/api/import`에 보냅니다. Chrome 저장소는 이 브라우저 프로필에 로컬 보관하고, 서버는 요청 범위의 기존 레코드를 새 결과로 대체해 메모리에 보관합니다. 원본 요청, 쿠키, `_AUTHDATA`, 학교/학급 식별자는 사용하지 않습니다.
