"""일 잡기 — 실행 직전에 같은 일을 누가 하는지 확인하고, 비어 있으면 브랜치·일지 '시작' 줄을 올려 잡는다.

    python tools/claim_task.py T77 --check                                   # 확인만(아무것도 바꾸지 않음)
    python tools/claim_task.py T77 write-lock --name bizcoder-1              # 잡기
    python tools/claim_task.py T31 korean --name gemini-1 --skill admin-s2b-buyer   # 여러 스킬에 걸친 일·상시 일(S)

종료값: 0 잡음(--check 면 비어 있음, 이미 내가 잡은 일이면 이어서) / 1 이미 누가 함·완료·교사 결정 대기 / 2 사용법·git 오류

왜: 교사가 여러 작업자에게 같은 일을 "해"라고 할 수 있고, 다른 폴더(따로 받은 저장소)에서 일하면
원격 브랜치를 새로 받지 않아 남이 잡은 일을 못 본다. 2026-11-25~26 T10·T11·T23·T25 가 그렇게 두 번씩 만들어졌다.

보는 것 (모두 바로 앞에서 `git fetch --prune` 한 뒤)
1. 원격 main 의 docs/TASKS.md 상태: `완료`·`교사 결정 대기` 면 잡지 않음
2. 원격 브랜치 `task/<번호>-…` — `git ls-remote` 로 원격에 직접 묻는다(main 만 받아 오는 복제본에서도 보이게)
3. 이 저장소의 로컬 브랜치 `task/<번호>-…` — 같은 PC 의 다른 작업 폴더(git worktree, tools/start_worker.ps1)가
   아직 안 올린 것도 보인다(작업 폴더끼리 브랜치 목록을 같이 씀)
--skill 을 주면 브랜치 이름에 그 스킬 이름이 든 것만 같은 일로 본다(T31·T33·S1 처럼 스킬마다 따로 잡는 일).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class GitError(Exception):
    pass


def git(*args: str, check: bool = True) -> str:
    res = subprocess.run(["git", "-c", "core.quotepath=false", *args], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if check and res.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {res.stderr.strip()}")
    return res.stdout.strip()


def task_status(number: str) -> str | None:
    """원격 main 의 TASKS 표에서 그 번호 줄의 마지막 칸(상태). 줄이 없으면 None."""
    text = git("show", "origin/main:docs/TASKS.md", check=False)
    m = re.search(r"^\|\s*" + re.escape(number) + r"\s*\|.*\|\s*([^|\n]*?)\s*\|\s*$", text, re.M)
    return m.group(1) if m else None


def blocked_reason(status: str | None) -> str | None:
    if status is None:
        return None
    if "완료" in status:
        return f"TASKS 상태가 '{status}'"
    if "결정 대기" in status:
        return f"TASKS 상태가 '{status}' — 교사 결정이 먼저"
    return None


def same_task_branches(number: str, skill: str | None) -> list[str]:
    """같은 번호의 원격·로컬 브랜치 이름들(origin/ 은 붙여서)."""
    prefix = re.compile(r"^task/" + re.escape(number) + r"-", re.I)

    def wanted(short: str) -> bool:
        return bool(prefix.match(short)) and (not skill or skill.lower() in short.lower())

    out = []
    # 원격은 git ls-remote 로 직접 묻는다. main 만 받아 오는 복제본(--single-branch, 웹 작업자 등)은
    # fetch 해도 남의 task/… 브랜치가 refs/remotes 에 안 생겨서, 그것만 보면 겹침을 놓친다(2026-11-26 작업자 제보).
    for line in git("ls-remote", "--heads", "origin").splitlines():
        ref = line.split("\t")[-1]
        short = ref[len("refs/heads/"):]
        if ref.startswith("refs/heads/") and wanted(short):
            # 내용(일지)을 볼 수 있게 그 브랜치만 받아 둔다
            git("fetch", "--quiet", "origin", f"+{ref}:refs/remotes/origin/{short}", check=False)
            out.append("origin/" + short)
    # 로컬 브랜치: 같은 저장소의 다른 작업 폴더(git worktree)가 아직 안 올린 것도 여기 보인다
    for ref in git("for-each-ref", "--format=%(refname)", "refs/heads/task/").splitlines():
        short = ref[len("refs/heads/"):]
        if wanted(short) and "origin/" + short not in out:
            out.append(short)
    return out


def owner_is_me(branch: str, name: str, number: str) -> bool:
    """그 브랜치의 내 일지에 이 번호 '시작' 줄이 있으면 내가 잡은 일."""
    log = git("show", f"{branch}:docs/worklog/{name}.md", check=False)
    return bool(re.search(re.escape(number) + r"\b[^\n]*시작", log))


def worktree_of(branch: str) -> str | None:
    """로컬 브랜치를 쓰고 있는 작업 폴더."""
    cur = None
    for line in git("worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            cur = line[len("worktree "):]
        elif line == f"branch refs/heads/{branch}":
            return cur
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("number", help="TASKS 번호(예: T77, S1)")
    ap.add_argument("desc", nargs="?", help="브랜치 이름 뒷부분(짧은 영어, 예: write-lock)")
    ap.add_argument("--name", help="작업자 이름(일지 파일 이름) — 잡을 때 필요")
    ap.add_argument("--skill", help="스킬마다 따로 잡는 일이면 스킬 이름")
    ap.add_argument("--check", action="store_true", help="확인만")
    a = ap.parse_args(argv)
    number = a.number.upper()
    if not re.fullmatch(r"[TS]\d{1,3}", number):
        print(f"번호 모양이 아니에요: {a.number} (예: T77, S1)")
        return 2
    if number.startswith("S") and not a.skill:
        print("상시 일(S)은 --skill <스킬 이름> 으로 무엇을 하는지 정해야 해요(겹침 확인용).")
        return 2
    if not a.check and not (a.desc and a.name):
        print("잡으려면 브랜치 설명과 --name 이 필요해요. 확인만 하려면 --check.")
        return 2

    try:
        git("fetch", "--quiet", "--prune", "origin")
        why = blocked_reason(task_status(number))
        if why:
            print(f"❌ {number} 는 잡지 않아요: {why}")
            return 1
        found = same_task_branches(number, a.skill)
        mine = [b for b in found if a.name and owner_is_me(b, a.name, number)]
        others = [b for b in found if b not in mine]
        if others:
            print(f"❌ {number}{' (' + a.skill + ')' if a.skill else ''} 는 이미 누가 하고 있어요:")
            for b in others:
                where = worktree_of(b) if not b.startswith("origin/") else None
                last = git("log", "-1", "--format=%an, %ad", "--date=format:%m-%d %H:%M", b, check=False)
                print(f"   {b}  ({last}{', 작업 폴더 ' + where if where else ''})")
            print("→ 시작하지 말고 교사(오케스트레이터)에게 한 줄 알린 뒤 다른 일을 고르세요.")
            return 1
        if mine:
            print(f"✅ {number} 는 이미 {a.name} 가 잡은 일이에요(이어서 하세요): {', '.join(mine)}")
            return 0
        if a.check:
            print(f"✅ {number}{' (' + a.skill + ')' if a.skill else ''} 는 비어 있어요.")
            return 0

        if git("status", "--porcelain"):
            print("❌ 이 작업 폴더에 커밋 안 한 변경이 있어요. 정리한 뒤 다시 잡으세요(남의 변경이 섞이지 않게).")
            return 2
        desc = re.sub(r"[^A-Za-z0-9._-]+", "-", a.desc).strip("-").lower() or "work"
        branch = f"task/{number}-{desc}"
        git("switch", "--quiet", "-c", branch, "origin/main")
        root = Path(git("rev-parse", "--show-toplevel"))
        log = root / "docs" / "worklog" / f"{a.name}.md"
        log.parent.mkdir(parents=True, exist_ok=True)
        text = log.read_text(encoding="utf-8") if log.exists() else f"# {a.name} 일지\n\n"
        if not text.endswith("\n"):
            text += "\n"
        scope = f" ({a.skill})" if a.skill else ""
        text += f"- {datetime.now():%Y-%m-%d %H:%M} {number}{scope} 시작 (브랜치 {branch})\n"
        log.write_text(text, encoding="utf-8")
        git("add", str(log.relative_to(root)))
        git("commit", "--quiet", "-m", f"docs: [worklog] {a.name} {number}{scope} 시작")
        push = subprocess.run(["git", "push", "--quiet", "-u", "origin", branch], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if push.returncode != 0:
            print(f"❌ 올리지 못했어요(같은 이름을 누가 먼저 올렸을 수 있음): {push.stderr.strip()}")
            return 1
        # 거의 같은 때 다른 이름으로 잡은 사람이 있는지 한 번 더
        git("fetch", "--quiet", "--prune", "origin")
        rivals = [b for b in same_task_branches(number, a.skill) if b not in (branch, "origin/" + branch)]
        if rivals:
            print(f"⚠ 잡았지만 거의 같은 때 같은 일을 잡은 브랜치가 있어요: {', '.join(rivals)} → 교사에게 알리세요.")
            return 1
        print(f"✅ {number}{scope} 를 잡았어요: 브랜치 {branch} (일지 '시작' 줄을 올림)")
        return 0
    except GitError as e:
        print(f"❌ git 오류: {e}")
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # 윈도우 까만 창에서 한글이 깨지지 않게
    sys.exit(main())
