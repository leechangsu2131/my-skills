"""tools/claim_task.py 시험 — 임시 폴더에 가짜 원격 저장소와 작업 폴더를 만들어 git 으로 실제로 돌린다(네트워크 없음)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "claim_task.py"

TASKS = """# 할 일

> 고르는 순서(claim_task.py --next): K I

## K. 큰 일

| 번호 | 할 일 | 상태 |
|---|---|---|
| T98 | 큰 일 | R · 열림 |
| T99 | 교사 PC 일 | P · 열림 |

## B. 순서 밖

| 번호 | 할 일 | 상태 |
|---|---|---|
| T80 | 순서 밖 | 열림 |

## I. 다음 일

| 번호 | 할 일 | 상태 |
|---|---|---|
| T77 | 잠금 | 열림 |
| T78 | 검사 | 완료(2026-11-26 합침) |
| T79 | 진도 | 교사 결정 대기 |
| T31 | 한국어로 | 열림 |
| T54 | 기록 문장 | 보류(묶음 밖) |
| T70 | 교실 도구 | 프로젝트 P1(ag-1) |
"""

ENV = {**os.environ, "GIT_AUTHOR_NAME": "시험", "GIT_AUTHOR_EMAIL": "t@example.invalid",
       "GIT_COMMITTER_NAME": "시험", "GIT_COMMITTER_EMAIL": "t@example.invalid", "PYTHONIOENCODING": "utf-8"}


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), cwd=cwd, env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace")


def g(cwd: Path, *args: str) -> str:
    r = run(cwd, "git", *args)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def claim(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return run(cwd, sys.executable, str(TOOL), *args)


@pytest.fixture()
def repos(tmp_path):
    """origin(빈 저장소) + 작업자 A·B 의 따로 받은 저장소 + A 의 같은 PC 작업 폴더(worktree)."""
    origin = tmp_path / "origin.git"
    g(tmp_path, "init", "--bare", "-b", "main", str(origin))
    seed = tmp_path / "seed"
    g(tmp_path, "clone", "-q", str(origin), str(seed))
    (seed / "docs" / "worklog").mkdir(parents=True)
    (seed / "docs" / "TASKS.md").write_text(TASKS, encoding="utf-8")
    (seed / "docs" / "worklog" / "README.md").write_text("# 일지\n", encoding="utf-8")
    g(seed, "add", ".")
    g(seed, "commit", "-q", "-m", "init")
    g(seed, "push", "-q", "origin", "HEAD:main")
    a, b = tmp_path / "a", tmp_path / "b"
    g(tmp_path, "clone", "-q", str(origin), str(a))
    g(tmp_path, "clone", "-q", str(origin), str(b))
    a2 = tmp_path / "a2"
    g(a, "worktree", "add", "-q", "--detach", str(a2), "origin/main")
    return {"origin": origin, "a": a, "b": b, "a2": a2}


def test_empty_task_check_is_free_and_changes_nothing(repos):
    r = claim(repos["a"], "T77", "--check")
    assert r.returncode == 0, r.stdout
    assert "비어 있어요" in r.stdout
    assert g(repos["a"], "ls-remote", "--heads", "origin") .count("task/") == 0


def test_claim_pushes_branch_and_worklog_start_line(repos):
    r = claim(repos["a"], "T77", "write-lock", "--name", "bizcoder-1")
    assert r.returncode == 0, r.stdout
    assert "refs/heads/task/T77-write-lock" in g(repos["a"], "ls-remote", "--heads", "origin")
    log = g(repos["a"], "show", "origin/task/T77-write-lock:docs/worklog/bizcoder-1.md")
    assert "T77 시작 (브랜치 task/T77-write-lock)" in log


@pytest.mark.parametrize("given, file", [("[claude-web- 173]", "claude-web-173"),
                                         ("[claude-web-lee2131@hanmail]", "claude-web-lee2131@hanmail")])
def test_name_with_space_or_brackets_uses_same_worklog(repos, given, file):
    """지침 첫 줄 대괄호 안 글자는 모양이 어떻든 이름 — 띄어쓰기·대괄호만 뺀다."""
    r = claim(repos["a"], "T77", "write-lock", "--name", given)
    assert r.returncode == 0, r.stdout
    log = g(repos["a"], "show", f"origin/task/T77-write-lock:docs/worklog/{file}.md")
    assert "T77 시작" in log


def test_other_clone_sees_claim_even_with_stale_refs(repos):
    """B 는 따로 받은 저장소라 아무것도 받지 않은 상태 — 도구가 먼저 fetch 해서 A 의 브랜치를 본다(11-25 겹침 사례)."""
    assert claim(repos["a"], "T77", "write-lock", "--name", "bizcoder-1").returncode == 0
    r = claim(repos["b"], "T77", "lock-all", "--name", "claude-local-1")
    assert r.returncode == 1, r.stdout
    assert "이미 누가" in r.stdout and "task/T77-write-lock" in r.stdout
    assert "task/T77-lock-all" not in g(repos["b"], "branch", "--list")


def test_single_branch_clone_still_sees_other_branches(tmp_path, repos):
    """main 만 받아 오는 복제본(--single-branch, 웹 작업자 등) — fetch 로는 남의 task 브랜치가 안 보여도 ls-remote 로 본다."""
    assert claim(repos["a"], "T77", "write-lock", "--name", "bizcoder-1").returncode == 0
    c = tmp_path / "c"
    g(tmp_path, "clone", "-q", "--single-branch", "-b", "main", str(repos["origin"]), str(c))
    g(c, "fetch", "-q", "--prune", "origin")
    assert "task/T77" not in g(c, "branch", "-r")  # 이 복제본의 fetch 로는 안 보임(제보된 상황)
    r = claim(c, "T77", "--check")
    assert r.returncode == 1, r.stdout
    assert "task/T77-write-lock" in r.stdout


def test_unpushed_branch_in_another_worktree_counts(repos):
    """같은 PC 의 다른 작업 폴더가 아직 안 올린 브랜치도 보인다."""
    g(repos["a2"], "switch", "-q", "-c", "task/T77-local-only")
    r = claim(repos["a"], "T77", "--check")
    assert r.returncode == 1, r.stdout
    assert "task/T77-local-only" in r.stdout and str(repos["a2"].name) in r.stdout


def test_done_or_waiting_for_teacher_is_not_claimed(repos):
    assert claim(repos["a"], "T78", "x", "--name", "w").returncode == 1
    r = claim(repos["a"], "T79", "x", "--name", "w")
    assert r.returncode == 1 and "결정" in r.stdout
    r = claim(repos["a"], "T54", "x", "--name", "w")
    assert r.returncode == 1 and "보류" in r.stdout
    r = claim(repos["a"], "T70", "x", "--name", "w")
    assert r.returncode == 1 and "프로젝트" in r.stdout


def test_same_worker_rerun_continues(repos):
    assert claim(repos["a"], "T77", "write-lock", "--name", "bizcoder-1").returncode == 0
    r = claim(repos["a"], "T77", "write-lock", "--name", "bizcoder-1")
    assert r.returncode == 0 and "이어서" in r.stdout


def test_skill_scoped_tasks_do_not_block_each_other(repos):
    assert claim(repos["a"], "T31", "s2b-buyer-korean", "--name", "w1", "--skill", "s2b-buyer").returncode == 0
    assert claim(repos["b"], "T31", "--check", "--skill", "iscream").returncode == 0
    assert claim(repos["b"], "T31", "--check", "--skill", "s2b-buyer").returncode == 1


def test_standing_task_needs_skill(repos):
    assert claim(repos["a"], "S1", "--check").returncode == 2


def test_dirty_worktree_is_refused(repos):
    (repos["a"] / "scratch.txt").write_text("x", encoding="utf-8")
    r = claim(repos["a"], "T77", "write-lock", "--name", "w")
    assert r.returncode == 2 and "커밋 안 한" in r.stdout


# --- 이어받기·--next (2026-11-27: 토큰이 끊겨 말없이 멈춘 일을 다른 작업자가 이어받게) ---

OLD = "2026-01-01T09:00:00+09:00"


def make_branch(repo: Path, branch: str, who: str, line: str, date: str | None = None) -> None:
    """남의 작업 브랜치를 손으로 만든다 — date 를 주면 그때 커밋한 것처럼(멈춘 브랜치)."""
    g(repo, "fetch", "-q", "origin")
    g(repo, "switch", "-q", "-c", branch, "origin/main")
    log = repo / "docs" / "worklog" / f"{who}.md"
    log.write_text(f"# {who} 일지\n\n- 2026-01-01 09:00 {line}\n", encoding="utf-8")
    g(repo, "add", ".")
    env = {**ENV, **({"GIT_COMMITTER_DATE": date, "GIT_AUTHOR_DATE": date} if date else {})}
    r = subprocess.run(["git", "commit", "-q", "-m", f"docs: {who}"], cwd=repo, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    g(repo, "push", "-q", "-u", "origin", branch)
    g(repo, "switch", "-q", "--detach", "origin/main")


def test_stale_branch_is_taken_over_on_same_branch(repos):
    make_branch(repos["a"], "task/T77-write-lock", "claude-web-1", "T77 진행 — 잠금 함수까지, 다음: 시험", OLD)
    r = claim(repos["b"], "T77", "other-name", "--name", "claude-web-2")
    assert r.returncode == 0, r.stdout
    assert "이어받았어요" in r.stdout and "잠금 함수까지" in r.stdout
    assert "task/T77-other-name" not in g(repos["b"], "ls-remote", "--heads", "origin")  # 새 브랜치 안 만듦
    log = g(repos["b"], "show", "origin/task/T77-write-lock:docs/worklog/claude-web-2.md")
    assert "T77 이어받음 (브랜치 task/T77-write-lock" in log and "claude-web-1" in log
    # 이어받은 뒤에는 그 작업자가 주인 — 다시 돌리면 '이어서'
    assert "이어서" in claim(repos["b"], "T77", "x", "--name", "claude-web-2").stdout


def test_fresh_branch_is_not_taken_over(repos):
    make_branch(repos["a"], "task/T77-write-lock", "claude-web-1", "T77 시작 (브랜치 task/T77-write-lock)")
    r = claim(repos["b"], "T77", "--check")
    assert r.returncode == 1 and "이어받을 수 있음" in r.stdout


def test_quit_line_is_taken_over_right_away(repos):
    make_branch(repos["a"], "task/T77-write-lock", "claude-web-1", "T77 그만둠 — 사용량 끝, 다음: 시험 2개")
    r = claim(repos["b"], "T77", "--check")
    assert r.returncode == 0 and "이어받을 수 있어요" in r.stdout


@pytest.mark.parametrize("line", ["T77 PR 올림 — 다 했음", "T77 막힘 — 교사 PC 필요"])
def test_done_or_stuck_is_not_taken_over_even_when_old(repos, line):
    make_branch(repos["a"], "task/T77-write-lock", "claude-web-1", line, OLD)
    assert claim(repos["b"], "T77", "--check").returncode == 1


def test_second_taker_sees_first_takeover(repos, tmp_path):
    make_branch(repos["a"], "task/T77-write-lock", "claude-web-1", "T77 시작", OLD)
    assert claim(repos["b"], "T77", "x", "--name", "w2").returncode == 0
    c = tmp_path / "c"
    g(tmp_path, "clone", "-q", str(repos["origin"]), str(c))
    r = claim(c, "T77", "x", "--name", "w3")
    assert r.returncode == 1 and "이미 누가" in r.stdout


def test_next_picks_takeover_before_new_work(repos):
    make_branch(repos["a"], "task/T77-write-lock", "claude-web-1", "T77 진행 — 반쯤", OLD)
    r = claim(repos["b"], "--next", "--check")
    assert r.returncode == 0 and "T77" in r.stdout and "이어받기" in r.stdout
    assert "task/T98" not in g(repos["b"], "ls-remote", "--heads", "origin")  # --check 는 아무것도 안 바꿈
    r = claim(repos["b"], "--next", "--name", "w2")
    assert r.returncode == 0 and "이어받았어요" in r.stdout


def test_next_follows_section_order_and_grade(repos):
    r = claim(repos["b"], "--next", "--name", "w2")
    assert r.returncode == 0 and "T98" in r.stdout  # K 가 I 보다 먼저
    assert "refs/heads/task/T98-work" in g(repos["b"], "ls-remote", "--heads", "origin")
    # 사람이 바뀌면(T98 은 방금 잡혀 바쁨) R 은 P 일(T99)을 건너뛰고 I 의 T77, P 는 T99
    assert "T77" in claim(repos["a"], "--next", "--check").stdout
    assert "T99" in claim(repos["a"], "--next", "--check", "--grade", "P").stdout


def test_next_never_picks_sections_outside_order_or_standing(repos):
    for n in ("T98", "T77", "T31"):
        make_branch(repos["a"], f"task/{n}-busy", "w1", f"{n} 시작")
    r = claim(repos["b"], "--next", "--name", "w2")
    assert r.returncode == 1 and "상시 일" in r.stdout and "T80" not in r.stdout


# --- 검토(2026-11-27)에서 나온 경우 ---

def test_takeover_works_in_single_branch_clone(tmp_path, repos):
    """main 만 받는 복제본에서도 이어받기가 되고, 실패해도 남의 일지가 스테이징된 채 남지 않는다."""
    make_branch(repos["a"], "task/T77-write-lock", "claude-web-1", "T77 진행 — 반쯤", OLD)
    c = tmp_path / "c"
    g(tmp_path, "clone", "-q", "--single-branch", "-b", "main", str(repos["origin"]), str(c))
    r = claim(c, "T77", "x", "--name", "w3")
    assert r.returncode == 0, r.stdout
    assert "이어받았어요" in r.stdout
    assert g(c, "status", "--porcelain") == ""


def test_returning_first_worker_is_not_owner_after_takeover(repos, tmp_path):
    make_branch(repos["a"], "task/T77-write-lock", "claude-web-1", "T77 시작 (브랜치 task/T77-write-lock)", OLD)
    assert claim(repos["b"], "T77", "x", "--name", "w2").returncode == 0
    r = claim(repos["a"], "T77", "x", "--name", "claude-web-1")
    assert r.returncode == 1, r.stdout
    assert "w2 가 이어받음" in r.stdout


def test_merged_branch_does_not_block_or_get_taken_over(repos):
    make_branch(repos["a"], "task/T77-work", "claude-web-1", "T77 그만둠 — 절반 합침", OLD)
    g(repos["a"], "push", "-q", "origin", "origin/task/T77-work:refs/heads/main")  # main 에 다 합쳐짐(ff)
    r = claim(repos["b"], "T77", "work", "--name", "w2")
    assert r.returncode == 0, r.stdout
    assert "잡았어요" in r.stdout and "task/T77-work-2" in r.stdout  # 같은 이름이 있어 -2


def test_next_skips_failed_takeover(repos):
    """이 PC 의 다른 작업 폴더가 쓰는 멈춘 브랜치는 이어받기 후보가 아니다 → 다음 일로."""
    make_branch(repos["a"], "task/T98-big", "claude-web-1", "T98 진행", OLD)
    g(repos["a2"], "switch", "-q", "task/T98-big")  # a 와 a2 는 브랜치 목록을 같이 씀 — 같은 PC 의 다른 작업 폴더가 그 브랜치를 씀
    r = claim(repos["a"], "--next", "--check")
    assert r.returncode == 0 and "T99" not in r.stdout and "T77" in r.stdout, r.stdout


# --- S8: TASKS 에 고를 일이 없으면 열린 이슈가 있는 스킬을 맡음(교사 요청 2026-11-28) ---

DONE_TASKS = """# 할 일

