"""일정 문구가 내게 해당하는지 '대상' 값으로 분류한다. 규칙은 config.toml로 바꿀 수 있다."""
from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

OTHER = "타학년·유치원"  # 아침 메시지에서 빠지는 값 (일정DB에는 남는다)


@dataclass(frozen=True)
class ClassifyConfig:
    my_grade: int = 3
    sports_keywords: tuple[str, ...] = (
        "체육", "대회", "육상", "축구", "양궁", "출전", "운동회", "체력",
        "스포츠클럽", "줄넘기", "수영", "paps", "소년체전",
    )
    exclude_keywords: tuple[str, ...] = ("유치원", "사서교사", "돌봄", "저학년", "고학년")
    mine_keywords: tuple[str, ...] = ("중학년",)


def load_config(path: str | os.PathLike | None = None) -> ClassifyConfig:
    from .envload import resolve_path  # 실행한 폴더 -> .env 폴더(OneDrive) -> 저장소 폴더 순서로 찾는다

    p = resolve_path(str(path or os.environ.get("TODO_CONFIG", "config.toml")))
    if not p.is_file():
        return ClassifyConfig()
    data = tomllib.loads(p.read_text(encoding="utf-8")).get("classify", {})
    allowed = {f.name for f in fields(ClassifyConfig)}
    kwargs = {k: (tuple(v) if isinstance(v, list) else v) for k, v in data.items() if k in allowed}
    return ClassifyConfig(**kwargs)


_RANGE = re.compile(r"([1-6])\s*[~∼\-–]\s*([1-6])\s*학년")
_GRADE = re.compile(r"([1-6])\s*학년")
# 3-2 같은 학급 표기. '4-5교시', '3-4월' 같은 것은 학급이 아니므로 제외한다.
_CLASS = re.compile(r"(?<!\d)([1-6])\s*-\s*([1-9])(?!\d|\s*(?:교시|시|명|월|일|차|회|주|개))")


def grades_mentioned(text: str) -> set[int]:
    g: set[int] = set()
    for a, b in _RANGE.findall(text):
        g.update(range(int(a), int(b) + 1))
    g.update(int(n) for n in _GRADE.findall(text))
    g.update(int(n) for n, _ in _CLASS.findall(text))
    return g


def classify(text: str, cfg: ClassifyConfig | None = None) -> str:
    """'3학년' / '체육' / '타학년·유치원' / '전체' 중 하나."""
    cfg = cfg or ClassifyConfig()
    low = text.lower()
    grades = grades_mentioned(text)
    if cfg.my_grade in grades or any(k in text for k in cfg.mine_keywords):
        return f"{cfg.my_grade}학년"
    if any(k.lower() in low for k in cfg.sports_keywords):
        return "체육"  # 체육업무 담당이면 다른 학년 대회도 챙겨야 하므로 학년 제외보다 우선
    if grades or any(k in text for k in cfg.exclude_keywords):
        return OTHER
    return "전체"
