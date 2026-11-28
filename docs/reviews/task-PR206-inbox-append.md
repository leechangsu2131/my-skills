# 검토: PR #206 (S8 school-todo-kakao `InboxSheet.append` 공개 함수)

claude-web-한멜 · S2 · 2026-11-28 · 고치지 않고 보고만 함

## 결론: 합쳐도 됨 🟢
- 제가 PR #183 검토(🟡 "비공개 속성 `_ws` 를 직접 씀")에서 지적한 것을 그대로 풀었다. `InboxSheet.append(line)` 한 함수(RAW·A열, 한 줄 5줄)와 `schedule_panel.py` 한 줄 교체(`inbox._ws.append_row(...)` → `inbox.append(line)`)뿐이라 범위가 작다.
- 시험: school-todo-kakao `test_inbox_append.py` 3 통과, 수업 비서 `test_schedule_panel.py` 34 통과. 일부러 `RAW` → `USER_ENTERED` 로 바꿔 보니 두 쪽 시험 모두 실패(수식 `=…` 이 글자 그대로 들어가는지 지킴).
- 수업 비서 시험은 가짜 시트를 **진짜 `InboxSheet` 로 감싸서** 쓰므로(`FakeDb.inbox`), 칸 → `append` → 시트까지 이어진 모양이 시험된다(별도 연결 확인 불필요).
- 개인정보·비밀값 모양 없음. 다른 스킬 폴더 수정은 이 일(S8)의 범위 안(school-todo-kakao ISSUES 갱신 포함).

## 참고
- `school-todo-kakao` 전체 시험 중 `test_recipients.py::test_sheet_reads_by_header_and_writes_raw_cells` 1개는 이 환경에 `gspread` 가 없어 실패 — main 에서도 같음(이 PR 과 무관).
- 남은 일(PR 본문·ISSUE-008 에 적혀 있음): 설정 값 사전을 받는 `SheetsDb` 열기 함수 → 그것이 되면 T114(서비스 계정 값을 환경 변수에 남기지 않기)도 더 깔끔하게 풀린다.

## 교사 PC 에서 할 일
- 없음(진짜 시트 쓰기는 PR #183 의 확인 항목에 포함).
