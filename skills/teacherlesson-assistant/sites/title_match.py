"""단원·차시 이름이 조금 달라도 같은 것으로 찾아 주는 순수 함수 (T82, ISSUE-005 셋째).

진도표의 이름과 출판사 사이트의 이름은 같은 차시인데도 띄어쓰기·쉼표·번호 표기가 조금씩 다르다.
  진도표: "만나요 음악시간"        사이트: "1. 만나요, 음악 시간"
  진도표: "[3차시] 위치 알아보기"  사이트: "3~4차시 위치 알아보기(사23~27p)"
이 파일은 사이트를 열거나 화면을 만지지 않고 글자만 비교한다(네트워크·selenium 없음).
음악(music_douclass/music_helper.py)·사회(social_class/social_class_helper.py) 도우미가 함께 쓴다.

비교 순서: 이름 정리 → 같음(same) → 포함(contains) → 비슷함(similar). 모두 아니면 None.

쓰는 법(중요): 느슨한 판정을 '처음 맞는 것을 고르는 반복문' 안에 넣지 않는다 — 비슷한 앞 차시가 정확한 뒤 차시보다 먼저 걸린다.
대신 찾기 직전에 resolve_search_texts·resolve_query 를 한 번 부른다: 기존 엄격한 규칙으로 맞는 것이 하나라도 있으면 그대로 두고,
하나도 없을 때만 가장 닮은 하나의 사이트 이름으로 바꿔 준다. 반복문과 엄격한 규칙은 손대지 않는다.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Callable, Optional, Sequence, Tuple, TypeVar

T = TypeVar("T")

SAME = "same"
CONTAINS = "contains"
SIMILAR = "similar"
_RANK = {SAME: 3, CONTAINS: 2, SIMILAR: 1}

# 이름에서 글자를 이만큼(정리한 뒤) 이상 가진 쪽만 '포함'으로 본다. "음악" 같은 짧은 말이 아무 데나 붙는 것을 막는다.
MIN_CONTAINS_LEN = 3
# '비슷함'으로 볼 최소 점수(0~1). 정리한 글자를 한 글자씩 맞춰 본 비율이다.
SIMILAR_THRESHOLD = 0.8

_SQUARE_LABEL = re.compile(r"[\[［【][^\]］】]*[\]］】]")  # [3차시] 같은 꼬리표는 통째로 뺀다
_PAREN = re.compile(r"[\(（]([^\)）]*)[\)）]")             # (사23~27p) 같은 쪽 표시는 빼고, 글자만 있으면 괄호만 뺀다
_LESSON_RANGE = re.compile(r"\d+(?:\s*[~\-～]\s*\d+)?\s*차시")  # 3차시, 3~4차시
_LEADING_NUMBER = re.compile(r"^\s*(?:제\s*)?\d+(?:\s*[~\-～]\s*\d+)?\s*(?:단원|차시|[.)\-:])\s*")  # 1. / 1단원 / 제1단원 / 1) / 1-2.
_NOT_WORD = re.compile(r"[^0-9a-z가-힣]")


def _paren_inner(match: "re.Match[str]") -> str:
    inner = match.group(1)
    return " " if re.search(r"\d", inner) else f" {inner} "


def normalize_title(text: Optional[str]) -> str:
    """이름을 비교하기 좋게 정리한다: 꼬리표·쪽 표시·앞 번호·'차시'·띄어쓰기·기호를 없애고 소문자로."""
    value = str(text or "")
    value = _SQUARE_LABEL.sub(" ", value)
    value = _PAREN.sub(_paren_inner, value)
    value = _LESSON_RANGE.sub(" ", value)
    value = _LEADING_NUMBER.sub("", value.strip())
    value = value.replace("차시", " ")
    return _NOT_WORD.sub("", value.lower())


def similarity(a: Optional[str], b: Optional[str]) -> float:
    """정리한 두 이름이 얼마나 닮았는지(0~1)."""
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def match_level(a: Optional[str], b: Optional[str], threshold: float = SIMILAR_THRESHOLD) -> Optional[str]:
    """'same' · 'contains' · 'similar' 중 가장 센 것, 아니면 None. 정리하고 남은 글자가 없으면 None."""
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return None
    if na == nb:
        return SAME
    short, long_ = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(short) >= MIN_CONTAINS_LEN and short in long_:
        return CONTAINS
    if SequenceMatcher(None, na, nb).ratio() >= threshold:
        return SIMILAR
    return None


def titles_match(a: Optional[str], b: Optional[str], threshold: float = SIMILAR_THRESHOLD) -> bool:
    return match_level(a, b, threshold) is not None


def best_match(
    query: Optional[str],
    candidates: Sequence[T],
    key: Optional[Callable[[T], str]] = None,
    threshold: float = SIMILAR_THRESHOLD,
) -> Optional[Tuple[T, str]]:
    """후보 중 query 와 가장 닮은 하나와 그 수준을 돌려준다. 같음 > 포함 > 비슷함, 같은 수준이면 점수가 높은 것, 그래도 같으면 앞의 것. 없으면 None."""
    best: Optional[Tuple[T, str]] = None
    best_key: Tuple[int, float] = (0, 0.0)
    for item in candidates:
        label = key(item) if key else str(item)
        level = match_level(query, label, threshold)
        if level is None:
            continue
        rank = (_RANK[level], similarity(query, label))
        if rank > best_key:  # 같은 점수면 먼저 나온 것을 지킨다
            best, best_key = (item, level), rank
    return best


def resolve_references(
    references: Sequence[str],
    titles: Sequence[str],
    strict: Callable[[str, str], bool],
    guard_numbers: bool = False,
) -> list:
    """찾는 이름(references)을 사이트의 이름으로 바로잡는다. '엄격 → 없을 때만 가장 비슷한 하나'.

    ① 기존 엄격한 규칙(strict(제목, 찾는 이름))으로 맞는 것이 하나라도 있으면 **그대로** 돌려준다
       → 정확히 찾던 것은 예전과 똑같이 찾고, 비슷한 다른 이름이 앞에 있어도 끌려가지 않는다.
    ② 하나도 없을 때만 같음 > 포함 > 비슷함 순으로 가장 닮은 제목 **하나**의 이름으로 바꿔 돌려준다.
       찾는 이름이 여러 개여도 전체에서 가장 닮은 하나만 고른다. 그 이름은 사이트 이름 그대로라 엄격한 규칙에도 맞는다.
    ③ 그것도 없으면 그대로 돌려준다(못 찾으면 못 찾았다고 해야 한다).
    guard_numbers=True 면 양쪽에 차시 번호가 있는 쌍은 번호가 이미 '아니다'라고 한 것이므로 이름으로 되살리지 않는다.
    """
    refs = list(references)
    pool = [t for t in titles if t]
    if not refs or not pool:
        return refs
    if any(strict(t, r) for r in refs for t in pool):
        return refs
    best: Optional[str] = None
    best_key: Tuple[int, float] = (0, 0.0)
    for r in refs:
        for t in pool:
            if guard_numbers and numbers_can_decide(t, r):
                continue
            level = match_level(r, t)
            if level is None:
                continue
            key = (_RANK[level], similarity(r, t))
            if key > best_key:  # 같은 점수면 먼저 나온 것을 지킨다
                best, best_key = t, key
    return [best] if best is not None else refs


def resolve_query(
    query: str,
    titles: Sequence[str],
    strict: Callable[[str, str], bool],
    guard_numbers: bool = False,
) -> str:
    """resolve_references 의 찾는 이름이 하나일 때."""
    return resolve_references([query], titles, strict, guard_numbers)[0]


def resolve_search_texts(
    lessons: Sequence[dict],
    unit_text: str,
    lesson_texts: Sequence[str],
    unit_matches: Callable[[str, str], bool],
    lesson_matches: Callable[[str, str], bool],
) -> Tuple[str, list]:
    """차시 목록(각 항목에 'unit_title'·'title')에서 단원 이름과 차시 이름들을 사이트 이름으로 바로잡는다.
    단원을 먼저 정하고, 그 단원 안의 차시들만 보고 차시를 정한다. 반복문은 그대로 두고 찾기 직전에 한 번만 부른다."""
    unit_titles = []
    for item in lessons:
        name = (item.get("unit_title") or "").strip()
        if name and name not in unit_titles:
            unit_titles.append(name)
    unit_text = resolve_query(unit_text, unit_titles, unit_matches)
    titles = [item.get("title") or "" for item in lessons if unit_matches(item.get("unit_title") or "", unit_text)]
    return unit_text, resolve_references(lesson_texts, titles, lesson_matches, guard_numbers=True)


def lesson_label_numbers(text: Optional[str]) -> list:
    """차시 번호 글자들. '[3~4차시] 이름' 처럼 꼬리표가 있으면 그 안의 숫자만, 없으면 글 전체의 숫자."""
    value = str(text or "")
    label = re.search(r"\[(.*?)\]", value)
    return re.findall(r"\d+", label.group(1) if label else value)


def numbers_can_decide(title_text: Optional[str], lesson_text: Optional[str]) -> bool:
    """두 차시 이름 모두에 차시 번호가 있으면 번호로 가른다(같은 이름이 다른 차시에 있어도 섞이지 않게)."""
    return bool(lesson_label_numbers(title_text)) and bool(lesson_label_numbers(lesson_text))
