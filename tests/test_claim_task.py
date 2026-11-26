"""tools/claim_task.py 시험 — 임시 폴더에 가짜 원격 저장소와 작업 폴더를 만들어 git 으로 실제로 돌린다(네트워크 없음)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "claim_task.py"

TASKS = """# 할 일

| 번호 | 할 일 | 상태 |
|---|---|---|
| T77 | 잠금 | 열림 |
| T78 | 검사 | 완료(2026-11-26 합침) |
| T79 | 진도 | 교사 결정 대기 |
| T31 | 한국어로 | 열림 |
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


def test_other_clone_sees_claim_even_with_stale_refs(repos):
    """B 는 따로 받은 저장소라 아무것도 받지 않은 상태 — 도구가 먼저 fetch 해서 A 의 브랜치를 본다(11-25 겹침 사례)."""
    assert claim(repos["a"], "T77", "write-lock", "--name", "bizcoder-1").returncode == 0
    r = claim(repos["b"], "T77", "lock-all", "--name", "claude-local-1")
    assert r.returncode == 1, r.stdout
    assert "이미 누가" in r.stdout and "task/T77-write-lock" in r.stdout
    assert "task/T77-lock-all" not in g(repos["b"], "branch", "--list")


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
