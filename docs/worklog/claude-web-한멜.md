# claude-web-한멜 일지

- 2026-11-28 13:05 T112 이어받음 (브랜치 task/T112-voice-cmd, 앞 — claude-web-yi2131@naver: 2026-11-28 06:52 T112 시작 (브랜치 task/T112-voice-cmd))
- 2026-11-28 13:09 S2 (review-pr190) 시작 (브랜치 task/S2-review-pr190)
- 2026-11-28 13:09 S2 (review-pr190) PR 올림 — PR #190(T112 말로 명령) 검토 글 docs/reviews/task-PR190-voice-cmd.md. 합쳐도 됨. 시험 28 통과, 같은 일을 따로 만들어 비교·입력 직접 확인(🟡 타이머 상한 없음). 메모: T112 를 이어받았으나 앞 작업자가 먼저 끝내 PR #190 이 있어 내 구현은 접음
- 2026-11-28 14:40 T110 이어받음 (브랜치 task/T110-theme-layout, 앞 — claude-web-소연: 2026-11-28 13:10 T110 그만둠 — claude-web-173 이 같은 때 만들어 PR #189 를 올려서 내 구현은 올리지 않음)
- 2026-11-28 14:42 claude-web-한멜 T110 PR 올림(#189 고침) — 검토 의견 3가지 반영: ①숨김·접힘을 class 대신 data-layout-* 속성으로(새로 고침·단계 이동에도 유지, 🔴) ②어두운 화면 교시 탭 색 ③좁은 화면 ⚙ 를 📞 옆 4번째 칸으로. 확인: Node 13·파일 시험 10 통과, Playwright 로 새로 고침 후 숨김 유지·390폭 ⚙ 같은 줄·🎯 화면에서 지금 할 일 보임·오류 0, 옛 코드로는 둘 다 재현됨. 교사 PC: 실제 휴대폰 머리글 모양
- 2026-11-28 14:48 S2 (review-pr192-195) 시작 (브랜치 task/S2-review-pr192-195)
- 2026-11-28 14:49 S2 (review-pr192-195) PR 올림 — PR #192(받아쓰기 사전 칸)·#195(Python 실행기 점검) 검토 글 docs/reviews/task-PR192-195-stt-words-ui-check-setup.md. 둘 다 합쳐도 됨. 확인: 시험 65+9 / 139 통과, bat 와 점검 규칙 대조, 저장 엣지 직접 실행(🟡 접었다 펴면 안 저장한 글 사라짐·빈 오른쪽은 지우기)
- 2026-11-28 21:42 S2 (review-pr206) 시작 (브랜치 task/S2-review-pr206)
- 2026-11-28 21:43 S2 (review-pr206) PR 올림 — PR #206(InboxSheet.append) 검토 글 docs/reviews/task-PR206-inbox-append.md. 합쳐도 됨(내 #183 검토 🟡 해소). 시험 3·34 통과, RAW 를 바꿔 보면 양쪽 시험 실패 확인
