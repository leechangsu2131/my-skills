# 학생선수 대회 참가 처리 워크플로우

> 대회 공문이 오면: **공문 읽기 → (신규 선수면) 나이스 학생선수 등록 → 학교장확인서 결재요청 → 출석인정결석 처리 기안 → 담임 안내**.
> 스크립트: `neis_student_athlete.py` (결과·캐시는 `data_dir()/student_athlete/`, 저장소에 학생 정보 없음)

## 빠른 사용 (토큰 절약: 출력은 몇 줄, 자세한 건 파일)

```powershell
cd skills/admin-neis-bot
python neis_student_athlete.py status                       # 학생선수·출석인정 허용/사용/잔여일 캐시 (먼저 1회)
python neis_student_athlete.py run "<대회 공문 파일들>" [--students 이름,이름] [--days 2026-10-21~2026-10-23] [--attach "참가 공문"]
#   → case JSON + 기안 txt(본문 클립보드) + 나이스 결재요청 팝업에서 학생 체크(실행 안 함)
python neis_student_athlete.py request <case.json> --apply --confirm APPLY_NEIS [--sancr 이름:검토,이름:결재 --save-sancr]
python neis_student_athlete.py submit --confirm APPLY_NEIS  # 기안창 결재선 확인 후 상신
python neis_student_athlete.py draft <case.json> --edufine  # 에듀파인 기안기에 제목·본문 주입(admin-edufine/playwright_gongmun_draft.py)
python neis_student_athlete.py register <이름> --item 축구 [--personal] [--detail 개인전] [--start 2026-03-02] [--grade 5]
```

- 공문 파일은 에듀파인 `ISSUE-010`(admin-edufine) 방식으로 `Downloads\공문`에 받아 둔 본문·붙임을 그대로 넘긴다(odt/hwpx/pdf/xlsx/txt, hwp·jpg는 못 읽음 → `--students`, `--days`로 보충).
- 대상 학생은 캐시(athletes.json)의 이름이 공문·붙임에 나오면 자동으로 잡는다. 협회 공문처럼 명단이 없으면 `--students`.
- 인정 기간 = 대회 기간의 평일. 공휴일·재량휴업일·이동일은 사람이 판단해 `--days`로 고친다. 잔여일수보다 많으면 경고.
- 제출·상신·저장은 모두 `--apply/--confirm APPLY_NEIS`가 있어야 실행(CLAUDE.md 규칙).

## 나이스 화면 ([체육] > {체육}학교운동부관리 > 학생선수관리)

| 메뉴 | 앱 ID | 쓰임 | 주요 컨트롤 |
|---|---|---|---|
| 학생선수관리 | `edu/sa/phe/phe/am/phe_pheam07_m00` | 선수 등록(1회)·수정·탈퇴 | `btnIns`(등록) → 학생찾기 팝업 `phe_pheam07_p02`(`cmbGrd` 필수, `ipbStuFlnm`, `btnSearch`, `grdStuList`, `btnSubmit`) → 입력폼 `grpInsert`: `cbxSptsYn`(개인운동선수), 종목 `cmbItemCd2`(개인: 전체 76종목)/`cmbItemCd3`(학교운동부 종목), `cmbDtlItemCd`(세부종목), `dti8`(운동시작일자), `txa1`(비고), `btnSave`, `btnBack1`(돌아가기) |
| 학생선수출결관리 | `phe_pheam09_m00` | 출석인정결석 허용(20)/사용/잔여일 조회 | `cmbAyr`, `btnSearch`, `dsList`(stuNm, grd, clsNm, itemCdNm, gijunil, dspAbeDdCnt, dspRestAbeDdCnt) |
| 학교장확인서출력관리 | `phe_pheam10_m00` | 대회마다 학교장확인서 결재요청 → 결재 후 출력 | `btnReq`(결재요청) → 팝업 `phe_pheam10_p00`(`btnSearch`, `grdList` 체크, `btnAprv` 승인요청) → 확인창 → 기안창 `wam_woapm07_p00` → 결재자지정 `wam_woapm07_p04`(ISSUE-005) → 상신. 결재 완료 후 `btnCfm`(학교장확인서출력, 한 명씩) |

- 출석인정결석 자체는 **담임이 학급 출결**에 입력하고, 학생선수출결관리는 그 합계를 보여 준다. 그래서 기안 후 담임 안내 메시지가 필요하다(`draft`가 함께 만듦).
- 승인요청은 학생선수출결관리에 출결 행이 없거나 사용일이 기준일 초과면 거부된다(메시지 SA-PHE-0118 등).

## 출석인정결석 처리 기안 양식 (내부결재)

```
제목: 학생선수(<종목>)의 『<대회명>』 참가에 따른 출석인정결석 처리[ 및 학교장 확인서 발급]
1. 관련: <발신기관> <문서번호>(<시행일>)
2. 위 호와 관련하여, 본교 학생선수(<종목>)의 『<대회명>』 참가에 따른 출석인정결석[ 처리 및 학교장 확인서 발급]을 다음과 같이 처리하고자 합니다.
  가. 대회 개요  1) 대회명  2) 일자/기간  3) 장소
  나. 대상 학생: <학년-반 이름>, …
  다. 출석인정결석 처리 내역  1) 인정 기간: <날짜> (<N>일[간])  2) 내용: <대회명> 참가
  라. 학생선수 학습권 보장 계획  1) 대회 참가 전후 담임교사 주관 기초학력 보충지도 실시함.
 [마. 학교장 확인서 발급  1) 본교는 위 학생선수에 대한 학교장 확인서를 나이스시스템으로 발급해서 발송하고자 함.]
붙임  <대회 공문> 1부.  끝.
```
학교장 확인서가 필요 없는 대회는 `--no-cert`.

## 함정 (자세한 건 ISSUES.md ISSUE-011)

- 메뉴 글자 뒤에 숨은 접근성 문구(`체육 0단계 메뉴항목`, `학생선수관리 2단계`)가 붙어 텍스트 비교가 실패 → 첫 줄에서 `\s*\d단계.*$` 제거 후 비교.
- 콤보·체크박스에 JS로 이벤트를 강제 발생시키면 종목 콤보 항목이 두 번 붙어 "The value of the item is duplicated" → 체크박스는 실제 마우스 클릭, 콤보는 `selectItemByValue`.
- 확인창(`app/cmn/confirm`)이 5~10초 늦게 뜸 → 반복해서 살피며 처리.
- 같은 9222 Chrome의 다른 세션이 내 NEIS 탭을 잡아 화면을 바꿀 수 있음 → 전용 탭(`data_dir/tab.txt`)을 쓰고, 이상하면 새 탭.
