# ag-1 일지

- 2026-11-26 13:46 T89 시작 (브랜치 task/T89-classroom-tools-bundle)
- 2026-11-26 13:51 T89 PR �ø� ? web/tools.js ���� �Լ�(Ÿ�̸ӡ���ǥ�� �̱⡤����), index.html ���� ���� ĭ, assistant_server.py /tools.js ���, tests/test_tools.js 33�� ���. Ȯ��: node tests/test_tools.js ��� ���, pytest test_assistant_server.py 33�� ���
- 2026-11-26 13:52 T53 시작 (브랜치 task/T53-manual-checklist)
- 2026-11-26 13:54 T53 PR �ø� ? docs/checklist-manual.md �ۼ� (12�� ����, �׸� '������ ������ �� ��' üũ����Ʈ). Ȯ��: ����� ���� ���� ���� üũ
- 2026-11-26 13:55 T72 시작 (브랜치 task/T72-compress-stages)
- 2026-11-26 14:15 그만둠 — T89·T53 완료 후 T72(뒤 단계 한 번에 줄이는 단추) 브랜치에서 index.html paceInfo/flag 부분 파악까지 진행. 다음에는 web/tools.js 에 남은 단계 분 비례 감소 순수 함수(꼭 해야 함 keep 단계 덜 줄임)와 tests/test_tools.js 시험을 추가하고 web/index.html 에 단추 연결하면 됨
- 2026-11-28 21:34 chrome-profiles 시작 (브랜치 task/chrome-profiles-pause-close-url) — 일시 중지 일괄 닫기, 트리 우클릭 닫기, 사이트 이동 기본값
- 2026-11-28 21:40 chrome-profiles 합칠 준비 — 일시 중지 일괄 닫기 버튼(pause_close_button), 트리 다중/단일 우클릭 창 닫기 메뉴, 사이트 이동 기본값(https://claude.ai/projects) 구현 및 SKILL.md·ISSUES.md 반영. 확인: py_compile 통과, pytest 32개 통과(사본 config/pauses + close_window·QMenu 대역)
