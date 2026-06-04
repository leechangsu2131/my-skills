# AGENTS.md

이 저장소의 표준 에이전트 지침은 `CLAUDE.md`입니다. Codex, Claude, Gemini, Cursor, Windsurf 등 어떤 IDE/에이전트에서 이어받더라도 먼저 `CLAUDE.md`, `PLANS.md`, `TROUBLESHOOTING.md`를 읽고 작업하세요.

핵심 요약:

- 한국어로 사용자와 협업합니다.
- 이 도구는 투자 권유가 아니라 주가에 담긴 가정과 계산 과정을 보여주는 가치분석 도구입니다.
- 현재 중심 사례는 삼성전기 `009150`입니다.
- 숫자에는 출처, 원문 계정명, 단위 변환, 계산식이 따라야 합니다.
- Streamlit 앱은 `python -m streamlit run valuation_app/dashboard.py --server.port 8501`로 실행합니다.
- 변경 후 `pytest`와 브라우저 확인을 합니다.
- `.superpowers/`는 명시 요청 전에는 커밋하지 않습니다.

