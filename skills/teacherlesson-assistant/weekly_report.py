"""수업 메모를 한 주 단위 정리 글로 만든다: sessions/ → reports/week-<월요일>.md

    python weekly_report.py                  # 이번 주
    python weekly_report.py --date 2026-11-20  # 그 날이 들어 있는 주

- 데이터 폴더의 파일만 읽고 쓴다. 바깥에 보내지 않으며, 화면에는 메모 내용 없이 개수만 낸다.
- 학생 이름은 '학생별' 절에만 둔다. 🙋 메모의 첫 낱말을 이름으로 보고, 다른 절에 같은 이름이 있으면 가린다.
  🙋 메모에 한 번도 안 적힌 이름은 알 수 없어 남는다.
- publisher_notes.json 은 읽기만 한다. 후보는 교사가 동의한 것만 넣는다(SKILL.md C).
"""
import argparse
import json
import pathlib
import re
import sys
from datetime import date, timedelta

SKILL_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(next(p / "_shared" for p in SKILL_DIR.parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir  # noqa: E402

SKILL = "teacherlesson-assistant"
SECTIONS = (("fix", "🔧 고칠점"), ("good", "👍 좋았음"), ("note", "📝 메모"), ("voice", "🎤 음성 메모"), ("star", "★ 표시"))
JOSA = re.compile(r"(이가|에게|한테|이|가|은|는|을|를|도|의)$")


def read_json(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def load_sessions(sessions: pathlib.Path):
    """(기록 목록, 못 읽은 파일 수). 날짜는 폴더 이름을 따른다."""
    records, broken = [], 0
    for path in sorted(sessions.glob("*/*.json")):
        try:
            day = date.fromisoformat(path.parent.name)
        except ValueError:
            continue
        rec = read_json(path)
        if not isinstance(rec, dict) or not isinstance(rec.get("memos", []), list):
            broken += 1
            continue
        memos = []
        for memo in rec.get("memos", []):
            if not isinstance(memo, dict):
                continue
            text = " ".join(str(memo.get("text") or "").split())
            if text and text != "(표시)":
                memos.append((memo.get("kind"), text))
        stem = path.stem.split("_", 1)
        records.append({
            "day": day,
            "period": stem[0],
            "subject": str(rec.get("subject") or stem[-1]),
            "publisher": str(rec.get("publisher") or ""),
            "title": " ".join(str(rec.get("title") or "").split()),
            "memos": memos,
        })
    return records, broken


def student_name(text: str) -> str:
    """🙋 메모의 첫 낱말. 낱말이 하나뿐이면 이름인지 알 수 없어 빈 글."""
    words = text.split()
    return words[0].strip(",.:;()[]") if len(words) > 1 else ""


def known_names(records) -> list[str]:
    """가릴 이름 목록(긴 것 먼저). '학생A가' 처럼 조사가 붙었으면 뗀 것도 넣는다."""
    names = set()
    for rec in records:
        for kind, text in rec["memos"]:
            if kind == "student":
                name = student_name(text)
                names.update(n for n in (name, JOSA.sub("", name)) if len(n) >= 2)
    return sorted(names, key=len, reverse=True)


def mask(text: str, names) -> str:
    for name in names:
        text = text.replace(name, "(학생)")
    return text


def build_report(records, monday: date, names, cautions: dict) -> str:
    end = monday + timedelta(days=6)
    week = [r for r in records if monday <= r["day"] <= end]
    lines = [f"# 주간 수업 정리 {monday} ~ {end}", "",
             "> 학생 이름이 들어 있을 수 있는 파일입니다. 데이터 폴더 밖으로 옮기거나 보내지 마세요.", ""]

    groups, students, candidates = {}, {}, {}
    for rec in week:
        key = (rec["subject"], rec["publisher"])
        where = f"{rec['day']:%m-%d} {rec['period']}"
        title = mask(rec["title"], names)
        for kind, text in rec["memos"]:
            if kind == "student":
                students.setdefault(student_name(text) or "이름 확인 필요", []).append(f"- {where} {rec['subject']}: {text}")
                continue
            if kind not in dict(SECTIONS):
                continue  # 단계 이동·시간 조정 기록
            safe = mask(text, names)
            groups.setdefault(key, {}).setdefault(kind, []).append(f"- {safe} ({f'{where} {title}'.strip()})")
            if kind == "fix" and rec["publisher"] and safe == text:
                candidates.setdefault(f"{rec['publisher']}|{rec['subject']}", []).append((text, (rec["day"], rec["period"])))

    lines += ["## 과목·출판사별", ""]
    if not groups:
        lines += ["이번 주에 남긴 수업 메모가 없습니다.", ""]
    for (subject, publisher), kinds in sorted(groups.items()):
        lines += [f"### {subject} ({publisher or '출판사 확인 필요'})", ""]
        for kind, label in SECTIONS:
            if kind in kinds:
                lines += [f"**{label}**", *kinds[kind], ""]

    lines += ["## 출판사 주의점 후보", "",
              "고칠점 중 아직 `publisher_notes.json` 에 없는 것입니다. 넣을 것만 골라 주세요(자동으로 넣지 않음).",
              "이 글은 AI 질문에 함께 들어갈 수 있으니, 넣기 전에 이름이 없는지 읽어 보세요.", ""]
    found = False
    for key, items in sorted(candidates.items()):
        known = {c.get("text") for c in cautions.get(key, []) if isinstance(c, dict)}
        fresh = list(dict.fromkeys(text for text, _ in items if text not in known))
        if not fresh:
            continue
        found = True
        count = len({lesson for _, lesson in items})
        repeat = f" — 이번 주 {count}개 수업에서 고칠점" if count > 1 else ""
        lines += [f"### {key.replace('|', ' / ')}{repeat}", *[f"- [ ] {text}" for text in fresh], ""]
    if not found:
        lines += ["후보가 없습니다.", ""]

    lines += ["## 🙋 학생별 발표 메모", ""]
    if not students:
        lines += ["이번 주 발표 메모가 없습니다.", ""]
    else:
        lines += ["메모의 첫 낱말로 묶었습니다.", ""]
    for name, items in sorted(students.items()):
        lines += [f"### {name}", *items, ""]
    return "\n".join(lines)


def make_report(data: pathlib.Path, day: date):
    """정리 글을 저장하고 (파일 경로, 그 주 수업 기록 수, 못 읽은 파일 수) 를 돌려준다."""
    monday = day - timedelta(days=day.weekday())
    records, broken = load_sessions(data / "sessions")
    cautions = read_json(data / "publisher_notes.json")
    # 이름은 지난 기록 전체에서 모은다(이번 주에 🙋 가 없던 학생도 가리려고).
    text = build_report(records, monday, known_names(records), cautions if isinstance(cautions, dict) else {})
    path = data / "reports" / f"week-{monday}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    count = sum(monday <= r["day"] <= monday + timedelta(days=6) for r in records)
    return path, count, broken


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="수업 메모 주간 정리")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today(), help="그 날이 들어 있는 주 (YYYY-MM-DD)")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    path, count, broken = make_report(data_dir(SKILL), args.date)
    print(f"수업 기록 {count}개를 정리했어요: {path}")
    if broken:
        print(f"⚠ 읽지 못한 기록 파일 {broken}개(전체 기간)")


if __name__ == "__main__":
    main()
