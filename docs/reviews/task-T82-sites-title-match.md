# 검토: `task/T82-sites-title-match` — 고친 뒤 합침 (2026-11-26 저녁, 교사 PC 오케스트레이터)

`title_match.py` 순수 함수 자체는 괜찮습니다(1·11차시는 번호로 갈림, 빈 문자열은 안 맞음, 범위·개인정보 문제 없음, teacherlesson-assistant 시험 332 통과).
문제는 **붙이는 방식**입니다. 음악·사회 도우미는 목록을 위에서부터 훑다가 **처음 맞는 것**을 고르는데, 그 판정에 '포함'·'비슷함'을 섞어서 원래 정확히 찾던 것보다 **앞에 있는 비슷한 이름**을 먼저 고릅니다.

## 🔴 합치기 전에 꼭

1. **차시 이름이 비슷하면 앞 차시를 고름**
   - 위치: `sites/social_class/social_class_helper.py` 722-729, `sites/music_douclass/music_helper.py` 534-541 (`lesson_matches`). 이 판정을 쓰는 곳: music `click_ppt_for_lesson`·`find_lesson_position`·`find_lesson_position_from_candidates`·`find_adjacent_lesson`, social `open_resource_for_lesson`
   - 재현: 목록 `["[3차시] 위치 알아보기", "[4차시] 위치 찾아보기"]` 에서 `"위치 찾아보기"` → 예전 4차시, 지금 **3차시**. `["[5차시] …장소를 표현해 볼까요", "[6차시] …장소를 조사해 볼까요"]` 에서 `"…장소를 조사해 볼까요"` → 예전 6차시, 지금 **5차시**
   - 결과: 엉뚱한 PPT. 음악은 틀린 `exact_title` 이 저장돼 PDF 추출·최근 기록·이전/다음 차시까지 어긋남
   - 고치는 방향: `lesson_matches` 에는 느슨한 판정을 넣지 않는다. 부르는 곳에서 **두 번 훑기** — ① 기존 엄격한 규칙으로 전체를 보고 ② 하나도 없을 때만 `title_match.best_match`(이미 있는데 안 쓰임)로 가장 높은 후보 하나. 사이트 여는 부분은 그대로, 찾는 반복문만 바뀜
2. **단원 이름이 정확히 맞아도 앞 단원이 함께 걸림**
   - 위치: `social_class_helper.py` 698, `music_helper.py` 508 (`unit_matches` 의 새 마지막 줄). 근본 원인 `title_match.py` 68 — '포함'을 양쪽 방향으로 봄
   - 재현: `"우리 지역의 모습과 변화"` → 예전 `"2. 우리 지역의 모습과 변화"` 만, 지금 `"1. 우리 지역의 모습"` 도 맞음. `ensure_unit_loaded` 가 처음 맞는 1단원을 펼치고 끝남
   - 고치는 방향: 1번과 같이 엄격 → 없을 때만 최고 후보 하나. 또는 단원은 '같음'만, 아니면 진도표 이름이 더 짧은 방향일 때만 '포함'
3. **시험이 위 경우를 덮지 않음** (`sites/social_class/test_social_title_match.py`, `sites/music_douclass/test_music_title_match.py`)
   - 위 재현 사례(3·4차시, 5·6차시, 1·2단원)를 "헷갈리는 후보가 앞에 있는 목록에서 무엇을 고르는가" 시험으로 추가

## 🟡 나중에 (이번에 안 고쳐도 됨)

- `title_match.py` 99-108: 사이트 꼬리표에 번호가 없으면(`[정리] 위치 알아보기`) `"[3차시] 위치 알아보기"` 로 찾아도 맞음. 찾는 쪽에만 번호가 있을 때 이름 비교를 할지 검토
- `title_match.py` 32: `"1-2. 만나요"` → `"2만나요"` 로 앞 번호 일부가 남음
- 음악 시험은 selenium 이 없는 곳에서 건너뜀 — 작업자 환경(sites 62 통과)과 다를 수 있음
- 고친 뒤에야 `ISSUES.md` 의 ISSUE-005 셋째 '완료' 표시가 맞음
