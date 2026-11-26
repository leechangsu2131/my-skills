# util-storagemap 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다. 양식은 맨 아래 주석 참고.

## 🔵 진행 중

_없음_

## 📌 백로그

### ISSUE-001: 물건 수량이 빈칸·null 로 오면 기본값 1 이 아니라 0 이 된다 (2026-11-25)
- **상태**: 📌 백로그 (확인 필요 — 의도인지 모름)
- **증상**: `toNumber('', 1)`·`toNumber(null, 1)` 이 `1` 이 아니라 `0`. 그래서 `NORMALIZE.items({ quantity: '' }).quantity` 도 `0`. (`undefined`·숫자 아닌 글은 기본값 1 이 맞게 나옴.)
- **원인**: `Number('')` 과 `Number(null)` 이 `0` 이라 "숫자가 아님" 검사(`Number.isFinite`)를 통과한다.
- **해결/조치**: (미적용) 수량 빈칸을 0개로 볼지 1개로 볼지 교사 확인 뒤, 1 이 맞다면 `toNumber` 에서 빈 문자열·null 을 기본값으로 처리. 시험은 현재 동작을 그대로 적은 시험 1개 + 바라는 동작을 적은 `todo` 시험 1개로 남겨 둠.
- **관련 파일**: `server.js`(`toNumber`, `NORMALIZE.items`), `tests/server_helpers.test.js`

## 🟢 해결됨

### ISSUE-003: `npm test` 가 자리표시 명령이라 시험이 안 돈다 (2026-11-25, 2026-11-26 해결)
- **상태**: 🟢 해결됨 (T69)
- **증상**: `package.json` 의 `test` 가 `echo "Error: no test specified" && exit 1` 이라 `npm test` 가 늘 실패했다.
- **원인**: 시험이 없던 때의 기본값이 그대로 남아 있었다. T07 로 `tests/server_helpers.test.js` 가 생겼다.
- **해결**: `package.json` 의 `test` 를 `node --test tests/server_helpers.test.js` 로 바꿨다. 이제 `skills/util-storagemap` 폴더에서 `npm test` 로 돈다(Node 22 는 폴더 이름만 주면 못 찾아서 파일을 직접 적음).
- **관련 파일**: `package.json`, `tests/server_helpers.test.js`

### ISSUE-002: 이름표 배열 안의 `null`·`undefined` 가 'null'·'undefined' 이름표가 된다 (2026-11-25, 2026-11-26 해결)
- **상태**: 🟢 해결됨 (T69)
- **증상**: `parseTags(['a', null, undefined])` → `['a', 'null', 'undefined']` 였다.
- **원인**: 배열을 `map(String)` 으로 글자로 바꾼 뒤에 `filter(Boolean)` 을 해서, 글자가 된 `null` 이 걸러지지 않았다.
- **해결**: `parseTags` 안에서 글자로 바꾸기 전에 `null`·`undefined` 를 거른다(배열 값과 JSON 배열 글 둘 다). 글자 `'null'` 은 그대로 둔다. 시험의 `todo` 표시를 지우고 JSON 배열·글자 `'null'` 시험을 더함. 소스를 일부러 틀리게 한 변이 2가지를 모두 시험이 잡음
- **관련 파일**: `server.js`(`parseTags`), `tests/server_helpers.test.js`

<!--
항목 양식 (복사해서 사용)

### ISSUE-001: 한 줄 제목 (YYYY-MM-DD)
- **상태**: 🔵 진행 중 | 📌 백로그 | 🟢 해결 (YYYY-MM-DD)
- **증상**: 무엇이 어떻게 안 됐나 (오류 메시지 그대로)
- **원인**: 확인된 원인
- **해결/조치**: 무엇을 바꿨나, 재발 방지
- **관련 파일**: `script.py`, 커밋 해시
-->
