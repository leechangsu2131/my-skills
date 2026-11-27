"""작업자 현황표: 원격 브랜치·할 일 목록(TASKS)·작업 일지를 모아 한눈에 보여 준다. 기본 파이썬 + git 만 씀.

    python tools/work_status.py            # 화면에 현황표
    python tools/work_status.py --fetch    # 먼저 git fetch --all --prune
    python tools/work_status.py --md       # 마크다운으로 (교사에게 보여 주거나 붙여 넣기)

보여 주는 것
- 진행 중인 작업 브랜치: TASKS 번호, 작업자(마지막 커밋한 사람), 마지막 커밋 때, main 보다 앞선 커밋 수, 충돌 여부, 멈춤(3일 넘게 새 커밋 없음)
- 합칠 준비가 된 것(충돌 없음) / 오래 멈춘 것
- TASKS 에서 '열림'인데 아무도 안 잡은 일 수(목록 채우기 필요 신호)
- 작업 일지(docs/worklog/*.md)의 마지막 기록 — main 과 각 브랜치에서
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or "."
STALE_DAYS = 3
sys.path.insert(0, str(Path(__file__).resolve().parent))
import claim_task  # noqa: E402  이어받기 기준(멈춘 시간·일지 마지막 줄)을 claim_task.py 와 똑같이 쓰려고
TASK_RE = re.compile(r"\b(T\d{2,3}|S\d{1,2})\b", re.I)


def git(*args: str) -> str:
    res = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res.stdout.strip()


def git_ok(*args: str) -> bool:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True).returncode == 0


def task_rows() -> dict[str, dict]:
    """docs/TASKS.md 표에서 번호·설명 앞부분·상태(마지막 칸)."""
    # 지금 폴더가 다른 브랜치일 수 있으니(여러 세션이 같은 폴더를 씀) 원격 main 의 목록을 읽는다
    text = git("show", "origin/main:docs/TASKS.md")
    if not text:
        try:
            text = open(f"{ROOT}/docs/TASKS.md", encoding="utf-8").read()
        except OSError:
            return {}
    rows = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and re.fullmatch(r"[TS]\d{1,3}", cells[0]):
            rows[cells[0].upper()] = {"desc": re.sub(r"\*\*|`", "", cells[1])[:40], "status": cells[-1]}
    return rows


def branches() -> list[dict]:
    out = []
    main = "origin/main"
    for ref in git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin").splitlines():
        if ref in (main, "origin/HEAD", "origin") or not ref.startswith("origin/"):
            continue
        ahead = int(git("rev-list", "--count", f"{main}..{ref}") or 0)
        if ahead == 0:
            continue  # 이미 다 합쳐진 브랜치
        # 커밋 번호는 달라도(rebase 등) 같은 내용이 이미 main 에 있으면 합쳐진 것으로 본다
        cherry = git("cherry", main, ref).splitlines()
        if cherry and all(line.startswith("-") for line in cherry):
            continue
        behind = int(git("rev-list", "--count", f"{ref}..{main}") or 0)
        when = git("log", "-1", "--format=%cI", ref)
        who = git("log", "-1", "--format=%an", ref)
        subject = git("log", "-1", "--format=%s", ref)
        name = ref.removeprefix("origin/")
        tasks = sorted({m.upper() for m in TASK_RE.findall(name + " " + subject)})
        clean = git_ok("merge-tree", "--write-tree", main, ref)
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(when)).days
        except ValueError:
            age = 0
        files = len(git("diff", "--name-only", f"{main}...{ref}").splitlines())
        log = last_worklog(ref)
        takeover = None
        if name.startswith("task/"):
            prev = os.getcwd()
            try:
                os.chdir(ROOT)
                takeover = claim_task.takeover_reason(claim_task.branch_state(ref))
            except claim_task.GitError:
                takeover = None
            finally:
                os.chdir(prev)
        out.append({"branch": name, "tasks": tasks, "who": who, "when": when[:16].replace("T", " "),
                    "age": age, "ahead": ahead, "behind": behind, "clean": clean, "files": files,
                    "subject": subject[:60], "log": log, "takeover": takeover})
    return sorted(out, key=lambda b: b["when"], reverse=True)


def last_worklog(ref: str) -> str:
    """그 브랜치에서 바뀐 docs/worklog/*.md 의 마지막 기록 한 줄."""
    changed = [f for f in git("diff", "--name-only", f"origin/main...{ref}").splitlines() if f.startswith("docs/worklog/")]
    for f in changed:
        lines = [l for l in git("show", f"{ref}:{f}").splitlines() if l.strip().startswith(("- ", "* "))]
        if lines:
            return lines[-1].strip()[2:][:90]
    return ""


def main_worklogs() -> list[tuple[str, str]]:
    out = []
    for f in git("ls-tree", "--name-only", "origin/main", "docs/worklog/").splitlines():
        if f.endswith("README.md") or not f.endswith(".md"):
            continue
        lines = [l for l in git("show", f"origin/main:{f}").splitlines() if l.strip().startswith(("- ", "* "))]
        if lines:
            out.append((f.split("/")[-1][:-3], lines[-1].strip()[2:][:90]))
    return out


def report(as_md: bool) -> str:
    rows, tasks = branches(), task_rows()
    taken = {t for b in rows for t in b["tasks"]}
    # 상태 칸이 "R · 열림"·"P · 열림"(등급·상태 칸)인 줄도 센다
    open_free = [k for k, v in tasks.items() if re.match(r"(?:[RPT]\s*·\s*)?열림", v["status"]) and k not in taken]
    ready = [b for b in rows if b["clean"] and b["age"] <= STALE_DAYS]
    stale = [b for b in rows if b["age"] > STALE_DAYS]
    free_to_take = [b for b in rows if b["takeover"]]
    L = []
    L.append(f"# 작업 현황 ({datetime.now():%Y-%m-%d %H:%M})")
    L.append("")
    L.append(f"- 진행 중 브랜치 {len(rows)}개 · 합칠 준비(충돌 없음) {len(ready)}개 · 멈춤({STALE_DAYS}일 넘게) {len(stale)}개")
    L.append(f"- 이어받기 가능({claim_task.STALE_HOURS:g}시간 넘게 멈춤·그만둠): {len(free_to_take)}개 — 다음 작업자의 `claim_task.py --next` 가 먼저 잡음")
    L.append(f"- TASKS '열림' 중 아무도 안 잡은 일: {len(open_free)}개" + ("  ← 10개 아래면 목록 채우기" if len(open_free) < 10 else ""))
    L.append("")
    L.append("| 브랜치 | 일 | 작업자 | 마지막 커밋 | 앞섬/뒤처짐 | 파일 | 충돌 | 마지막 일지 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for b in rows:
        mark = "" if b["clean"] else "⚠ 있음"
        when = b["when"] + (f" (멈춤 {b['age']}일)" if b["age"] > STALE_DAYS else "")
        if b["takeover"]:
            when += " · 이어받기 가능"
        tdesc = ", ".join(f"{t} {tasks.get(t, {}).get('desc', '')}".strip() for t in b["tasks"]) or "(번호 없음)"
        L.append(f"| `{b['branch']}` | {tdesc} | {b['who']} | {when} | {b['ahead']}/{b['behind']} | {b['files']} | {mark or '없음'} | {b['log'] or b['subject']} |")
    if open_free:
        L.append("")
        L.append("**아무도 안 잡은 '열림' 일**: " + ", ".join(open_free))
    logs = main_worklogs()
    if logs:
        L.append("")
        L.append("**작업자 일지 마지막 줄 (main)**")
        L += [f"- {who}: {line}" for who, line in logs]
    text = "\n".join(L)
    if not as_md:
        text = text.replace("**", "").replace("`", "")
    return text


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--md", action="store_true")
    a = ap.parse_args()
    if a.fetch:
        git("fetch", "--all", "--prune")
    print(report(a.md))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
