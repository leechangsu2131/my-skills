# 검토: `task/T95-douclass-cli-args` (PR #101) — claude-web-162, 2026-11-27

결론: **합쳐도 됩니다.** 꼭 고쳐야 할 문제는 못 찾았습니다. 이 브랜치는 고치지 않았습니다.

## 직접 돌려 본 것 (브랜치를 따로 받아서)

- `python -m unittest test_douclass_scripts` (sites/music_douclass): 13개 통과
- `python douclass_probe.py --help`: 도움말 나오고 끝남(selenium 없어도)
- `python scan_music_pdf_header.py` (경로 없음): 안내 후 종료 코드 2
- `python scan_music_pdf_header.py nofile.pdf`: "파일을 찾을 수 없어요" 후 종료 코드 2
- `sites` 시험 전체: 43 통과·2 건너뜀 / `build_catalog.py --check`: 통과 / `check_privacy.py`: 통과
- `skills/teacherlesson-assistant` 안 `.py` 에서 `C:\Users\…` 모양 검색: 0건

## 🔴 합치기 전에 꼭

없음.

## 🟡 나중에 (이번에 안 고쳐도 됨)

1. **`--target ""` (빈 말)**: 기호·띄어쓰기를 뺀 뒤 빈 글이 되어 모든 쪽이 "맞음"으로 나옵니다(`scan_music_pdf_header.py` 의 `target in norm_text`). 빈 값이면 안내 후 종료 코드 2 로 막으면 좋습니다.
2. **`douclass_probe.py` 의 실제 동작은 시험이 없음**: 시험은 `--help`·selenium 없음·붙기 실패(종료 코드 1)까지만 봅니다. 차시·PPT 단추를 찾는 본문은 예전 그대로이고 실제 Chrome 에서 돌려 보지 않았습니다 — **확인 필요**(교사 PC).
3. 작은 것: `scan()` 이 쪽마다 `get_text()` 를 두 번 부릅니다(쪽 수가 많은 PDF 에서만 느림). 머리말 판정이 앞 200자인 점은 예전과 같습니다.
4. 이 환경에는 PyMuPDF 가 없어 `tests/test_notebook_notes.py` 를 불러오지 못합니다(이 PR 과 무관, T93 과 관련). `scan_music_pdf_header.py` 시험은 가짜 fitz 라 영향 없음.

## 범위·안전

- 고친 파일은 `sites/music_douclass/` 안 3개와 작성자 일지뿐. 개인정보·비밀값·저작물 없음.
- 예전 기본값(포트 9222, `1~2차시`, `길고짧은음높고낮은음`)을 그대로 두어 기존 사용법이 안 깨집니다.
