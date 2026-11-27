# 수업 비서 건강 점검 갱신 (S5) — 2026-11-26 저녁

작업자 `claude-web-lee2131@hanmail` · 기준 `main` `8e02f7e` · 대상 `teacherlesson-assistant` 하나 · **고친 것은 없고 확인한 것만** 적었습니다.

같은 날 낮의 [health-2026-11-26.md](health-2026-11-26.md) 는 `sites/` 를 다루지 않았고, 그 뒤 T83(PR #78)이 합쳐졌습니다. 그래서 그 보고를 다시 쓰지 않고, **달라진 것만** 덧붙입니다.

## 한눈에

- 요구 파일(`requirements.txt`)만 설치한 새 가상환경에서 **`sites/` 시험이 이제 돕니다**: 32 통과 · 1 건너뜀(`test_music_helper` — selenium 이 요구 파일에 없음). selenium 을 더하면 37 통과, 건너뜀 없음.
- **그런데 자동 점검(CI)은 `sites/` 를 아직 안 돌립니다.** `.github/workflows/check.yml` 의 이 스킬 `target` 이 `tests test_assistant_server.py test_supabase_schedule.py` 뿐이라, `sites/` 시험이 다시 깨져도 빨간불이 안 켜집니다.
- CI 가 이미 도는 부분은 그대로 정상: `tests test_assistant_server.py test_supabase_schedule.py` **281 통과**. `python tools/build_catalog.py --check` 도 문제 없음.

## 확인한 방법과 한계

- 새 가상환경 두 개: ① `requirements.txt` + pytest 만, ② 거기에 selenium 추가. 홈 폴더·저장소 폴더에 무엇을 쓰는지는 이번에 따로 보지 않았습니다.
- **Python 3.13.18** 에서 돌렸습니다(CI 는 3.12). 버전 차이가 결과에 영향이 있는지는 확인하지 않았습니다.
- 실제 사이트(음악 두클래스·사회 아이스크림)나 크롬은 열지 않았습니다. `sites/` 시험은 글자·경로만 비교하는 것들입니다.

## 낮 보고와 달라진 점

| 항목 | 낮 | 지금 |
|---|---|---|
| `teacherlesson-assistant` CI 대상 시험 | 130 + 72(폴더 밖 2파일, CI 가 안 돌던 때) | 281 통과 (CI 가 `tests` 와 폴더 밖 2파일을 함께 돎) |
| `sites/` 시험 | 보고에 없음(`pytest sites` 는 모으기 실패 3 + 실패 3) | 32 통과 · 1 건너뜀 |
| `assistant_server.py` 첫머리 설명 | 옛 진도 서버 기준(ISSUE-023) | 고침(T86, #80) |

## 제안 (고치지 않음 — 공용 파일이라 교사 판단)

1. `check.yml` 의 `teacherlesson-assistant` `target` 을 `tests sites test_assistant_server.py test_supabase_schedule.py` 로. 이때 `test_music_helper` 는 CI 에서 **건너뜀**으로 나옵니다(selenium 이 요구 파일에 없어서). 돌리려면 `requirements.txt` 에 selenium 을 넣을지는 교사 결정(교사 PC 는 이미 설치).
2. `sites/music_douclass/douclass_probe.py`·`scan_music_pdf_header.py`(T83 에서 이름만 바꿈)에는 `C:\Users\user\...` 하드코딩 경로가 남아 있습니다. 쓸 일이 없으면 지울지는 교사 확인.

## 남은 확인

- 이 보고는 `sites/` 만 새로 쟀습니다. 다른 스킬은 낮 보고 그대로이고 다시 돌리지 않았습니다.
