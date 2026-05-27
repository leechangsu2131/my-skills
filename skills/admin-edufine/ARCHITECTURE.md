# 공문 자동화 — 아키텍처 제안서 및 구현 체크리스트

## 역할 분담 요약

| 단계 | 자동화 여부 | 담당 |
|------|------------|------|
| ODT 파일 파싱 | ✅ 자동 | `parse_gongmun.py` |
| 에듀파인 브라우저 실행 | ✅ 자동 | `playwright_edufine.py` |
| 공동인증서 로그인 | 🙋 수동 | 사용자 |
| 기안 폼 필드 입력 | ✅ 자동 | `playwright_edufine.py` |
| 기안 본문 작성 | 🤖→🙋 LLM 초안 + 복붙 | 사용자 |
| 결재 상신 | 🙋 수동 | 사용자 |

---

## 구현 체크리스트

### ✅ Phase 1 — 파싱 (완료)

- [x] `parse_gongmun.py` 작성
- [x] `extract_text_from_odt()` — XML 직접 파싱
- [x] `extract_full_text_flat()` — 정규식 매칭용 flat 텍스트
- [x] `parse_sihaeng()` — 시행 공문번호/일자
- [x] `parse_jeopsu()` — 접수 공문번호/일자
- [x] `parse_title()` — 제목
- [x] `parse_susin()` — 수신
- [x] `parse_balshincheo()` — 발신처
- [x] `parse_gwanryeon()` — 관련 공문번호
- [x] 실제 ODT 파일 테스트 통과

### 🚧 Phase 2 — Playwright 자동화

- [ ] `playwright_edufine.py` 기본 골격 작성
- [ ] 에듀파인 실제 URL 확인 및 상수화
- [ ] 로그인 완료 감지 로직 (`wait_for_url` 또는 DOM 요소)
- [ ] 기안 메뉴 셀렉터 파악 (iframe 구조 확인 필수)
- [ ] 각 입력 필드 셀렉터 매핑:
  - [ ] 제목 필드
  - [ ] 관련 공문번호 필드
  - [ ] 시행일자 필드
  - [ ] 기타 메타데이터 필드
- [ ] 본문 입력 대기 로직
- [ ] 오류 처리 (셀렉터 못 찾을 때 안내 메시지)

### 🔲 Phase 3 — 통합 CLI

- [ ] `main.py` 작성
  - [ ] `argparse`로 ODT 경로 인자 처리
  - [ ] 파싱 → 미리보기 → 확인 → 자동화 연결
  - [ ] `--dry-run` 플래그 (파싱 결과만 출력, 브라우저 실행 안 함)

### 🔲 Phase 4 — GUI (선택)

- [ ] `gui_app.py` 작성 (tkinter 또는 PyQt6)
- [ ] 파일 선택 다이얼로그
- [ ] 파싱 결과 테이블 미리보기
- [ ] 자동 입력 시작 버튼
- [ ] 진행 상태 표시

---

## Playwright 구현 가이드

### 에듀파인 iframe 구조 대응

에듀파인은 iframe이 중첩되는 구조가 많습니다. 셀렉터 탐색 순서:

```python
# 방법 1: 직접 셀렉터
page.fill('#input_title', data['제목'])

# 방법 2: iframe 안에 있는 경우
frame = page.frame_locator('iframe#main_frame').frame_locator('iframe#work_frame')
frame.locator('#input_title').fill(data['제목'])

# 방법 3: name 속성으로 frame 찾기
frame = page.frame(name='mainFrame')
```

### 로그인 완료 감지 패턴

```python
# 방법 A: URL 변화 감지
page.wait_for_url("**/main**", timeout=120_000)  # 2분 대기

# 방법 B: 특정 요소 등장 감지
page.wait_for_selector('#logout_btn', timeout=120_000)

# 방법 C: 콘솔에서 사용자 Enter 대기 (가장 단순)
input("로그인 완료 후 Enter를 누르세요: ")
```

### 느린 정부 시스템 대응

```python
page.set_default_timeout(30_000)          # 기본 타임아웃 30초
page.wait_for_load_state('networkidle')   # 네트워크 안정화 대기
page.wait_for_timeout(800)                # 짧은 대기 (애니메이션 등)
```

---

## 파싱 개선 포인트 (추후 작업)

1. **HWPX 지원 추가**: ODT와 별도로 HWPX 파서 연결
   - 기존 `parse_gongmun.py`의 함수들은 텍스트 기반이므로 HWPX 텍스트 추출 후 동일 함수 재사용 가능

2. **다중 파일 배치 처리**: 폴더 내 모든 ODT 파일을 순서대로 처리

3. **파싱 결과 저장**: JSON 또는 CSV로 누적 저장 (공문 이력 관리)

4. **실패 케이스 강화**:
   - 공문번호가 없는 공문
   - 날짜 형식이 다른 경우 (`2026년 4월 3일` 등)
   - 테이블 구조가 다른 발신처 기관

---

## 테스트 방법

```bash
# 파싱만 테스트
python parse_gongmun.py samples/sample.odt

# Playwright dry-run (브라우저만 열고 입력 안 함)
python playwright_edufine.py --dry-run

# 전체 통합 실행
python main.py samples/sample.odt
```
