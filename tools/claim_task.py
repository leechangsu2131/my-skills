"""일 잡기 — 실행 직전에 같은 일을 누가 하는지 확인하고, 비어 있으면 브랜치·일지 '시작' 줄을 올려 잡는다.
앞 작업자가 멈춘 일(토큰이 끊김 등)이면 그 브랜치를 그대로 받아 이어받는다.

    python tools/claim_task.py --next --name claude-web-173                  # 다음 일을 골라 잡기(멈춘 일 이어받기 먼저)
    python tools/claim_task.py --next --check                                # 무엇을 고를지 보기만
    python tools/claim_task.py T77 --check                                   # 확인만(아무것도 바꾸지 않음)
    python tools/claim_task.py T77 write-lock --name bizcoder-1              # 잡기(멈춘 브랜치가 있으면 이어받기)
    python tools/claim_task.py T31 korean --name gemini-1 --skill admin-s2b-buyer   # 여러 스킬에 걸친 일·상시 일(S)
    python tools/claim_task.py --skills                                       # S8 후보 스킬 순위 보기

--next 순서: 내 일 → 멈춘 일 이어받기 → TASKS '열림' 일(K I G H J E) → 그것도 없으면 **S8**(열린 이슈가 있는 스킬 하나를
맡아 ISSUES 를 고치기) — 수업 비서 묶음 스킬 먼저, 그다음 열린 이슈·최근 커밋이 많은 스킬(교사 요청 2026-11-28: 일이 금방 떨어짐).

종료값: 0 잡음·이어받음(--check 면 잡을 수 있음, 이미 내가 잡은 일이면 이어서) / 1 이미 누가 함·완료·교사 결정 대기·고를 일 없음 / 2 사용법·git 오류

왜: 교사가 여러 작업자에게 같은 일을 "해"라고 할 수 있고, 다른 폴더(따로 받은 저장소)에서 일하면
원격 브랜치를 새로 받지 않아 남이 잡은 일을 못 본다. 2026-11-25~26 T10·T11·T23·T25 가 그렇게 두 번씩 만들어졌다.
또 작업자는 대개 토큰이 떨어져 말없이 멈춘다(2026-11-27 S1 브랜치 둘이 '시작' 한 줄로 몇 시간 멈춤) →
교사가 일을 하나씩 다시 시키지 않아도 다음 작업자가 이어받게 한다(교사 요청 2026-11-27).

보는 것 (모두 바로 앞에서 `git fetch --prune` 한 뒤)
1. 원격 main 의 docs/TASKS.md 상태: `완료`·`교사 결정 대기`·`보류`·`프로젝트 P<n>` 이면 잡지 않음
2. 원격 브랜치 `task/<번호>-…` — `git ls-remote` 로 원격에 직접 묻는다(main 만 받아 오는 복제본에서도 보이게)
3. 이 저장소의 로컬 브랜치 `task/<번호>-…` — 같은 PC 의 다른 작업 폴더(git worktree, tools/start_worker.ps1)가
   아직 안 올린 것도 보인다(작업 폴더끼리 브랜치 목록을 같이 씀)
--skill 을 주면 브랜치 이름에 그 스킬 이름이 든 것만 같은 일로 본다(T31·T33·S1 처럼 스킬마다 따로 잡는 일).

이어받기: 남의 원격 브랜치라도 그 브랜치 일지 마지막 줄이 `그만둠` 이거나, STALE_HOURS(기본 2시간,
환경변수 CLAIM_STALE_HOURS) 넘게 새 커밋이 없으면(마지막 줄이 `시작`·`진행`·`합칠 준비`·`이어받음`) 잡을 수 있다.
`PR 올림`(끝남 — 합치기 기다림)·`막힘`(교사가 풂)은 이어받지 않는다. 이어받을 때는 새 브랜치를 만들지 않고 그 브랜치에
내 일지 `이어받음` 줄을 올린다 — 같은 때 둘이 이어받으면 늦은 쪽은 푸시가 거절돼 ❌.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from functools import lru_cache
from pathlib import Path

STALE_HOURS = float(os.environ.get("CLAIM_STALE_HOURS", "2"))
# 일지 줄의 종류(worklog/README.md). 줄 앞쪽(" — " 앞)에서 가장 먼저 나오는 것으로 정한다.
KINDS = ("이어받음", "PR 올림", "합칠 준비", "그만둠", "막힘", "진행", "시작")
NO_TAKEOVER = {"PR 올림": "끝남 — 합치기를 기다림", "막힘": "막힘 — 교사가 풂"}
DEFAULT_ORDER = ["K", "I", "G", "H", "J", "E"]
# S8: TASKS 에 고를 일이 없을 때 스킬 하나의 열린 이슈를 고치는 일 — 브랜치 task/S8-<스킬>
ISSUE_TASK = "S8"
PUSH_FAILED = 3  # claim_new 안에서만: 못 올려 원래 자리로 돌아감 → --next 는 다음 후보로(밖으로는 1)
BUNDLE = ("teacherlesson-assistant", "util-notebooklm", "teacherlesson-guide", "teacherlesson-schedule",
          "teacherlesson-from-neis")  # TASKS.md 맨 위 ★ 수업 비서 묶음
RECENT_DAYS = 14


class GitError(Exception):
    pass


def git(*args: str, check: bool = True) -> str:
    res = subprocess.run(["git", "-c", "core.quotepath=false", *args], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if check and res.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {res.stderr.strip()}")
    return res.stdout.strip()


def tasks_text() -> str:
    return git("show", "origin/main:docs/TASKS.md", check=False)


def task_status(number: str) -> str | None:
    """원격 main 의 TASKS 표에서 그 번호 줄의 마지막 칸(상태). 줄이 없으면 None."""
    m = re.search(r"^\|\s*" + re.escape(number) + r"\s*\|.*\|\s*([^|\n]*?)\s*\|\s*$", tasks_text(), re.M)
    return m.group(1) if m else None


def blocked_reason(status: str | None) -> str | None:
    if status is None:
        return None
    if "완료" in status:
        return f"TASKS 상태가 '{status}'"
    if "결정 대기" in status:
        return f"TASKS 상태가 '{status}' — 교사 결정이 먼저"
    if "프로젝트" in status:
        return f"TASKS 상태가 '{status}' — 큰 프로젝트를 맡은 작업자가 함"
    if "보류" in status:
        return f"TASKS 상태가 '{status}' — 지금은 하지 않는 일(수업 비서 묶음 밖 등)"
    return None


@lru_cache(maxsize=1)
def remote_task_heads() -> tuple[str, ...]:
    """원격의 task/… 브랜치 이름들. git ls-remote 로 직접 묻고, 내용(일지)을 볼 수 있게 한 번에 받아 둔다.
    main 만 받아 오는 복제본(--single-branch, 웹 작업자 등)은 fetch 해도 남의 task/… 브랜치가 refs/remotes 에
    안 생겨서, 그것만 보면 겹침을 놓친다(2026-11-26 작업자 제보)."""
    heads = []
    for line in git("ls-remote", "--heads", "origin").splitlines():
        ref = line.split("\t")[-1]
        if ref.startswith("refs/heads/task/"):
            heads.append(ref[len("refs/heads/"):])
    if heads:
        git("fetch", "--quiet", "origin", "+refs/heads/task/*:refs/remotes/origin/task/*", check=False)
    return tuple(heads)


def same_task_branches(number: str, skill: str | None) -> list[str]:
    """같은 번호의 원격·로컬 브랜치 이름들(origin/ 은 붙여서)."""
    prefix = re.compile(r"^task/" + re.escape(number) + r"-", re.I)
    # 스킬이 있으면 번호 바로 뒤가 그 스킬 이름이고 그 뒤는 끝이나 '-' — 부분 문자열로 보면
    # exam-grader 가 exam-graderv2 브랜치를, photo-organizer 가 student-photo-organizer 브랜치를 제 것으로 봄(검토 2026-11-28)
    exact = re.compile(r"^task/" + re.escape(number) + "-" + re.escape(skill or "") + r"(?:-|$)", re.I)

    def wanted(short: str) -> bool:
        return bool(exact.match(short)) if skill else bool(prefix.match(short))

    out = ["origin/" + short for short in remote_task_heads() if wanted(short)]
    # 로컬 브랜치: 같은 저장소의 다른 작업 폴더(git worktree)가 아직 안 올린 것도 여기 보인다
    for ref in git("for-each-ref", "--format=%(refname)", "refs/heads/task/").splitlines():
        short = ref[len("refs/heads/"):]
        if wanted(short) and "origin/" + short not in out:
            out.append(short)
    return out


def owner_is_me(branch: str, name: str, number: str) -> bool:
    """그 브랜치를 마지막으로 잡은(`시작`·`이어받음`) 작업자가 나면 내 일.
    내 `시작` 줄이 있어도 그 뒤에 남이 `이어받음` 을 올렸으면 이제 남의 일이다(검토 2026-11-27 — 토큰이 다시 차서
    돌아온 앞 작업자와 이어받은 작업자가 둘 다 '내 일'로 믿고 같은 브랜치를 고치던 문제)."""
    claims = [who for who, line in worklog_lines(branch) if log_kind(line) in ("시작", "이어받음")]
    if claims:
        return claims[-1] == name
    log = git("show", f"{branch}:docs/worklog/{name}.md", check=False)
    return bool(re.search(re.escape(number) + r"\b[^\n]*(시작|이어받음)", log))


def worktree_of(branch: str) -> str | None:
    """로컬 브랜치를 쓰고 있는 작업 폴더."""
    cur = None
    for line in git("worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            cur = line[len("worktree "):]
        elif line == f"branch refs/heads/{branch}":
            return cur
    return None


def log_kind(line: str) -> str:
    head = line.split(" — ")[0]
    found = [(head.find(k), k) for k in KINDS if k in head]
    return min(found)[1] if found else ""


def is_merged(branch: str) -> bool:
    """그 브랜치의 커밋이 모두 원격 main 에 들어 있음."""
    return subprocess.run(["git", "merge-base", "--is-ancestor", branch, "origin/main"],
                          capture_output=True).returncode == 0


def here() -> Path:
    return Path(git("rev-parse", "--show-toplevel")).resolve()


def used_elsewhere(branch: str) -> str | None:
    """같은 이름의 로컬 브랜치를 이 PC 의 다른 작업 폴더가 쓰고 있으면 그 폴더."""
    where = worktree_of(branch.removeprefix("origin/"))
    return where if where and Path(where).resolve() != here() else None


def worklog_lines(branch: str) -> list[tuple[str, str]]:
    """그 브랜치가 스스로 올린 일지 줄들 (작업자, 줄), 오래된 것부터.
    main 을 받아 합친 커밋(merge)은 빼고(남의 일지가 섞임), 이미 main 에 합쳐진 브랜치면 마지막 일지 커밋 하나만."""
    if is_merged(branch):
        return []  # 다 합쳐진 브랜치 — 남은 커밋이 없어 main 의 남의 일지 줄을 읽게 됨(검토 2026-11-27)
    base = git("merge-base", "origin/main", branch, check=False)
    diff = git("log", "--first-parent", "--no-merges", "--reverse", "-p", "--format=", f"{base}..{branch}",
               "--", "docs/worklog/", check=False)
    out, who = [], ""
    for line in diff.splitlines():
        if line.startswith("+++ "):
            m = re.search(r"docs/worklog/(.+)\.md$", line)
            who = m.group(1) if m and m.group(1) != "README" else ""
        elif who and line.startswith(("+- ", "+* ")):
            out.append((who, line[3:].strip()))
    return out


def branch_state(branch: str) -> dict:
    ct = git("log", "-1", "--format=%ct", branch, check=False)
    hours = (time.time() - int(ct)) / 3600 if ct.isdigit() else 0.0
    lines = worklog_lines(branch)
    who, last = lines[-1] if lines else ("", "")
    return {"branch": branch, "hours": hours, "who": who, "last": last, "kind": log_kind(last), "lines": lines,
            "elsewhere": used_elsewhere(branch)}


def takeover_reason(state: dict, limit: float = STALE_HOURS) -> str | None:
    """이어받을 수 있으면 그 까닭, 아니면 None."""
    if not state["branch"].startswith("origin/"):
        return None  # 아직 안 올린 로컬 브랜치 — 받을 수 없음
    if state["kind"] in NO_TAKEOVER or state.get("elsewhere"):
        return None  # 끝남·막힘, 또는 이 PC 의 다른 작업 폴더가 그 브랜치를 쓰는 중
    if state["kind"] == "그만둠":
        return f"앞 작업자({state['who']})가 그만둠"
    if state["hours"] >= limit:
        return f"{state['hours']:.0f}시간 동안 새 커밋 없음({state['who'] or '일지 없음'}, 마지막: {state['kind'] or '?'})"
    return None


def evaluate(number: str, skill: str | None, name: str | None, limit: float) -> dict:
    """잡을 수 있는지 본다(아무것도 바꾸지 않음). action: blocked · busy · mine · takeover · free."""
    why = blocked_reason(task_status(number))
    if why:
        return {"action": "blocked", "why": why}
    found = same_task_branches(number, skill)
    # 이미 main 에 다 합쳐진 원격 브랜치는 끝난 일 — 겹침으로 보지 않는다(이어 할 것이 있으면 새 브랜치로)
    found = [b for b in found if not (b.startswith("origin/") and is_merged(b))]
    mine = [b for b in found if name and owner_is_me(b, name, number)]
    others = [b for b in found if b not in mine]
    if mine:
        return {"action": "mine", "branches": mine}
    if not others:
        return {"action": "free"}
    states = [branch_state(b) for b in others]
    busy = [s for s in states if not takeover_reason(s, limit)]
    if busy:
        return {"action": "busy", "states": busy}
    # 모두 멈춤 — 가장 최근에 손댄 브랜치를 이어받는다(나머지는 오케스트레이터가 정리)
    pick = min(states, key=lambda s: s["hours"])
    return {"action": "takeover", "state": pick, "why": takeover_reason(pick, limit)}


def append_log(name: str, line: str) -> str:
    root = Path(git("rev-parse", "--show-toplevel"))
    log = root / "docs" / "worklog" / f"{name}.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    text = log.read_text(encoding="utf-8") if log.exists() else f"# {name} 일지\n\n"
    if not text.endswith("\n"):
        text += "\n"
    log.write_text(text + f"- {datetime.now():%Y-%m-%d %H:%M} {line}\n", encoding="utf-8")
    return str(log.relative_to(root))


def push(branch: str) -> str | None:
    res = subprocess.run(["git", "push", "--quiet", "-u", "origin", branch], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    return None if res.returncode == 0 else res.stderr.strip()


def claim_new(number: str, skill: str | None, name: str, desc: str) -> int:
    scope = f" ({skill})" if skill else ""
    desc = re.sub(r"[^A-Za-z0-9._-]+", "-", desc).strip("-").lower() or "work"
    if skill and not re.match(re.escape(skill.lower()) + r"(?:-|$)", desc):
        desc = f"{skill.lower()}-{desc}"
    taken = set(remote_task_heads()) | {r[len("refs/heads/"):] for r in
                                        git("for-each-ref", "--format=%(refname)", "refs/heads/task/").splitlines()}
    branch, n = f"task/{number}-{desc}", 2
    while branch in taken:  # 합쳐진 옛 브랜치가 같은 이름이면
        branch, n = f"task/{number}-{desc}-{n}", n + 1
    back = git("symbolic-ref", "--quiet", "--short", "HEAD", check=False) or git("rev-parse", "HEAD")
    git("switch", "--quiet", "-c", branch, "origin/main")
    git("add", append_log(name, f"{number}{scope} 시작 (브랜치 {branch})"))
    git("commit", "--quiet", "-m", f"docs: [worklog] {name} {number}{scope} 시작")
    err = push(branch)
    if err:
        git("checkout", "--quiet", "-f", back, check=False)  # 원래 자리로, 못 올린 브랜치는 지움(검토 2026-11-28)
        git("branch", "--quiet", "-D", branch, check=False)
        print(f"❌ 올리지 못했어요(같은 이름을 누가 먼저 올렸을 수 있음, 원래 자리로 돌아감): {err}")
        return PUSH_FAILED
    # 거의 같은 때 다른 이름으로 잡은 사람이 있는지 한 번 더
    git("fetch", "--quiet", "--prune", "origin")
    remote_task_heads.cache_clear()
    rivals = [b for b in same_task_branches(number, skill) if b not in (branch, "origin/" + branch)
              and not (b.startswith("origin/") and is_merged(b))]
    if rivals:
        print(f"⚠ 잡았지만 거의 같은 때 같은 일을 잡은 브랜치가 있어요: {', '.join(rivals)} → 교사에게 알리세요.")
        return 1
    print(f"✅ {number}{scope} 를 잡았어요: 브랜치 {branch} (일지 '시작' 줄을 올림)")
    return 0


def take_over(number: str, skill: str | None, name: str, state: dict, why: str) -> int:
    scope = f" ({skill})" if skill else ""
    remote = state["branch"]
    short = remote.removeprefix("origin/")
    if state.get("elsewhere"):
        print(f"❌ {short} 는 이 PC 의 다른 작업 폴더({state['elsewhere']})가 쓰고 있어요 — 그 폴더에서 이어서 하세요.")
        return 1
    existed = bool(git("rev-parse", "--verify", "--quiet", f"refs/heads/{short}", check=False))
    if existed and git("rev-list", "--count", f"{remote}..{short}") != "0":
        print(f"❌ 로컬 {short} 에 원격에 없는 커밋이 있어요 — 먼저 정리하세요(남의 일이 섞이지 않게).")
        return 2
    back = git("symbolic-ref", "--quiet", "--short", "HEAD", check=False) or git("rev-parse", "HEAD")

    def undo() -> None:
        """원래 자리로 — 남의 일지가 스테이징된 채 남지 않게(검토 2026-11-27)."""
        git("checkout", "--quiet", "-f", back, check=False)
        if not existed:
            git("branch", "--quiet", "-D", short, check=False)

    try:
        if existed:
            git("switch", "--quiet", short)
            git("merge", "--quiet", "--ff-only", remote)
        else:
            # --track 은 쓰지 않는다: main 만 받는 복제본(--single-branch)은 origin/task/… 를 추적 브랜치로 안 쳐서
            # 실패한다(검토 2026-11-27 재현). 올릴 곳은 아래 push -u 가 정한다.
            git("switch", "--quiet", "-c", short, remote)
        prev = f"{state['who']}: {state['last'][:80]}" if state["last"] else "일지 없음"
        git("add", append_log(name, f"{number}{scope} 이어받음 (브랜치 {short}, 앞 — {prev})"))
        git("commit", "--quiet", "-m", f"docs: [worklog] {name} {number}{scope} 이어받음")
    except GitError as e:
        undo()
        print(f"❌ 이어받지 못했어요(git 오류, 원래 자리로 돌아감): {e}")
        return 2
    err = push(short)
    if err:
        undo()
        if re.search(r"rejected|non-fast-forward|fetch first", err):
            print(f"❌ 그새 누가 이 브랜치에 올렸어요(앞 작업자가 다시 왔거나 다른 작업자가 먼저 이어받음): {err}")
            return 1
        print(f"❌ 올리지 못했어요(인터넷·권한 등, 원래 자리로 돌아감): {err}")
        return 2
    print(f"✅ {number}{scope} 를 이어받았어요: 브랜치 {short} ({why})")
    print("   앞 작업자가 남긴 일지(어디까지 했고 다음에 무엇을 할지) — 여기서부터 이어서 하세요:")
    for who, line in state["lines"][-6:]:
        print(f"   - {who}: {line}")
    behind = git("rev-list", "--count", f"{short}..origin/main", check=False)
    if behind.isdigit() and int(behind) > 20:
        print(f"   (main 보다 {behind}커밋 뒤처짐 — 고치기 전에 `git merge origin/main` 으로 맞추세요)")
    print("   TASKS 의 '끝난 기준'·체크리스트에서 안 된 것부터 하고, 단계마다 커밋·푸시·일지 `진행` 줄을 남기세요.")
    return 0


def next_candidates(grade: str) -> list[str]:
    """TASKS 에서 고를 순서대로 '열림' T 번호들. 순서는 TASKS 의 `고르는 순서(claim_task.py --next): K I …` 줄."""
    text = tasks_text()
    m = re.search(r"고르는 순서\(claim_task\.py --next\)\s*:\s*([A-Z](?:[\s,→]+[A-Z])*)", text)
    order = re.findall(r"[A-Z]", m.group(1)) if m else DEFAULT_ORDER
    by_section: dict[str, list[str]] = {}
    section = None
    for line in text.splitlines():
        if line.startswith("## "):
            sm = re.match(r"##\s+([A-Z])\.", line)
            section = sm.group(1) if sm else None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if section is None or len(cells) < 3 or not re.fullmatch(r"T\d{1,3}", cells[0]):
            continue
        status = cells[-1]
        gm = re.match(r"\s*([RP])\s*·", status)
        need = gm.group(1) if gm else "R"
        if blocked_reason(status) or not ("열림" in status or "진행" in status):
            continue
        if grade == "R" and need == "P":
            continue
        by_section.setdefault(section, []).append(cells[0])
    return [n for s in order for n in by_section.get(s, [])]


def show_busy(number: str, skill: str | None, states: list[dict]) -> None:
    print(f"❌ {number}{' (' + skill + ')' if skill else ''} 는 이미 누가 하고 있어요:")
    for s in states:
        b = s["branch"]
        where = worktree_of(b) if not b.startswith("origin/") else None
        last = git("log", "-1", "--format=%an, %ad", "--date=format:%m-%d %H:%M", b, check=False)
        note = f"일지 '{s['kind']}'" if s["kind"] else ""
        if s.get("elsewhere"):
            note += f"{', ' if note else ''}이 PC 의 다른 작업 폴더가 씀"
        elif s["kind"] == "이어받음":
            note += f"{', ' if note else ''}{s['who']} 가 이어받음 — 앞 작업자라도 이제 남의 일"
        if s["kind"] not in NO_TAKEOVER and b.startswith("origin/"):
            note += f"{', ' if note else ''}{s['hours']:.1f}시간 전 — {STALE_HOURS:g}시간 넘게 멈추면 이어받을 수 있음"
        print(f"   {b}  ({last}{', 작업 폴더 ' + where if where else ''}{'; ' + note if note else ''})")


def rank_skills() -> list[dict]:
    """S8 후보: 원격 main 에서 열린 이슈(🔵 진행 중·📌 백로그의 `###` 항목)가 있는 스킬.
    수업 비서 묶음이 먼저, 그다음 점수(열린 이슈 ×2 + 최근 RECENT_DAYS 일 커밋 수, 최대 10) 순. 보관 스킬은 뺀다."""
    open_issues: dict[str, int] = {}
    section_open: dict[str, bool] = {}
    out = git("grep", "-n", "-e", "^## ", "-e", "^### ", "origin/main", "--", "skills/*/ISSUES.md", check=False)
    for line in out.splitlines():
        m = re.match(r"^origin/main:skills/([^/]+)/ISSUES\.md:\d+:(.*)$", line)
        if not m:
            continue
        skill, text = m.groups()
        if text.startswith("## "):
            section_open[skill] = bool(re.search(r"🔵|📌|진행 중|백로그", text)) and "🟢" not in text
        elif section_open.get(skill) and re.match(r"###\s+[A-Z][A-Za-z]*-\S", text):
            # `### 📄 기존 ing.md 내용` 같은 옮김 제목은 세지 않음(검토 2026-11-28)
            open_issues[skill] = open_issues.get(skill, 0) + 1
    shelved = set()
    for line in git("grep", "-n", "-e", "status:", "origin/main", "--", "skills/*/SKILL.md", check=False).splitlines():
        m = re.match(r"^origin/main:skills/([^/]+)/SKILL\.md:\d+:\s*status:\s*(\S+)", line)
        if m and m.group(2).startswith("보관"):
            shelved.add(m.group(1))
    recent: dict[str, set] = {}
    log = git("log", "origin/main", f"--since={RECENT_DAYS}.days.ago", "--format=@%H", "--name-only", "--", "skills/",
              check=False)
    sha = ""
    for line in log.splitlines():
        if line.startswith("@"):
            sha = line[1:]
        elif line.startswith("skills/"):
            recent.setdefault(line.split("/")[1], set()).add(sha)
    ranked = []
    for skill, n in open_issues.items():
        if skill in shelved or skill.startswith("_"):
            continue
        c = len(recent.get(skill, ()))
        ranked.append({"skill": skill, "issues": n, "recent": c, "bundle": skill in BUNDLE,
                       "score": n * 2 + min(c, 10)})
    ranked.sort(key=lambda r: (not r["bundle"], -r["score"], r["skill"]))
    return ranked


def _pick(a, plans: list, kinds=("mine", "takeover", "free")) -> int | None:
    """plans: [((번호, 스킬), evaluate 결과)]. 잡았거나 이미 내 일이면 종료값, 고를 게 없으면 None."""
    for kind in kinds:
        for (n, skill), ev in plans:
            if ev["action"] != kind:
                continue
            label = f"{n} ({skill})" if skill else n
            if kind == "mine":
                print(f"✅ {label} 는 이미 {a.name} 가 잡은 일이에요(이어서 하세요): {', '.join(ev['branches'])}")
                return 0
            if a.check:
                what = f"이어받기 — {ev['why']}" if kind == "takeover" else "새로 잡기"
                print(f"✅ 다음 일: {label} ({what})")
                return 0
            if git("status", "--porcelain"):
                print("❌ 이 작업 폴더에 커밋 안 한 변경이 있어요. 정리한 뒤 다시 잡으세요(남의 변경이 섞이지 않게).")
                return 2
            if kind == "takeover":
                if take_over(n, skill, a.name, ev["state"], ev["why"]) == 0:
                    return 0
                print(f"   → {label} 는 건너뛰고 다음 후보를 봐요.")
                continue
            r = claim_new(n, skill, a.name, skill or a.desc or "work")
            if r == PUSH_FAILED:
                print(f"   → {label} 는 건너뛰고 다음 후보를 봐요.")
                continue
            return r
    return None


def my_issue_branches(name: str | None) -> list[str]:
    """내가 마지막으로 잡은(시작·이어받음) S8 브랜치 — 순위가 바뀌어도 '내 일'로 먼저 찾게."""
    if not name:
        return []
    return [b for b in same_task_branches(ISSUE_TASK, None)
            if not (b.startswith("origin/") and is_merged(b)) and owner_is_me(b, name, ISSUE_TASK)]


def run_next(a) -> int:
    t_plans = [((n, None), evaluate(n, None, a.name, a.stale_hours)) for n in next_candidates(a.grade)]
    # 1) 내 일 — T 든 S8 이든 먼저(내 S8 을 두고 새 T 일을 잡지 않게, 검토 2026-11-28)
    r = _pick(a, t_plans, ("mine",))
    if r is not None:
        return r
    mine8 = my_issue_branches(a.name)
    if mine8:
        print(f"✅ {ISSUE_TASK} 는 이미 {a.name} 가 잡은 일이에요(이어서 하세요): {', '.join(mine8)}")
        return 0
    # 2) TASKS 일: 멈춘 일 이어받기 → 새로 잡기
    r = _pick(a, t_plans, ("takeover", "free"))
    if r is not None:
        return r
    # 3) S8 — 순위대로 하나씩 평가(첫 후보가 비면 바로 잡음)
    ranked = rank_skills()[:12]
    if ranked:
        print(f"TASKS 에 고를 '열림' 일이 없어요 → {ISSUE_TASK}: 열린 이슈가 있는 스킬 하나를 맡아요"
              "(수업 비서 묶음 먼저, 그다음 열린 이슈·최근 커밋이 많은 스킬).")
        for x in ranked:
            plan = [((ISSUE_TASK, x["skill"]), evaluate(ISSUE_TASK, x["skill"], a.name, a.stale_hours))]
            r = _pick(a, plan, ("takeover", "free"))
            if r is not None:
                return r
    print("고를 일이 없어요 → TASKS 맨 아래 상시 일(S)을 하세요. 예:")
    print(f"   python tools/claim_task.py S1 <짧은-영어-설명> --name {a.name or '<내 이름>'} --skill <스킬 이름>")
    return 1


def show_skills() -> int:
    ranked = rank_skills()
    print(f"S8 후보 스킬(열린 이슈 · 최근 {RECENT_DAYS}일 커밋) — 위에서부터 고름")
    for i, x in enumerate(ranked, 1):
        print(f"{i:>2}. {'★ ' if x['bundle'] else '  '}{x['skill']}  이슈 {x['issues']} · 커밋 {x['recent']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("number", nargs="?", help="TASKS 번호(예: T77, S1). --next 면 비움")
    ap.add_argument("desc", nargs="?", help="브랜치 이름 뒷부분(짧은 영어, 예: write-lock)")
    ap.add_argument("--name", help="작업자 이름(일지 파일 이름) — 잡을 때 필요")
    ap.add_argument("--skill", help="스킬마다 따로 잡는 일이면 스킬 이름")
    ap.add_argument("--check", action="store_true", help="확인만")
    ap.add_argument("--next", action="store_true", help="다음 일을 골라 잡기: 내 일 → 멈춘 일 이어받기 → 열림 일")
    ap.add_argument("--grade", choices=["R", "P"], default="R", help="내 등급(P: 교사 PC 작업자 — P 일도 고름)")
    ap.add_argument("--stale-hours", type=float, default=STALE_HOURS, help="몇 시간 새 커밋이 없으면 이어받을지")
    ap.add_argument("--skills", action="store_true", help="S8 후보 스킬 순위만 보기")
    a = ap.parse_args(argv)
    try:  # tools/·docs/ 에서 돌려도 pathspec(skills/*, docs/worklog/)이 맞게 저장소 맨 위로(검토 2026-11-28)
        os.chdir(git("rev-parse", "--show-toplevel"))
    except GitError as e:
        print(f"❌ git 저장소 안에서 돌려 주세요: {e}")
        return 2
    if a.skills:
        git("fetch", "--quiet", "origin", check=False)
        return show_skills()
    if a.name:
        a.name = re.sub(r"\s+", "", a.name).strip("[]")  # 지침 첫 줄 '[claude-web- 173]' 처럼 띄어쓰기·대괄호가 섞여도 같은 일지 파일로

    if a.next:
        if a.number and not a.desc:  # `--next work` 처럼 설명만 준 경우
            a.desc, a.number = a.number, None
        if not a.check and not a.name:
            print("--next 로 잡으려면 --name 이 필요해요. 보기만 하려면 --check.")
            return 2
        try:
            git("fetch", "--quiet", "--prune", "origin")
            return run_next(a)
        except GitError as e:
            print(f"❌ git 오류: {e}")
            return 2

    number = (a.number or "").upper()
    if not re.fullmatch(r"[TS]\d{1,3}", number):
        print(f"번호 모양이 아니에요: {a.number} (예: T77, S1 — 다음 일을 고르게 하려면 --next)")
        return 2
    if number.startswith("S") and not a.skill:
        print("상시 일(S)은 --skill <스킬 이름> 으로 무엇을 하는지 정해야 해요(겹침 확인용).")
        return 2
    if not a.check and not (a.desc and a.name):
        print("잡으려면 브랜치 설명과 --name 이 필요해요. 확인만 하려면 --check.")
        return 2

    try:
        git("fetch", "--quiet", "--prune", "origin")
        ev = evaluate(number, a.skill, a.name, a.stale_hours)
        scope = f" ({a.skill})" if a.skill else ""
        if ev["action"] == "blocked":
            print(f"❌ {number} 는 잡지 않아요: {ev['why']}")
            return 1
        if ev["action"] == "busy":
            show_busy(number, a.skill, ev["states"])
            print("→ 시작하지 말고 다른 일을 고르세요(`python tools/claim_task.py --next --name <내 이름>`).")
            return 1
        if ev["action"] == "mine":
            print(f"✅ {number} 는 이미 {a.name} 가 잡은 일이에요(이어서 하세요): {', '.join(ev['branches'])}")
            return 0
        if a.check:
            if ev["action"] == "takeover":
                print(f"✅ {number}{scope} 는 이어받을 수 있어요: {ev['state']['branch']} ({ev['why']})")
            else:
                print(f"✅ {number}{scope} 는 비어 있어요.")
            return 0
        if git("status", "--porcelain"):
            print("❌ 이 작업 폴더에 커밋 안 한 변경이 있어요. 정리한 뒤 다시 잡으세요(남의 변경이 섞이지 않게).")
            return 2
        if ev["action"] == "takeover":
            return take_over(number, a.skill, a.name, ev["state"], ev["why"])
        r = claim_new(number, a.skill, a.name, a.desc)
        return 1 if r == PUSH_FAILED else r
    except GitError as e:
        print(f"❌ git 오류: {e}")
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # 윈도우 까만 창에서 한글이 깨지지 않게
    sys.exit(main())