> 고르는 순서(claim_task.py --next): K

## K. 큰 일

| 번호 | 할 일 | 상태 |
|---|---|---|
| T98 | 끝난 일 | R · 완료 |

## S. 상시 일

| 번호 | 할 일 | 등급 |
|---|---|---|
| S8 | 스킬 하나의 열린 이슈 고치기 | R |
"""


def issues(open_n: int, solved_n: int = 1) -> str:
    body = "# 이슈\n\n## 🔵 진행 중\n\n" + "".join(f"### ISSUE-{i:03d}: 열림 {i}\n- 할 일\n\n" for i in range(1, open_n + 1))
    body += "## 📌 백로그\n\n_없음_\n\n## 🟢 해결됨\n\n"
    return body + "".join(f"### ISSUE-{100 + i}: 끝남\n" for i in range(solved_n))


@pytest.fixture()
def issue_repos(tmp_path):
    origin = tmp_path / "origin.git"
    g(tmp_path, "init", "--bare", "-b", "main", str(origin))
    seed = tmp_path / "seed"
    g(tmp_path, "clone", "-q", str(origin), str(seed))
    (seed / "docs" / "worklog").mkdir(parents=True)
    (seed / "docs" / "TASKS.md").write_text(DONE_TASKS, encoding="utf-8")
    (seed / "docs" / "worklog" / "README.md").write_text("# 일지\n", encoding="utf-8")
    for skill, n, status in [("teacherlesson-assistant", 1, "개발"), ("admin-a", 3, "운영"),
                             ("admin-b", 0, "운영"), ("old-thing", 5, "보관")]:
        d = seed / "skills" / skill
        d.mkdir(parents=True)
        (d / "ISSUES.md").write_text(issues(n), encoding="utf-8")
        (d / "SKILL.md").write_text(f"---\nname: {skill}\nmetadata:\n  status: {status}\n---\n", encoding="utf-8")
    g(seed, "add", ".")
    g(seed, "commit", "-q", "-m", "init")
    g(seed, "push", "-q", "origin", "HEAD:main")
    a, b = tmp_path / "a", tmp_path / "b"
    g(tmp_path, "clone", "-q", str(origin), str(a))
    g(tmp_path, "clone", "-q", str(origin), str(b))
    return {"a": a, "b": b}


def test_skills_ranking_bundle_first_skips_solved_and_shelved(issue_repos):
    r = claim(issue_repos["a"], "--skills")
    assert r.returncode == 0, r.stdout
    lines = [l for l in r.stdout.splitlines() if l[:3].strip().rstrip(".").isdigit()]
    assert "teacherlesson-assistant" in lines[0] and "admin-a" in lines[1] and len(lines) == 2, r.stdout


def test_next_falls_back_to_s8_and_spreads_workers(issue_repos):
    r = claim(issue_repos["a"], "--next", "--name", "w1")
    assert r.returncode == 0 and "S8 (teacherlesson-assistant)" in r.stdout, r.stdout
    assert g(issue_repos["a"], "branch", "--show-current") == "task/S8-teacherlesson-assistant"
    r = claim(issue_repos["b"], "--next", "--name", "w2")  # 앞 스킬은 w1 이 막 잡음 → 다음 스킬
    assert r.returncode == 0 and "S8 (admin-a)" in r.stdout, r.stdout
    r = claim(issue_repos["a"], "--next", "--check", "--name", "w1")  # 다시 물으면 내 일
    assert "이미 w1 가 잡은 일" in r.stdout, r.stdout
