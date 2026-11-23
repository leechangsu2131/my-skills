"""Google Keep(Takeout) 메모를 md로 풀어 볼트 밖에 모은다.

운용지침: 원시 기록은 볼트에 통째로 옮기지 않는다. 그래서 이 스크립트는 볼트를 건드리지 않고
<내 문서>/my-skills-data/personal-obsidansystem-main/keep/ 아래에만 쓴다.
승격 후보를 고른 뒤에만 볼트 00_Inbox로 옮긴다(SKILL.md "Keep 메모 가져오기" 참고).

사용:
  python keep_import.py <takeout.zip 또는 압축 푼 폴더> [--include-archived] [--only-new]

만드는 것 (keep/YYYYMMDD_HHMMSS/):
  notes/*.md   메모 하나당 파일 하나 (frontmatter: source, keep_created, keep_edited, labels ...)
  _전체.md     모든 메모를 시간순으로 이은 파일 (NotebookLM 업로드·Claude 훑어보기용)
  _목록.csv    번호·날짜·라벨·제목·글자 수·첫 줄 (Claude가 이것만 보고 후보를 고른다)
상태 파일 keep/_seen.json 에 가져온 메모 id를 남겨 --only-new 로 새 메모만 뽑을 수 있다.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(next(p / "_shared" for p in Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir  # 결과물(메모 내용)은 저장소 밖에 둔다


def iter_keep_json(src: Path):
    """(이름, dict) 를 돌려준다. zip이든 폴더든 Keep 폴더 안 *.json 만 읽는다."""
    if src.is_file() and src.suffix.lower() == ".zip":
        with zipfile.ZipFile(src) as zf:
            for name in zf.namelist():
                if name.lower().endswith(".json") and "/keep/" in name.replace("\\", "/").lower():
                    try:
                        yield name, json.loads(zf.read(name).decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        print(f"  건너뜀(읽기 실패): {name}", file=sys.stderr)
    else:
        for p in sorted(src.rglob("*.json")):
            if "keep" not in str(p.parent).lower():
                continue
            try:
                yield p.name, json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                print(f"  건너뜀(읽기 실패): {p}", file=sys.stderr)


def usec_to_dt(v) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(v) / 1_000_000)
    except (TypeError, ValueError, OSError):
        return None


def note_body(n: dict) -> str:
    parts = []
    text = (n.get("textContent") or "").strip()
    if text:
        parts.append(text)
    for item in n.get("listContent") or []:
        mark = "x" if item.get("isChecked") else " "
        parts.append(f"- [{mark}] {item.get('text', '').strip()}")
    for a in n.get("annotations") or []:
        if a.get("url"):
            parts.append(f"- 링크: [{a.get('title') or a['url']}]({a['url']})")
    for a in n.get("attachments") or []:
        parts.append(f"- 첨부: {a.get('filePath', '')} ({a.get('mimetype', '')})")
    return "\n".join(parts).strip()


def note_id(name: str, n: dict) -> str:
    created = str(n.get("createdTimestampUsec") or "")
    return hashlib.sha1(f"{Path(name).stem}|{created}".encode("utf-8")).hexdigest()[:12]


def safe_name(s: str, limit: int = 50) -> str:
    s = re.sub(r'[\\/:*?"<>|\r\n\t#^\[\]]+', " ", s).strip()
    return re.sub(r"\s+", " ", s)[:limit].strip() or "제목없음"


def yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main() -> int:
    ap = argparse.ArgumentParser(description="Google Keep Takeout → md (볼트 밖)")
    ap.add_argument("source", help="Takeout zip 파일 또는 압축 푼 폴더")
    ap.add_argument("--include-archived", action="store_true", help="보관처리된 메모도 포함")
    ap.add_argument("--only-new", action="store_true", help="예전에 가져온 메모는 빼고 새 메모만")
    args = ap.parse_args()

    src = Path(args.source).expanduser().resolve()
    if not src.exists():
        print(f"없는 경로: {src}", file=sys.stderr)
        return 2

    base = data_dir() / "keep"
    seen_path = base / "_seen.json"
    seen: dict = json.loads(seen_path.read_text(encoding="utf-8")) if seen_path.exists() else {}

    notes = []
    skipped = {"휴지통": 0, "보관": 0, "빈 메모": 0, "이미 가져옴": 0}
    for name, n in iter_keep_json(src):
        if not isinstance(n, dict) or not ({"textContent", "listContent", "title"} & n.keys()):
            continue
        if n.get("isTrashed"):
            skipped["휴지통"] += 1
            continue
        if n.get("isArchived") and not args.include_archived:
            skipped["보관"] += 1
            continue
        body = note_body(n)
        title = (n.get("title") or "").strip()
        if not body and not title:
            skipped["빈 메모"] += 1
            continue
        nid = note_id(name, n)
        if args.only_new and nid in seen:
            skipped["이미 가져옴"] += 1
            continue
        created = usec_to_dt(n.get("createdTimestampUsec"))
        edited = usec_to_dt(n.get("userEditedTimestampUsec")) or created
        notes.append({
            "id": nid,
            "title": title,
            "body": body,
            "created": created,
            "edited": edited,
            "labels": [l.get("name", "") for l in n.get("labels") or [] if l.get("name")],
            "pinned": bool(n.get("isPinned")),
            "archived": bool(n.get("isArchived")),
        })

    notes.sort(key=lambda x: x["created"] or datetime.min)
    if not notes:
        print("가져올 메모가 없습니다.", {k: v for k, v in skipped.items() if v})
        return 0

    out = base / datetime.now().strftime("%Y%m%d_%H%M%S")
    (out / "notes").mkdir(parents=True, exist_ok=True)
    rows, merged = [], []
    for i, n in enumerate(notes, 1):
        first_line = next((l.strip() for l in n["body"].splitlines() if l.strip()), "")
        first_line = re.sub(r"^- \[[ x]\] ", "", first_line)
        title = n["title"] or first_line[:40] or "제목없음"
        day = n["created"].strftime("%Y-%m-%d") if n["created"] else "날짜없음"
        fname = f"{i:04d}_{day}_{safe_name(title)}.md"
        fm = [
            "---",
            "source: google-keep",
            f"keep_id: {n['id']}",
            f"keep_created: {n['created'].isoformat(timespec='minutes') if n['created'] else ''}",
            f"keep_edited: {n['edited'].isoformat(timespec='minutes') if n['edited'] else ''}",
            f"labels: [{', '.join(yaml_str(l) for l in n['labels'])}]",
        ]
        if n["pinned"]:
            fm.append("pinned: true")
        if n["archived"]:
            fm.append("archived: true")
        fm.append("---")
        heading = f"# {n['title']}\n\n" if n["title"] else ""
        (out / "notes" / fname).write_text("\n".join(fm) + "\n\n" + heading + n["body"] + "\n", encoding="utf-8")

        label_txt = ", ".join(n["labels"])
        merged.append(f"## {i}. {title}\n- 날짜: {day}" + (f" · 라벨: {label_txt}" if label_txt else "") + f"\n\n{n['body']}\n")
        rows.append([i, day, label_txt, n["title"], len(n["body"]), first_line[:80], fname])
        seen[n["id"]] = day

    (out / "_전체.md").write_text(
        f"# Google Keep 메모 ({len(notes)}개, {datetime.now():%Y-%m-%d} 추출)\n\n" + "\n---\n\n".join(merged),
        encoding="utf-8",
    )
    with open(out / "_목록.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["번호", "날짜", "라벨", "제목", "글자수", "첫줄", "파일"])
        w.writerows(rows)
    seen_path.write_text(json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"메모 {len(notes)}개 → {out}")
    print("  제외:", {k: v for k, v in skipped.items() if v} or "없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
