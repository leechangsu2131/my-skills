"""로컬 IDE(Codex·Antigravity) 교대 작업용 — 받기·합치기·올리기를 한 번에.

교사 PC 에서는 로컬 IDE 하나가 원래 my-skills 폴더에서 일한다(한 번에 하나, 교대로).
GitHub 에서 일하는 작업자(Claude 웹 등)와 꼬이지 않게, 시작·중간·끝에 이 명령을 쓴다.

    python tools/sync_work.py start <브랜치>   # 시작: 깨끗한지 확인 → 받기 → 내 브랜치로 → 최신 main 합치기
    python tools/sync_work.py save             # 한 단계 끝·1~2시간마다: 받기 → 최신 main 합치기 → 올리기
    python tools/sync_work.py end              # 끝낼 때: save 한 뒤 폴더를 빈 상태(origin/main)로 → 다음 IDE 가 바로 시작

- 커밋은 직접 한다(고친 파일만 git add → git commit). 커밋 안 한 변경이 있으면 이 명령은 멈춘다.
- 합치기는 merge(rebase·강제 푸시 안 함). 충돌이 나면 합치기를 취소하고 충돌 파일을 알려 준다(폴더는 그대로).
- save·start 는 같은 파일을 고치는 다른 원격 브랜치가 있으면 알려 준다(먼저 합쳐질 쪽을 교사·Claude Code 와 정하기).

종료값: 0 됨 / 1 멈춤(커밋 안 한 변경·충돌 등 — 안내대로) / 2 사용법·git 오류
"""
from __future__ import annotations

import argparse
import subprocess
import sys


class GitError(Exception):
    pass


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "core.quotepath=false", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def git(*args: str, check: bool = True) -> str:
    res = run(*args)
    if check and res.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {res.stderr.strip()}")
    return res.stdout.strip()


def current_branch() -> str | None:
    return git("symbolic-ref", "-q", "--short", "HEAD", check=False) or None


def remote_has(branch: str) -> bool:
    return bool(git("rev-parse", "--verify", "-q", f"refs/remotes/origin/{branch}", check=False))


def stop_if_dirty(when: str) -> bool:
    changes = git("status", "--porcelain")
    if not changes:
        return False
    print(f"❌ 커밋 안 한 변경이 있어요({when} 멈춤):")
    for line in changes.splitlines()[:15]:
        print("   " + line)
    print("→ 내 변경이면 고친 파일만 git add → git commit 한 뒤 다시. 앞 IDE 가 남긴 변경이면 그 IDE 에서 커밋·푸시하거나 교사에게.")
    return True


def merge(ref: str, what: str) -> bool:
    """ref 를 지금 브랜치에 합친다. 충돌이면 취소하고 False."""
    res = run("merge", "--no-edit", ref)
    if res.returncode == 0:
        if "Already up to date" not in res.stdout:
            print(f"   {what} 을(를) 합쳤어요.")
        return True
    conflicts = git("diff", "--name-only", "--diff-filter=U", check=False)
    run("merge", "--abort")
    print(f"❌ {what} 을(를) 합치다 충돌이 났어요 — 합치기를 취소했어요(폴더는 그대로):")
    for f in conflicts.splitlines():
        print("   " + f)
    print("→ 내 프로젝트 파일이면 git merge " + ref + " 로 다시 합쳐 직접 풀고, 남의 영역이면 일지에 '막힘'을 적고 교사(Claude Code)에게.")
    return False


def changed_files(ref: str) -> set[str]:
    out = git("diff", "--name-only", f"origin/main...{ref}", check=False)
    return {f for f in out.splitlines() if f and not f.startswith("docs/worklog/")}


def report_overlaps(branch: str) -> None:
    mine = changed_files("HEAD")
    if not mine:
        return
    hits = []
    for ref in git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/").splitlines():
        if ref in ("origin/main", "origin/HEAD", "origin", f"origin/{branch}"):
            continue
        common = mine & changed_files(ref)
        if common:
            hits.append((ref, sorted(common)))
    if hits:
        print("⚠ 같은 파일을 고치는 다른 브랜치가 있어요(합칠 때 꼬일 수 있음 — 먼저 합칠 쪽을 정하세요):")
        for ref, files in hits:
            print(f"   {ref}: {', '.join(files[:5])}{' …' if len(files) > 5 else ''}")


def save(branch: str) -> int:
    if remote_has(branch) and not merge(f"origin/{branch}", f"원격의 {branch}"):
        return 1
    if not merge("origin/main", "최신 main"):
        return 1
    ahead = git("rev-list", "--count", f"origin/{branch}..HEAD") if remote_has(branch) else "새 브랜치"
    if ahead != "0":
        res = run("push", "--quiet", "-u", "origin", branch)
        if res.returncode != 0:
            print(f"❌ 올리지 못했어요: {res.stderr.strip()}")
            return 1
        print(f"   {branch} 를 올렸어요({ahead if ahead == '새 브랜치' else ahead + '개 커밋'}).")
    report_overlaps(branch)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["start", "save", "end"])
    ap.add_argument("branch", nargs="?", help="start 때 내 브랜치(예: proj/P2-phone-ui)")
    a = ap.parse_args(argv)
    try:
        if a.action == "start":
            if not a.branch:
                print("start 에는 브랜치 이름이 필요해요(예: proj/P2-phone-ui).")
                return 2
            if a.branch in ("main", "master"):
                print("main 에서는 일하지 않아요 — 내 브랜치 이름을 주세요(예: proj/P2-phone-ui).")
                return 2
            if stop_if_dirty("시작"):
                return 1
            git("fetch", "--quiet", "--prune", "origin")
            if git("rev-parse", "--verify", "-q", f"refs/heads/{a.branch}", check=False):
                git("switch", "--quiet", a.branch)
            elif remote_has(a.branch):
                git("switch", "--quiet", "-c", a.branch, "--track", f"origin/{a.branch}")
            else:
                git("switch", "--quiet", "-c", a.branch, "origin/main")
                print(f"   새 브랜치 {a.branch} 를 최신 main 에서 만들었어요.")
            if remote_has(a.branch) and not merge(f"origin/{a.branch}", f"원격의 {a.branch}"):
                return 1
            if not merge("origin/main", "최신 main"):
                return 1
            report_overlaps(a.branch)
            print(f"✅ 시작 준비 끝: {a.branch} (최신 main 까지 받음)")
            return 0

        branch = current_branch()
        if not branch or branch in ("main", "master"):
            print("❌ 내 브랜치가 아니에요. 먼저 python tools/sync_work.py start <브랜치>.")
            return 2
        if stop_if_dirty("올리기"):
            return 1
        git("fetch", "--quiet", "--prune", "origin")
        code = save(branch)
        if code:
            return code
        if a.action == "end":
            git("switch", "--quiet", "--detach", "origin/main")
            print(f"✅ 올리고 폴더를 비웠어요(최신 main). 이어서 할 때: python tools/sync_work.py start {branch}")
        else:
            print(f"✅ 받고 합치고 올렸어요: {branch}")
        return 0
    except GitError as e:
        print(f"❌ git 오류: {e}")
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
