"""수업 흐름 JSON을 읽기만 하며 빠진 값과 지도서 혼입 의심을 점검한다."""
import argparse
import json
import pathlib
import re
import sys


TEXT_FIELDS = (
    "name", "purpose", "do", "say", "tip", "teacher_support", "check",
    "teacher_actions", "teacher_prompts", "student_actions", "expected_responses",
)
LEGACY_FIELDS = {"do", "say", "tip"}
GUIDE_WORD = re.compile(r"[가-힣]{2,}|[A-Za-z]{3,}|\d+")


def _text(value) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value or "")


def flow_words(flow: dict) -> set[str]:
    """목표와 단계 안내에서 지도서 대조에 쓸 낱말을 뽑는다."""
    parts = [_text(flow.get("goal"))]
    for step in flow.get("steps", []):
        if isinstance(step, dict):
            parts.extend(_text(step.get(field)) for field in TEXT_FIELDS)
    return {word.casefold() for word in GUIDE_WORD.findall(" ".join(parts))}


def guide_word_ratio(flow: dict, guide_text: str) -> tuple[int, int, float | None]:
    """(지도서에 없는 낱말 수, 흐름 낱말 수, 비율). 낱말이 없으면 비율은 None."""
    words = flow_words(flow)
    if not words:
        return 0, 0, None
    guide = {word.casefold() for word in GUIDE_WORD.findall(guide_text or "")}
    missing = words - guide
    return len(missing), len(words), len(missing) / len(words)


def check_flow(flow) -> list[str]:
    """흐름 한 개의 문제를 사람이 읽을 짧은 문장 목록으로 돌려준다."""
    if not isinstance(flow, dict):
        return ["JSON 맨 위가 객체가 아님"]

    issues = []
    if not str(flow.get("goal") or "").strip():
        issues.append("차시 목표 없음")

    steps = flow.get("steps")
    if not isinstance(steps, list) or not steps:
        return issues + ["단계 없음"]

    total = 0.0
    names = []
    has_legacy = False
    has_new = False
    for number, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            issues.append(f"{number}단계가 객체가 아님")
            continue
        name = " ".join(str(step.get("name") or "").split())
        if not name:
            issues.append(f"{number}단계 이름 없음")
        else:
            names.append(name.casefold())
        minutes = step.get("minutes")
        if isinstance(minutes, bool) or not isinstance(minutes, (int, float)):
            issues.append(f"{number}단계 분이 숫자가 아님")
        elif minutes <= 0:
            issues.append(f"{number}단계 분이 0 이하")
        else:
            total += minutes
        has_legacy |= any(_text(step.get(field)).strip() for field in LEGACY_FIELDS)
        has_new |= any(_text(step.get(field)).strip() for field in set(TEXT_FIELDS) - LEGACY_FIELDS - {"name"})

    duplicate = sorted({name for name in names if names.count(name) > 1})
    if duplicate:
        issues.append("같은 단계명 반복: " + ", ".join(duplicate))
    if total < 35 or total > 45:
        issues.append(f"시간 합계 {total:g}분(35~45분 아님)")
    if has_legacy and has_new:
        issues.append("옛 안내(do/say/tip)와 새 단계별 안내가 섞임")
    return issues


def check_file(path: pathlib.Path, guide_text: str | None = None) -> dict:
    try:
        flow = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError) as exc:
        return {"path": path, "issues": [f"JSON 읽기 실패: {exc}"], "guide": None}
    guide = guide_word_ratio(flow, guide_text) if guide_text is not None and isinstance(flow, dict) else None
    return {"path": path, "issues": check_flow(flow), "guide": guide}


def render_table(results: list[dict]) -> str:
    lines = ["| 파일 | 시간·구조 점검 | 지도서에 없는 낱말 |", "|---|---|---|"]
    for result in results:
        issues = "<br>".join(result["issues"]) or "정상"
        guide = result["guide"]
        ratio = "-" if guide is None or guide[2] is None else f"{guide[0]}/{guide[1]} ({guide[2]:.0%})"
        lines.append(f"| {result['path'].name} | {issues} | {ratio} |")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="수업 흐름 JSON 점검(파일은 고치지 않음)")
    parser.add_argument("flows", type=pathlib.Path, help="flows 폴더")
    parser.add_argument("--guide", type=pathlib.Path, help="대조할 지도서 구간 md")
    args = parser.parse_args(argv)
    if not args.flows.is_dir():
        parser.error(f"flows 폴더가 없습니다: {args.flows}")
    try:
        guide = args.guide.read_text(encoding="utf-8-sig") if args.guide else None
    except (OSError, UnicodeError) as exc:
        parser.error(f"지도서 글을 읽을 수 없습니다: {exc}")
    results = [check_file(path, guide) for path in sorted(args.flows.glob("*.json"))]
    print(render_table(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
