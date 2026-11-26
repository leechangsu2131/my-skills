"""tools/merge_ready.py 시험 — 임시 폴더에 가짜 원격(bare)과 작업 폴더를 만들어 git 으로 실제로 돌린다(네트워크 없음).

T81: 이미 다른 판으로 main 에 들어간 브랜치는 '문서·시험만' 이 아니라 '건너뜀' 으로 나눠야 한다.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "merge_ready.py"

ENV = {**os.environ, "GIT_AUTHOR_NAME": "시험", "GIT_AUTHOR_EMAIL": "t@example.invalid",
       "GIT_COMMITTER_NAME": "시험", "GIT_COMMITTER_EMAIL": "t@example.invalid", "PYTHONIOENCODING": "utf-8"}

TASKS = """# 할 일

| 번호 | 할 일 | 상태 |
|---|---|---|
| T10 | 시험 쓰기 | 완료(2026-11-26 합침) |
| T11 | 다른 일 | 열림 |
"""
ISSUES = "".join(f"- 항목 {i}\n" for i in range(10))


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), cwd=cwd, env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace")


def g(cwd: Path, *args: str) -> str:
    r = run(cwd, "git", *args)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def commit(work: Path, files: dict[str, str], msg: str) -> None:
    for name, text in files.items():
        p = work / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        g(work, "add", name)
    g(work, "commit", "-q", "-m", msg)


def make_repo(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    g(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    g(tmp_path, "clone", "-q", str(origin), str(work))
    g(work, "checkout", "-q", "-b", "main")
    commit(work, {"docs/TASKS.md": TASKS, "skills/a/ISSUES.md": "# a\n", "README.md": "x\n"}, "base")
    g(work, "push", "-q", "origin", "main")
    return work


def push_branch(work: Path, name: str, files: dict[str, str]) -> None:
    g(work, "checkout", "-q", "-b", name, "main")
    commit(work, files, f"work {name}")
    g(work, "push", "-q", "origin", name)
    g(work, "checkout", "-q", "main")


def classify(work: Path) -> str:
    r = run(work, sys.executable, str(TOOL))
    assert r.returncode == 0, r.stderr
    return r.stdout


def section(out: str, kind: str) -> str:
    """'[문서·시험만] N개' 부터 다음 '[' 절 앞까지."""
    head = f"[{kind}]"
    start = out.index(head)
    nxt = out.find("\n[", start + 1)
    return out[start: nxt if nxt != -1 else len(out)]


def test_main_에_이미_있는_내용을_다시_더한_브랜치는_건너뛴다(tmp_path):
    work = make_repo(tmp_path)
    # 다른 판(squash 같은)으로 main 에 먼저 들어간 내용
    commit(work, {"skills/a/ISSUES.md": "# a\n" + ISSUES}, "main 에 먼저 합쳐진 판")
    g(work, "push", "-q", "origin", "main")
    # 같은 내용을 따로 더한 브랜치(다른 커밋이라 cherry 로는 같다고 안 나옴)
    push_branch_from_base(work, "feature/same-work", {"skills/a/ISSUES.md": "# a\n" + ISSUES, "skills/a/NOTE.md": "n\n"})
    out = classify(work)
    assert "feature/same-work" in section(out, "건너뜀")
    assert "feature/same-work" not in section(out, "문서·시험만")
    assert "main 에 이미 있음" in section(out, "건너뜀")


def push_branch_from_base(work: Path, name: str, files: dict[str, str]) -> None:
    base = g(work, "rev-list", "--max-parents=0", "main")
    g(work, "checkout", "-q", "-b", name, base)
    commit(work, files, f"work {name}")
    g(work, "push", "-q", "origin", name)
    g(work, "checkout", "-q", "main")


def test_새_내용을_더한_브랜치는_그대로_문서_시험만(tmp_path):
    work = make_repo(tmp_path)
    push_branch(work, "feature/new-docs", {"skills/a/ISSUES.md": "# a\n" + ISSUES})
    out = classify(work)
    assert "feature/new-docs" in section(out, "문서·시험만")


def test_TASKS_에서_이미_완료한_번호의_브랜치는_건너뛴다(tmp_path):
    work = make_repo(tmp_path)
    push_branch(work, "task/T10-tests-again", {"skills/a/NEW.md": "다른 판의 같은 일\n"})
    out = classify(work)
    assert "task/T10-tests-again" in section(out, "건너뜀")
    assert "이미 완료" in section(out, "건너뜀")


def test_열림_번호의_브랜치는_건너뛰지_않는다(tmp_path):
    work = make_repo(tmp_path)
    push_branch(work, "task/T11-docs", {"skills/a/NEW.md": "새 글\n"})
    out = classify(work)
    assert "task/T11-docs" in section(out, "문서·시험만")


def test_상시_일_S_번호는_완료_표시와_상관없이_건너뛰지_않는다(tmp_path):
    work = make_repo(tmp_path)
    text = TASKS + "| S1 | 상시 | 완료 |\n"
    commit(work, {"docs/TASKS.md": text}, "S1 표시")
    g(work, "push", "-q", "origin", "main")
    push_branch(work, "task/S1-some-skill", {"skills/a/NEW.md": "새 글\n"})
    out = classify(work)
    assert "task/S1-some-skill" in section(out, "문서·시험만")


def test_코드가_바뀐_새_브랜치는_코드_바뀜으로_남는다(tmp_path):
    work = make_repo(tmp_path)
    push_branch(work, "feature/code", {"skills/a/run.py": "print(1)\n"})
    out = classify(work)
    assert "feature/code" in section(out, "코드 바뀜")
