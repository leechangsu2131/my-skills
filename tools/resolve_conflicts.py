"""합치기(merge) 중 충돌난 일지·문서를 규칙대로 푼다 — 오케스트레이터가 작업자 브랜치를 합칠 때.

    python tools/resolve_conflicts.py                 # 충돌난 docs/worklog/*.md 만 푼다(나머지는 목록만 알림)
    python tools/resolve_conflicts.py --keep-both F…  # 지정한 마크다운 파일은 두 쪽 내용을 다 남긴다(충돌 표시만 지움)

규칙 (docs/ORCHESTRATION.md 3. 합치기)
- 작업자 일지(docs/worklog/<이름>.md): 두 쪽 줄을 모아 '- 날짜 시각' 줄을 시간순으로, 같은 줄은 한 번만.
  제목(# …)은 맨 위 한 번만. 항목 아래 이어지는 줄은 그 항목에 붙는다.
- --keep-both 로 준 문서(ISSUES.md 등): 두 쪽을 다 남긴다. 같은 내용이 두 번 들어가지 않았는지는 눈으로 본다.
- 코드 파일은 풀지 않는다(작업자에게 돌려보내거나 직접 판단).
푼 파일은 git add 한다. 커밋은 하지 않는다(남은 충돌이 없으면 `git commit --no-edit`).
종료값: 0 남은 충돌 없음 / 1 아직 충돌난 파일이 있음 / 2 git 오류
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

ITEM = re.compile(r"^- \d{4}-\d{2}-\d{2}")
MARKER = re.compile(r"^(<<<<<<< .*|=======|>>>>>>> .*)\r?\n", re.M)


def git(*args: str, check: bool = True) -> str:
    res = subprocess.run(["git", "-c", "core.quotepath=false", *args], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if check and res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {res.stderr.strip()}")
    return res.stdout


def conflicted() -> list[str]:
    return [f for f in git("diff", "--name-only", "--diff-filter=U").splitlines() if f]


def merge_worklog(ours: str, theirs: str) -> str:
    """두 쪽 일지를 합친 글."""
    head: list[str] = []
    items: list[str] = []
    seen: set[str] = set()
    for side in (ours, theirs):
        in_items = False
        for line in side.splitlines():
            if ITEM.match(line):
                in_items = True
                if line not in seen:
                    seen.add(line)
                    items.append(line)
            elif not in_items:
                if line not in head:
                    head.append(line)
            elif line.strip() and not line.startswith("#") and items and line not in items[-1].split("\n"):
                items[-1] += "\n" + line          # 항목 아래 이어지는 줄
    items.sort(key=lambda s: s[2:18])             # '- YYYY-MM-DD HH:MM'
    return "\n".join(head).rstrip() + "\n\n" + "\n".join(items) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep-both", nargs="*", default=[], help="두 쪽을 다 남길 마크다운 파일")
    a = ap.parse_args(argv)
    try:
        for path in conflicted():
            if path.startswith("docs/worklog/") and path.endswith(".md"):
                ours, theirs = git("show", f":2:{path}", check=False), git("show", f":3:{path}", check=False)
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(merge_worklog(ours, theirs))
            elif path in a.keep_both:
                with open(path, encoding="utf-8", newline="") as f:
                    text = f.read()
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(MARKER.sub("", text))
            else:
                continue
            git("add", path)
            print(f"   풀었어요: {path}")
        left = conflicted()
        if left:
            print("❌ 아직 충돌난 파일(직접 보세요 — 코드면 작업자에게 돌려보내기):")
            for f in left:
                print("   " + f)
            return 1
        print("✅ 남은 충돌 없음 → git commit --no-edit")
        return 0
    except RuntimeError as e:
        print(f"❌ {e}")
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
