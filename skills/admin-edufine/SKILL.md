---
name: admin-edufine
description: >
  경북교육청 에듀파인(K-에듀파인) 행정 업무 자동화 스킬.
  (1) ODT 공문 파싱 후 에듀파인 기안 자동 입력
  (2) 업무포털 K-에듀파인 결재대기 / 공람대기 문서 자동 수집 및 결재 창 열기
---

# admin-edufine 스킬

경상북도 경주 화천초등학교 에듀파인 행정 업무를 자동화합니다.

---

## 기능 1 — 공문 자동 기안 (ODT → 에듀파인 입력)

ODT 공문 파일을 파싱하여 에듀파인 기안 화면에 자동으로 데이터를 입력합니다.

### 실행 방법

```bash
# 1. Chrome 원격 디버깅 모드로 실행 (최초 1회)
launch_chrome.bat

# 2. 공문 자동 기안 실행
python playwright_edufine.py 공문파일.odt
```

### 관련 파일
- [`parse_gongmun.py`](parse_gongmun.py): ODT 공문 파싱 모듈
- [`playwright_edufine.py`](playwright_edufine.py): 에듀파인 기안 자동 입력 스크립트
- [`launch_chrome.bat`](launch_chrome.bat): Chrome 원격 디버깅 모드 실행 배치

---

## 기능 2 — 결재대기 자동화 봇 (NEW)

업무포털(gbe.eduptl.kr) K-에듀파인 전자결재 현황 위젯에서
결재대기 / 공람대기 문서 목록을 자동 수집하고,
K-에듀파인 결재 창을 열어 처리를 지원합니다.

### 사전 조건

1. `launch_chrome.bat` 으로 Chrome을 원격 디버깅 모드(포트 9222)로 실행
2. 업무포털(https://gbe.eduptl.kr)에 공동인증서로 로그인 완료
3. 보안 프로그램(KCaseAgent, MarkAnyDRM) 정상 실행 중

### 실행 방법

```bash
# 결재대기 목록 확인만 (dry-run, 창은 열지 않음)
python edufine_auto_approve.py

# 결재대기 + K-에듀파인 결재 창 열기
python edufine_auto_approve.py --apply

# 공람대기 처리
python edufine_auto_approve.py --tab dsplayWait --apply

# 발송대기 처리
python edufine_auto_approve.py --tab sendWait --apply
```

### 처리 흐름

```
Chrome(9222) 연결
  → 업무포털 탭 확인
  → "결재대기" 탭 클릭 (K-에듀파인 문서함 위젯)
  → kedufine iframe (klef.gbe.kr) 에서 문서 목록 수집
  → result/ 폴더에 txt 파일로 저장
  → [--apply 시] K-에듀파인 결재 창 열기
  → 사용자가 직접 결재 처리
```

### 지원하는 탭 종류

| 옵션 값 | 설명 |
|---------|------|
| `sanctnWait` (기본) | 결재대기 |
| `dsplayWait` | 공람대기 |
| `sanctnView` | 문서진행 |
| `sendWait` | 발송대기 |

### 수집 결과 파일

`result/edufine_sanctnWait_YYYYMMDD_HHMMSS.txt` 형식으로 저장됩니다.

```
K-에듀파인 결재대기 문서 목록
수집 시각: 2026-07-14 10:00:00
처리 모드: dry-run
문서 수: 5건
============================================================

  1. [2026-06-26] [추가신청] 초등학교 체육활동 여건 개선 지원 사업 2차 수요조사 (박은정)
  2. [2026-07-01] [안내] 2026 대한민국 학교체육 축전 참가 안내 (박은정)
  ...
```

### 관련 파일
- [`edufine_auto_approve.py`](edufine_auto_approve.py): 결재대기 자동화 메인 스크립트
- `result/`: 처리된 문서 목록 저장 폴더 (자동 생성)

---

## 주요 기술 정보

### 포털 구조

| 항목 | 값 |
|------|-----|
| 업무포털 URL | `https://gbe.eduptl.kr/bpm_man_mn00_001.do` |
| K-에듀파인 메인 | `https://klef.gbe.kr/keris_ui/main.do` |
| 결재대기 iframe URL | `https://klef.gbe.kr/bms/cz/cb/viw/retrieveSanctnWaitDocListNice.do` |
| iframe 이름 | `kedufine` |
| CDP 디버깅 포트 | `9222` |
| 플랫폼 | Nexacro17 기반 (K-에듀파인), 순수 JSP (결재대기 iframe) |

### 포털 결재 위젯 링크

| 메뉴 | URL |
|------|-----|
| 결재(긴급) | `https://klef.gbe.kr/portal/link.do?link=sanctnWait` |
| 문서진행 | `https://klef.gbe.kr/portal/link.do?link=sanctnView` |
| 공람 | `https://klef.gbe.kr/portal/link.do?link=dsplayWait` |
| 발송대기 | `https://klef.gbe.kr/portal/link.do?link=sendWait` |

---

## 핵심 제약사항

1. **공동인증서 로그인은 자동화하지 않음** — 사용자가 수동으로 진행
2. **결재 버튼 클릭은 자동화하지 않음** — 사용자가 K-에듀파인에서 직접 결재
3. **에듀파인 비밀번호를 코드에 하드코딩하지 않음**
4. K-에듀파인은 Nexacro17 기반으로 보안 모듈(KCaseAgent, MarkAnyDRM) 체크 필요
   → 새 탭으로 자동 열면 `install.html`로 리다이렉트될 수 있음
   → 사용자가 직접 열었을 때만 정상 동작

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| Chrome 연결 실패 | CDP 포트 9222 미실행 | `launch_chrome.bat` 또는 `launch_chrome_default.bat` 실행 |
| 업무포털 탭 없음 | 로그인 안 됨 | 브라우저에서 gbe.eduptl.kr 로그인 |
| kedufine iframe 없음 | "결재대기" 탭 미클릭 | 스크립트가 자동으로 탭 클릭 |
| K-에듀파인 install.html | 임시 디버깅 프로필의 보안 통신 차단 | **해결 방법 A**: 디버깅 브라우저 주소창에 `chrome://flags` 접속 -> `Block insecure private network requests` (또는 `Local Network Access Checks`)를 검색하여 **Disabled**로 변경 후 브라우저 재시작.<br>**해결 방법 B**: 기존 크롬 창을 완전히 닫고 `launch_chrome_default.bat`을 실행하여 본인의 일상 크롬 프로필로 디버깅 시작. |
| 문서 목록 비어있음 | 실제 결재대기 없음 | 정상 상태 |

