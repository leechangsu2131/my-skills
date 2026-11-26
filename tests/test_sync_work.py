"""tools/sync_work.py 시험 — 임시 폴더에 가짜 원격 저장소를 만들어 git 으로 실제로 돌린다(네트워크 없음)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "sync_work.py"
ENV = {**os.environ, "GIT_AUTHOR_NAME": "시험", "GIT_AUTHOR_EMAIL": "t@example.invalid",
       "GIT_COMMITTER_NAME": "시험", "GIT_COMMITTER_EMAIL": "t@example.invalid", "PYTHONIOENCODING": "utf-8"}


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), cwd=cwd, env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace")


def g(cwd: Path, *args: str) -> str:
    r = run(cwd, "git", *args)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def sync(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return run(cwd, sys.executable, str(TOOL), *args)


def commit(cwd: Path, name: str, text: str, msg: str = "c") -> None:
    (cwd / name).parent.mkdir(parents=True, exist_ok=True)
    (cwd / name).write_text(text, encoding="utf-8")
    g(cwd, "add", name)
    g(cwd, "commit", "-q", "-m", msg)


@pytest.fixture()
def repos(tmp_path):
    """origin + 교사 PC 폴더(pc, 로컬 IDE 가 씀) + GitHub 에서 일하는 다른 작업자(web)."""
    origin = tmp_path / "origin.git"
    g(tmp_path, "init", "--bare", "-b", "main", str(origin))
    seed = tmp_path / "seed"
    g(tmp_path, "clone", "-q", str(origin), str(seed))
    commit(seed, "web/index.html", "a\nb\nc\n", "init")
    commit(seed, "README.md", "readme\n", "readme")
    g(seed, "push", "-q", "origin", "HEAD:main")
    pc, web = tmp_path / "pc", tmp_path / "web"
    g(tmp_path, "clone", "-q", str(origin), str(pc))
    g(tmp_path, "clone", "-q", str(origin), str(web))
    return {"origin": origin, "pc": pc, "web": web}


def test_start_makes_new_branch_from_latest_main(repos):
    commit(repos["web"], "README.md", "readme 2\n")
    g(repos["web"], "push", "-q", "origin", "HEAD:main")
    r = sync(repos["pc"], "start", "proj/P2-phone")
    assert r.returncode == 0, r.stdout
    assert g(repos["pc"], "branch", "--show-current") == "proj/P2-phone"
    assert (repos["pc"] / "README.md").read_text(encoding="utf-8") == "readme 2\n"


def test_save_merges_main_and_pushes(repos):
    pc = repos["pc"]
    assert sync(pc, "start", "proj/P2-phone").returncode == 0
    commit(pc, "web/phone.css", "x\n")
    commit(repos["web"], "README.md", "from web\n")
    g(repos["web"], "push", "-q", "origin", "HEAD:main")
    r = sync(pc, "save")
    assert r.returncode == 0, r.stdout
    assert "refs/heads/proj/P2-phone" in g(pc, "ls-remote", "--heads", "origin")
    assert (pc / "README.md").read_text(encoding="utf-8") == "from web\n"   # 남의 변경도 받음
    assert g(pc, "rev-list", "--count", "origin/proj/P2-phone..HEAD") == "0"


def test_dirty_tree_stops_without_changing_anything(repos):
    pc = repos["pc"]
    assert sync(pc, "start", "proj/P2-phone").returncode == 0
    (pc / "web" / "phone.css").write_text("half\n", encoding="utf-8")
    r = sync(pc, "save")
    assert r.returncode == 1 and "커밋 안 한" in r.stdout
    assert (pc / "web" / "phone.css").read_text(encoding="utf-8") == "half\n"


def test_conflict_is_aborted_and_reported(repos):
    pc, web = repos["pc"], repos["web"]
    assert sync(pc, "start", "proj/P2-phone").returncode == 0
    commit(pc, "web/index.html", "a\nPC\nc\n")
    commit(web, "web/index.html", "a\nWEB\nc\n")
    g(web, "push", "-q", "origin", "HEAD:main")
    r = sync(pc, "save")
    assert r.returncode == 1 and "web/index.html" in r.stdout
    assert g(pc, "status", "--porcelain") == ""                       # 합치기 취소됨
    assert "PC" in (pc / "web" / "index.html").read_text(encoding="utf-8")


def test_overlap_with_other_branch_is_warned(repos):
    pc, web = repos["pc"], repos["web"]
    g(web, "switch", "-q", "-c", "task/T70-tools")
    commit(web, "web/index.html", "a\nb\nc\nd\n")
    g(web, "push", "-q", "origin", "task/T70-tools")
    assert sync(pc, "start", "proj/P2-phone").returncode == 0
    commit(pc, "web/index.html", "z\na\nb\nc\n")
    r = sync(pc, "save")
    assert r.returncode == 0, r.stdout
    assert "origin/task/T70-tools" in r.stdout and "web/index.html" in r.stdout


def test_end_pushes_and_leaves_folder_free_for_next_ide(repos):
    pc = repos["pc"]
    assert sync(pc, "start", "proj/P1-tools").returncode == 0
    commit(pc, "web/tools.js", "t\n")
    r = sync(pc, "end")
    assert r.returncode == 0, r.stdout
    assert g(pc, "branch", "--show-current") == ""                    # 빈 상태(origin/main)
    assert "refs/heads/proj/P1-tools" in g(pc, "ls-remote", "--heads", "origin")
    # 다음 IDE 가 자기 브랜치로 바로 시작, 나중에 앞 IDE 가 이어받기도 됨
    assert sync(pc, "start", "proj/P2-phone").returncode == 0
    assert sync(pc, "end").returncode == 0
    assert sync(pc, "start", "proj/P1-tools").returncode == 0
    assert (pc / "web" / "tools.js").exists()


def test_save_on_main_is_refused(repos):
    r = sync(repos["pc"], "save")
    assert r.returncode == 2
