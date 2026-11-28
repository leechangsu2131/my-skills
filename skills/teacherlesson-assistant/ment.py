"""💬 학생 대응 멘트 도우미 (T106) — 문장 파일 읽기, 교사가 덧붙인 대답, 누른 횟수. AI 를 부르지 않는다.

- 문장: `web/ment.json`(저장소, 교사 검토). 교사가 덧붙인 대답: 데이터 폴더 `ment_custom.json`(저장소 아님).
- 누른 횟수: 데이터 폴더 `ment_counts.json` — {"날짜": {"상황id": 횟수}}. 학생 이름·메모 글은 저장하지 않는다.
- 파일 경로는 모두 인자로 받는다(시험은 임시 폴더만 씀). 서버 연결은 assistant_server.py 의 /api/ment* 몇 줄.
"""
from __future__ import annotations

import json
import os
import pathlib
import threading
from datetime import date, timedelta

MAX_CUSTOM_PER_SITUATION = 10
MAX_TEXT = 200
_lock = threading.Lock()


def _read(path, default):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def _write(path, value) -> None:
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def check_shape(data) -> list[str]:
    """ment.json 모양 검사 — 고쳐야 할 점을 글로 돌려준다(없으면 빈 목록)."""
    problems: list[str] = []
    if not isinstance(data, dict) or not isinstance(data.get("situations"), list):
        return ["최상위에 situations 목록이 없어요."]
    seen = set()
    for index, item in enumerate(data["situations"], start=1):
        where = f"{index}번째 상황"
        if not isinstance(item, dict):
            problems.append(f"{where}: 객체가 아니에요.")
            continue
        sid = item.get("id")
        if not isinstance(sid, str) or not sid.strip():
            problems.append(f"{where}: id 가 비었어요.")
        elif sid in seen:
            problems.append(f"{where}: id '{sid}' 가 겹쳐요.")
        else:
            seen.add(sid)
        for key in ("label", "said"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                problems.append(f"{where}: {key} 가 비었어요.")
        answers = item.get("answers")
        if not isinstance(answers, list) or not 2 <= len(answers) <= 3 or not all(isinstance(a, str) and a.strip() for a in answers):
            problems.append(f"{where}: answers 는 빈 글자 없는 2~3개여야 해요.")
        principle = item.get("principle")
        if not isinstance(principle, dict) or not all(isinstance(principle.get(k), str) and principle[k].strip() for k in ("name", "note")):
            problems.append(f"{where}: principle 의 name·note 가 비었어요.")
    return problems


def load_situations(path) -> list[dict]:
    """상황 목록. 파일이 없거나 모양이 틀리면 빈 목록(화면은 '문장 파일을 못 읽었어요' 로 알림)."""
    data = _read(path, None)
    return data["situations"] if data is not None and not check_shape(data) else []


def read_custom(path) -> dict[str, list[str]]:
    """교사가 덧붙인 대답 {상황id: [글]} — 깨졌거나 모양이 다르면 그 부분만 버린다."""
    raw = _read(path, {})
    if not isinstance(raw, dict):
        return {}
    return {sid: [t for t in texts if isinstance(t, str) and t.strip()]
            for sid, texts in raw.items() if isinstance(sid, str) and isinstance(texts, list)}


def with_custom(situations: list[dict], custom: dict[str, list[str]]) -> list[dict]:
    """상황마다 `custom`(교사가 덧붙인 대답) 목록을 붙인다. 없는 상황의 custom 은 무시."""
    return [{**s, "custom": list(custom.get(s["id"], []))} for s in situations]


def _ids(situations) -> set[str]:
    return {s["id"] for s in situations}


def add_custom(path, situations: list[dict], situation: str, text) -> list[str]:
    text = str(text or "").strip()
    if situation not in _ids(situations):
        raise ValueError("없는 상황이에요.")
    if not text:
        raise ValueError("대답이 비어 있어요.")
    if len(text) > MAX_TEXT:
        raise ValueError(f"대답은 {MAX_TEXT}자까지 쓸 수 있어요.")
    with _lock:
        custom = read_custom(path)
        items = custom.setdefault(situation, [])
        if text in items:
            return items
        if len(items) >= MAX_CUSTOM_PER_SITUATION:
            raise ValueError(f"한 상황에 대답은 {MAX_CUSTOM_PER_SITUATION}개까지 둘 수 있어요. 안 쓰는 것을 지워 주세요.")
        items.append(text)
        _write(path, custom)
        return items


def remove_custom(path, situations: list[dict], situation: str, index) -> list[str]:
    if situation not in _ids(situations):
        raise ValueError("없는 상황이에요.")
    with _lock:
        custom = read_custom(path)
        items = custom.get(situation, [])
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(items):
            raise ValueError("지울 대답을 찾지 못했어요.")
        items.pop(index)
        if not items:
            custom.pop(situation, None)
        _write(path, custom)
        return items


def read_counts(path) -> dict[str, dict[str, int]]:
    raw = _read(path, {})
    if not isinstance(raw, dict):
        return {}
    clean: dict[str, dict[str, int]] = {}
    for day, row in raw.items():
        if isinstance(day, str) and isinstance(row, dict):
            clean[day] = {sid: n for sid, n in row.items()
                          if isinstance(sid, str) and isinstance(n, int) and not isinstance(n, bool) and n > 0}
    return clean


def press(path, situations: list[dict], situation: str, day: str | None = None) -> int:
    """상황 단추를 한 번 눌렀다고 세고, 그날 그 상황의 누적 횟수를 돌려준다."""
    if situation not in _ids(situations):
        raise ValueError("없는 상황이에요.")
    day = day or date.today().isoformat()
    date.fromisoformat(day)  # 날짜 모양 검사
    with _lock:
        counts = read_counts(path)
        row = counts.setdefault(day, {})
        row[situation] = row.get(situation, 0) + 1
        _write(path, counts)
        return row[situation]


def week_counts(counts: dict[str, dict[str, int]], monday: date) -> dict[str, int]:
    """월요일~일요일 합계 {상황id: 횟수}."""
    total: dict[str, int] = {}
    for offset in range(7):
        for sid, n in counts.get((monday + timedelta(days=offset)).isoformat(), {}).items():
            total[sid] = total.get(sid, 0) + n
    return total
