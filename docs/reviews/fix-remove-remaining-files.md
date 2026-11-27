# 검토: fix/remove-remaining-files (PR #149)

- 검토: claude-web-yi2131@naver · 2026-11-27 (상시 일 S2)
- 참고: 이 검토를 올리기 전에 PR 이 이미 합쳐졌음(2026-11-28 확인). 아래 🟡 은 합쳐진 뒤에 남은 확인거리
- 대상: PR 머리 — main 기준. 이 브랜치는 고치지 않았음
- **판정: 🟢 합쳐도 됨 (교사 지시 작업) — 단, 아래 🟡 의 "기록에는 남는다"는 교사가 알고 있어야 함**

## 확인한 것

- 지운 것: 영수증 사진 1(`admin-class-buy/data/KakaoTalk_…jpg`), 빈 시험지 그림 3(`classmanage-exam-graderV2/data/template/blank_p1~3.jpg`), 책 본문 `util-pdf-translator/scripts/output/chapter_01.txt`. 일지 줄에 "교사 지시"라고 적혀 있고 ISSUES 에도 "교사 결정 2026-11-27" 로 남김.
- `.gitignore` 에 같은 위치를 더해 다시 올라오지 않게 함.
- 지운 파일을 코드·시험이 읽는지 확인:
  - `util-pdf-translator`: 시험이 `chapter_01.txt` 를 임시 폴더(`tmp_path`)에 만들어 쓰므로 영향 없음 → 이 스킬 시험 103 통과(main 과 같음). `SKILL.md` 의 폴더 그림은 예시 글이라 그대로 둬도 됨.
  - `classmanage-exam-graderV2`: 실행 코드는 `data/template/blank.png`·프로젝트별 `template_dir` 를 쓰고 지운 `blank_p*.jpg` 이름은 안 씀. `scratch_rewrite.py`(작업 흔적 파일)의 화면 조각에만 `blank_p1.jpg` 이름이 남음 — 실행에는 영향 없어 보임(추정).
- 저장소 `tests` 395 통과, `build_catalog.py --check` 오류 0(경고 1개는 이번 PR 과 무관한 `util-school-print/ParameterSetObject.pdf`).

## 🟡 알아 둘 것

1. **git 기록(히스토리)에는 파일이 그대로 남음** — 저장소가 공개라서 옛 커밋을 열면 영수증 사진 등을 볼 수 있음. PR 글도 같은 말을 적었음. 영수증에 개인정보(카드 번호 등)가 있었다면 기록 정리(강제 푸시)가 필요한지 교사가 정해야 함. 이 검토에서는 사진 내용을 열어 보지 않았음(확인 필요).
2. `admin-class-buy/data/` 에는 영수증 정리 `receipt_paris_baguette_20260618.json` 과 증빙자료 `.docx` 가 아직 추적 중. `.gitignore` 는 `*.jpg`·`*.png` 만 막음. 내용은 열어 보지 않았고 JSON 최상위 칸에 `teacher` 가 있음(교직원 이름은 허용 범위) — 카드 번호·전화번호가 없는지는 한 번 확인 필요.
3. `classmanage-exam-graderV2/tests/test_grading_student_page.py` 가 불러오는 단계에서 오류 — **main 에서도 똑같음**(이 PR 과 무관, 묶음 밖 스킬이라 기록만).
4. 브랜치 이름이 `fix/…`(작업자 규칙은 `task/…`). 교사 지시 작업이라 문제없음.

## 확인 못 한 것

- 사진·docx 의 실제 내용, 기록 정리 필요 여부.
