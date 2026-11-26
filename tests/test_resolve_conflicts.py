"""tools/resolve_conflicts.py 시험 — 임시 저장소에서 실제로 충돌을 만들어 푼다."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "resolve_conflicts.py"
sys.path.insert(0, str(ROOT / "tools"))
from resolve_conflicts import merge_worklog  # noqa: E402

ENV = {**os.environ, "GIT_AUTHOR_NAME": "시험", "GIT_AUTHOR_EMAIL": "t@example.invalid",
       "GIT_COMMITTER_NAME": "시험", "GIT_COMMITTER_EMAIL": "t@example.invalid", "PYTHONIOENCODING": "utf-8"}


def g(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, env=ENV, capture_output=True, text=True, encoding="utf-8")
    return r.stdout


def write(cwd: Path, name: str, text: str) -> None:
    p = cwd / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def test_merge_worklog_sorts_by_time_and_keeps_one_heading():
    ours = "# w 일지\n\n- 2026-11-26 10:00 T1 시작\n- 2026-11-26 12:00 T1 PR 올림\n"
    theirs = "# w 일지\n\n- 2026-11-26 10:00 T1 시작\n- 2026-11-26 11:00 T2 시작\n  이어지는 설명\n"
    out = merge_worklog(ours, theirs)
    assert out.count("# w 일지") == 1
    lines = [l for l in out.splitlines() if l.startswith("- ")]
    assert lines == ["- 2026-11-26 10:00 T1 시작", "- 2026-11-26 11:00 T2 시작", "- 2026-11-26 12:00 T1 PR 올림"]
    assert "  이어지는 설명" in out.split("T2 시작")[1].split("\n- ")[0]


@pytest.fixture()
def conflict_repo(tmp_path):
    r = tmp_path / "r"
    g(tmp_path, "init", "-q", "-b", "main", str(r))
    write(r, "docs/worklog/w.md", "# w 일지\n\n- 2026-11-26 09:00 T0 시작\n")
    write(r, "docs/ISSUES.md", "# 문제\n\n끝\n")
    write(r, "code.py", "x = 1\n")
    g(r, "add", ".")
    g(r, "commit", "-q", "-m", "init")
    g(r, "switch", "-q", "-c", "b")
    write(r, "docs/worklog/w.md", "# w 일지\n\n- 2026-11-26 09:00 T0 시작\n- 2026-11-26 11:00 T2 시작\n")
    write(r, "docs/ISSUES.md", "# 문제\n\n### B 항목\n끝\n")
    g(r, "commit", "-q", "-am", "b")
    g(r, "switch", "-q", "main")
    write(r, "docs/worklog/w.md", "# w 일지\n\n- 2026-11-26 09:00 T0 시작\n- 2026-11-26 10:00 T1 시작\n")
    write(r, "docs/ISSUES.md", "# 문제\n\n### A 항목\n끝\n")
    g(r, "commit", "-q", "-am", "a")
    g(r, "merge", "-q", "b")
    return r


def run_tool(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=cwd, env=ENV, capture_output=True, text=True,
                          encoding="utf-8")


def test_worklog_resolved_and_other_markdown_reported(conflict_repo):
    r = run_tool(conflict_repo)
    assert r.returncode == 1 and "docs/ISSUES.md" in r.stdout
    log = (conflict_repo / "docs/worklog/w.md").read_text(encoding="utf-8")
    assert "<<<<<<<" not in log and log.index("10:00 T1") < log.index("11:00 T2")


def test_keep_both_clears_markers(conflict_repo):
    r = run_tool(conflict_repo, "--keep-both", "docs/ISSUES.md")
    assert r.returncode == 0, r.stdout
    issues = (conflict_repo / "docs/ISSUES.md").read_text(encoding="utf-8")
    assert "### A 항목" in issues and "### B 항목" in issues and "=======" not in issues
