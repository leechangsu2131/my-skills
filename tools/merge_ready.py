"""작업자 브랜치를 기계적으로 나누고, 문서·시험만 바꾼 것은 한꺼번에 합친다 (오케스트레이터용, 기본 파이썬 + git).

    python tools/merge_ready.py                 # 나누기만(합치지 않음): 문서·시험만 / 코드 바뀜 / 건너뜀
    python tools/merge_ready.py --merge         # 문서·시험만인 브랜치를 지금 브랜치에 합치고 시험·카탈로그 점검
    python tools/merge_ready.py --merge --push  # 다 통과하면 origin main 으로 푸시

- 지금 폴더가 main 이 아니어도 된다. 합치기는 **지금 체크아웃된 브랜치**에 하므로 보통 임시 worktree 에서 돌린다:
  git -c core.longpaths=true worktree add -b orch-<날짜> <짧은 경로> origin/main  →  그 폴더에서 이 도구 실행
- 충돌 처리: docs/worklog/*.md 는 두 쪽 줄을 시간순으로 모으고, 다른 .md 는 두 쪽 내용을 모두 남긴다.
  코드 파일 충돌이면 그 브랜치는 합치지 않고 '보류'.
- 건너뜀: 이미 내용이 main 에 있음(cherry), 브랜치가 더한 줄이 main 파일에 이미 거의 다 있음(다른 판으로 합쳐짐),
  브랜치 이름의 TASKS 번호가 docs/TASKS.md 에서 이미 '완료'(후속 보완 브랜치면 손으로 확인),
  7일 넘게 새 커밋 없음, 일지 한 파일만 바꿈('시작'만 한 것).
- 코드 바뀜 브랜치는 합치지 않는다 → reviewer 에이전트 검토 뒤 손으로.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ALREADY_RATIO = 0.9   # 브랜치가 더한 줄 중 main 에 이미 있는 비율이 이만큼이면 '다른 판으로 합쳐짐'
TASK_BRANCH = re.compile(r"^task/([TS]\d+)(?:-|$)")
TEST_FILE = re.compile(r"(^|/)(tests?/|test_[^/]*\.py$|[^/]*\.test\.js$|conftest\.py$)")


def git(*a: str, check: bool = False) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", "-c", "core.quotepath=false", *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise SystemExit(r.stderr.strip())
    return r


def out(*a: str) -> str:
    return git(*a).stdout.strip()


def already_in_main_ratio(ref: str, files: list[str]) -> tuple[int, int]:
    """브랜치(merge-base 이후)가 더한 빈 줄 아닌 줄 중 main 의 같은 파일에 이미 있는 줄 수. (있는 줄, 더한 줄)"""
    present = added = 0
    for f in files:
        diff = out("diff", "--unified=0", f"origin/main...{ref}", "--", f)
        lines = {l[1:].strip() for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++") and l[1:].strip()}
        if not lines:
            continue
        shown = git("show", f"origin/main:{f}")
        main_lines = {l.strip() for l in shown.stdout.splitlines()} if shown.returncode == 0 else set()
        added += len(lines)
        present += len(lines & main_lines)
    return present, added


def done_tasks() -> set[str]:
    """origin/main 의 docs/TASKS.md 표에서 상태가 '완료' 로 시작하는 번호(T80 같은)."""
    done = set()
    for line in git("show", "origin/main:docs/TASKS.md").stdout.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and re.fullmatch(r"[TS]\d+", cells[0]) and cells[-1].startswith("완료"):
            done.add(cells[0])
    return done


def classify() -> list[dict]:
    done = done_tasks()
    rows = []
    refs = out("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin").split()
    for ref in refs:
        name = ref.removeprefix("origin/")
        if name in ("main", "HEAD") or ref == "origin":
            continue
        ahead = int(out("rev-list", "--count", f"origin/main..{ref}") or 0)
        if not ahead:
            continue
        cherry = [l for l in out("cherry", "origin/main", ref).splitlines() if l]
        age_days = (int(out("log", "-1", "--format=%ct", "origin/main") or 0) - int(out("log", "-1", "--format=%ct", ref) or 0)) / 86400
        files = [l.split("\t")[-1] for l in out("diff", "--name-status", f"origin/main...{ref}").splitlines() if l]
        code = [f for f in files if not (f.endswith(".md") or TEST_FILE.search(f))]
        if cherry and all(l.startswith("-") for l in cherry):
            kind, why = "건너뜀", "내용이 이미 main 에 있음"
        elif (m := TASK_BRANCH.match(name)) and m.group(1) in done and not m.group(1).startswith("S"):
            kind, why = "건너뜀", f"{m.group(1)} 는 TASKS 에서 이미 완료(후속 보완이면 손으로 확인)"
        elif (r := already_in_main_ratio(ref, files)) and r[1] and r[0] / r[1] >= ALREADY_RATIO:
            kind, why = "건너뜀", f"더한 줄 {r[0]}/{r[1]} 이 main 에 이미 있음(다른 판으로 합쳐짐)"
        elif age_days > 7:
            kind, why = "건너뜀", f"{age_days:.0f}일째 새 커밋 없음(오래됨)"
        elif len(files) == 1 and files[0].startswith("docs/worklog/"):
            kind, why = "건너뜀", "일지 '시작'만"
        elif code:
            kind, why = "코드 바뀜", ", ".join(code[:3]) + (" …" if len(code) > 3 else "")
        else:
            kind, why = "문서·시험만", f"파일 {len(files)}개"
        rows.append({"branch": name, "kind": kind, "why": why, "files": files})
    return rows


def resolve_md_conflicts() -> tuple[bool, str]:
    files = [f for f in out("diff", "--name-only", "--diff-filter=U").splitlines() if f]
    for f in files:
        if not f.endswith(".md"):
            return False, f
    for f in files:
        if f.startswith("docs/worklog/"):
            ours = out("show", f":2:{f}").splitlines()
            theirs = out("show", f":3:{f}").splitlines()
            head = [l for l in ours if not l.startswith("- ")] or [l for l in theirs if not l.startswith("- ")]
            items = list(dict.fromkeys(l for l in ours + theirs if l.startswith("- ")))
            items.sort(key=lambda l: (re.match(r"- (\d{4}-\d{2}-\d{2} \d{2}:\d{2})?", l).group(1) or ""))
            while head and not head[-1].strip():
                head.pop()
            Path(f).write_text("\n".join(head + [""] + items) + "\n", encoding="utf-8")
        else:
            s = Path(f).read_text(encoding="utf-8")
            s = re.sub(r"<<<<<<< [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n",
                       lambda m: m.group(1).rstrip("\n") + "\n\n" + m.group(2), s, flags=re.S)
            if "<<<<<<<" in s:
                return False, f
            Path(f).write_text(s, encoding="utf-8")
        git("add", f)
    return True, ""


def test_dirs(files: list[str]) -> set[str]:
    """바뀐 시험 파일이 든 스킬(또는 루트 tests)."""
    dirs = set()
    for f in files:
        if not TEST_FILE.search(f):
            continue
        p = Path(f)
        if p.parts[0] == "tests":
            dirs.add("tests")
            continue
        # tests 폴더의 부모(스킬 안 하위 폴더일 수 있음)
        parts = list(p.parts)
        if "tests" in parts:
            dirs.add(str(Path(*parts[:parts.index("tests")])))
        elif "test" in parts:
            dirs.add(str(Path(*parts[:parts.index("test")])))
        else:
            dirs.add(str(p.parent))
    return dirs


def run_tests(dirs: set[str]) -> list[tuple[str, str, bool]]:
    results = []
    for d in sorted(dirs):
        js = list(Path(d).rglob("*.test.js"))
        if js:
            r = subprocess.run(["node", "--test", *map(str, js)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            results.append((d, f"node 종료값 {r.returncode}", r.returncode == 0))
        if list(Path(d).rglob("test_*.py")):
            cwd = d if d != "tests" else "."
            target = "tests" if d == "tests" else "."
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", target],
                               cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            last = (r.stdout.strip().splitlines() or ["(출력 없음)"])[-1]
            results.append((d, last, r.returncode in (0, 5)))
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()
    git("fetch", "--quiet", "--prune", "origin")
    rows = classify()
    for k in ("문서·시험만", "코드 바뀜", "건너뜀"):
        sel = [r for r in rows if r["kind"] == k]
        print(f"\n[{k}] {len(sel)}개")
        for r in sel:
            print(f"  {r['branch']:45s} {r['why']}")
    if not a.merge:
        return 0
    merged, held, touched = [], [], []
    for r in [r for r in rows if r["kind"] == "문서·시험만"]:
        m = git("merge", "--no-ff", f"origin/{r['branch']}", "-m", f"merge: {r['branch']}")
        if m.returncode != 0:
            ok, bad = resolve_md_conflicts()
            if not (ok and git("commit", "--no-edit").returncode == 0):
                git("merge", "--abort")
                held.append((r["branch"], bad))
                continue
        merged.append(r["branch"])
        touched += r["files"]
    print(f"\n합침 {len(merged)}개, 보류 {len(held)}개")
    for b, f in held:
        print(f"  보류 {b}: {f}")
    ok_all = True
    for d, msg, ok in run_tests(test_dirs(touched)):
        ok_all &= ok
        print(f"  {'✅' if ok else '❌'} {d}: {msg}")
    cat = subprocess.run([sys.executable, "tools/build_catalog.py", "--check"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok_all &= cat.returncode == 0
    print(f"  {'✅' if cat.returncode == 0 else '❌'} 카탈로그 점검")
    if a.push:
        if not ok_all:
            print("시험·점검 실패가 있어 푸시하지 않았어요. 고친 뒤 git push origin HEAD:main")
            return 1
        git("fetch", "--quiet", "origin")
        git("merge", "--no-edit", "origin/main")
        p = git("push", "origin", "HEAD:main")
        print("푸시 완료" if p.returncode == 0 else f"푸시 실패: {p.stderr.strip()[:200]}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
