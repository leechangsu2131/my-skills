# 검토: task/S1-tests-prepare-lessons-helpers (PR #144)

- 검토: claude-web-은정 · 2026-11-27 (상시 일 S2)
- 대상 커밋: `8af7742` — main `0e7e1da` 에 합쳐 본 상태(충돌 없음)
- **판정: 🔴 그대로 합치면 자동 검사 `tests (repo-root)` 가 실패함. 아래 1번만 고치면 합치기를 권함**

## 1. `requests` 가 없는 곳에서 시험 6개 실패

- PR 자동 검사: `tests (repo-root)` 6 실패 · 436 통과, 모두 `ModuleNotFoundError: No module named 'requests'`.
- 원인: `test_lesson_pdf_from_supabase_writes_the_pdf`·`test_lesson_pdf_failures_return_false_without_writing`(4개)·`test_lesson_pdf_rejects_data_that_is_not_a_pdf` 가 진짜 `supabase_schedule` 을 불러오고, 그 파일이 `requests` 를 씀. repo-root 칸은 `pyyaml PyMuPDF` 만 설치함.
- 재현: `requests` 를 못 불러오게 막고 새 시험 파일만 돌리면 6 실패 · 41 통과.
- 고침 후보(임시 사본에서 확인: `requests` 를 막아도, 막지 않아도 47 통과) — 설치 목록(`check.yml`)을 안 바꿔도 됨:

```python
def fake_supabase(monkeypatch):
    """requests 없이도 돌게 supabase_schedule 을 가짜 모듈로 바꾼다."""
    fake = mock.Mock()
    monkeypatch.setitem(sys.modules, "supabase_schedule", fake)
    return fake
```

  세 시험의 `import supabase_schedule` 을 `supabase_schedule = fake_supabase(monkeypatch)` 로 바꿈.

## 확인한 것

- `requests` 가 있는 이 환경: 새 시험 47 통과.
- 소스를 한 곳씩 깨뜨려 보기 12곳(다시 묻기, PDF 판별, 글 300자 기준, 대기 시간, 연결 오류, `--redo` 보존, 중복 실행 거절, 종료 코드, 주의점, 오류 처리, 파일 닫기, 재시도 간격): 12곳 모두 시험이 실패함. PR 설명의 "24곳"은 전부 다시 해 보지 않음.
- 저장소 루트 `tests/conftest.py` 가 데이터 폴더·중앙 `.env` 를 임시 위치로 돌림 → 실제 데이터를 건드리지 않음(코드).
- PR #141(`parse_plan` 음수 분)과 함께 합쳐 `test_parse_plan`·`test_prepare_pipeline`·`test_prepare_lessons` 196 통과, 충돌 없음.
- `tools/check_privacy.py --stdin` 경고 0. 바뀐 파일은 새 시험 하나와 작업자 일지.

## 확인 못 한 것

- 이 환경에는 PyMuPDF 가 없어 저장소 루트 시험 전체는 못 돌림. 윈도우에서의 실행.
