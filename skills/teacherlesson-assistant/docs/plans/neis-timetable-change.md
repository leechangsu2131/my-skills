# 설계: 나이스 시간표 변경을 교시 탭에 '변경됨'으로 보이기 (T84, ISSUE-008 둘째)

2026-11-26 · 설계만, 코드는 바꾸지 않음. 코드에서 확인한 것과 **확인 필요**를 나눠 적는다.

## 0. 구현 전에 먼저 볼 것

- **확인 필요(가장 중요)**: 보결·시간표 교체를 했을 때 NEIS `주간학습안내작성` 의 `dsWikLrn` 과목이 실제로 바뀌는지. 담임이 주간학습안내를 고치지 않으면 안 바뀔 수 있다. 바뀌지 않으면 아래 방법으로는 알 수 없으니 구현하지 않는다.
- 확인 방법: 시간표가 바뀐 주를 NEIS 에서 조회 → 확장 뷰어에서 그 날 그 교시의 과목을 본다.

## 1. 지금 자료 모양 (코드에서 확인)

- 읽기: `teacherlesson-from-neis/extension/neis-reader.js` `readPayload()`
- 저장: `extension/background.js` `normalizePayload()` → `storePayload()`, Chrome `storage.local` 키 `teacherlessonNeisCache`
- 모양: `{records, updatedAt, rangeStart, rangeEnd, source, fetchedWeeks, completeMonths}`
- 레코드: `date`(YYYY-MM-DD), `period`(숫자 글자), `subject`, `unit`, `content`, `lesson_number`, `total_lessons`, `textbook_page`, `additional_page`
- **보결·교체를 알려 주는 칸은 없다.** → 진도표 과목과 다른지 비교해서만 알 수 있다.
- 과목이 빈 칸은 `normalizePayload()` 에서 버려진다 → '수업이 없어짐'과 '아직 안 씀'을 구별할 수 없다.
- `fetchedWeeks["월|금"]` 에 그 주를 읽은 시각(ms)이 있다. 같은 주는 12시간 캐시라 방금 바뀐 것은 늦게 보인다.
- 수업 비서 쪽: `assistant_server.py` `state()` 의 `lessons[]` 에 `period`(정수 또는 None), `subject`.

## 2. 넘기는 방법

| 방법 | 장점 | 단점 |
|---|---|---|
| **A. 확장 → 수업 비서에 POST (권장)** | 단추 한 번 | 서버가 확장 요청을 받도록 예외가 필요 |
| B. 확장에서 JSON 내려받기 → 서버가 파일 읽기 | 서버 보안 규칙 그대로 | 매번 파일을 옮겨야 해서 안 쓰게 되기 쉬움 |

옛 `teacherlesson-from-neis/server.py`(5101, `/api/import`)는 지금 확장이 일상에서 쓰지 않으므로 중계 서버로 되살리지 않는다.

### A 의 모양

- 확장: 팝업에 **수업 비서로 보내기** 단추. `background.js` 에 `sendWeekToAssistant()`. 보내는 칸은 `date`, `period`, `subject` 와 `fetched_at` 뿐(학생 현황 키 `teacherlessonNeisStudentStatus` 는 읽지 않음).
- `manifest.json` `host_permissions` 에 `http://127.0.0.1:5180/*` 추가. 버전 올림.
- 서버: `POST /api/neis-week` → `save_neis_week()` → 데이터 폴더 `neis_week.json`. 보낸 날짜 범위만 갈아 끼움.
  - 본문: `{"range_start","range_end","fetched_at","records":[{"date","period","subject"}]}`
- 보안: 지금 `do_POST` 는 `_trusted()` 가 `chrome-extension://` Origin 을 403 으로 막는다. **`_trusted()` 는 넓히지 않는다.** `/api/neis-week` 한 경로만 따로 검사한다.
  - `Host` 검사는 그대로
  - `Origin` 이 config `neis_extension_id` 로 만든 `chrome-extension://<id>` 와 **정확히 같을 때만**. 설정이 비어 있으면 거절
  - 본문 크기·레코드 수 제한(1200), 날짜·교시 형식 검사
- **확인 필요**: 압축해제 확장의 ID 는 PC·폴더마다 다를 수 있음. `host_permissions` 가 있을 때 사전 요청(OPTIONS) 없이 가는지, 실제 `Origin` 값. 사전 요청이 오면 `do_OPTIONS` 를 이 경로에만 추가.
- 5180 은 config `port` 로 바꿀 수 있다. 바꾼 PC 는 manifest 와 맞지 않는다.

## 3. 비교 함수

새 파일 `neis_timetable.py` (파일·네트워크를 쓰지 않는 순수 함수):

```python
def subject_key(name: str, aliases: dict[str, str]) -> str      # 공백 제거 후 별칭 적용
def compare_timetable(lessons, records, day: str, aliases) -> dict[int, dict]
# {교시: {"status": "same"|"changed"|"neis_only"|"progress_only", "neis": [과목], "progress": [과목]}}
```

- 그 날 레코드가 하나도 없으면 `{}` (모르는 것을 '변경됨'으로 보이지 않음)
- 한 교시에 과목이 여럿이면 하나라도 같으면 `same`
- `period` 가 None 인 진도표 수업은 비교하지 않음
- `fetch_schedule()` 이 'Supabase 연결 오류'·'기본 시간표'를 돌려준 날은 비교하지 않음
- 별칭은 config `neis_subject_aliases`. **확인 필요**: NEIS 과목 이름과 진도표 이름이 실제로 어떻게 다른지(창체·통합교과 등)

## 4. 화면

- `state()`: `lesson["neis"]` = 그 교시 결과, 최상위 `neis` = `{"fetched_at", "only": [진도표에 없는 교시·과목]}`
- `web/index.html` `renderTabs()`: `changed` 면 과목 아래 `⚠ 변경됨`, `progress_only` 면 `? 나이스에 없음`
- 고른 교시 화면: "나이스에는 3교시가 **체육**이에요 (11/26 08:10에 읽음)". 진도표는 **자동으로 고치지 않는다** — 기존 진도 조정 단추를 교사가 누른다.
- `neis_only` 는 새 탭을 만들지 않고 탭 위에 한 줄로 알림
- 읽은 지 하루가 지났으면 "오래된 자료" 표시

## 5. 순서와 시험

1. 0번 확인 (교사 PC)
2. `neis_timetable.py` + 시험: 같음·바뀜·한쪽만·자료 없음·별칭·교시 None
3. `POST /api/neis-week` + 시험: 다른 Origin 403, 설정 없음 403, 다른 경로는 여전히 확장 Origin 403
4. 화면 표시
5. 확장 단추 → 교사 PC 에서 실제 확인

학생 정보는 이 흐름에 넣지 않는다. 시험은 가짜 레코드만 쓴다.
