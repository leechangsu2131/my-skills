"""tools/build_catalog.py 의 '추적 중인 결과물 경고' 시험.

실제 저장소 파일은 건드리지 않는다. 가짜 경로 목록·임시 폴더·임시 git 저장소만 쓴다.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_catalog as bc  # noqa: E402


# ---------- find_artifacts (순수 함수) ----------

def test_nothing_suspicious_gives_no_warning():
    paths = [
        "README.md",
        "skills/demo/SKILL.md",
        "skills/demo/ISSUES.md",
        "skills/demo/scripts/run.py",
        "skills/demo/template.md",
        "docs/plans/pdf-notes.md",
    ]
    assert bc.find_artifacts(paths) == []


def test_empty_list():
    assert bc.find_artifacts([]) == []


def test_tmp_folder_is_grouped_into_one_line_with_count():
    paths = [f"skills/demo/tmp_pages/p{i}.png" for i in range(3)] + ["skills/demo/SKILL.md"]
    warnings = bc.find_artifacts(paths)
    assert len(warnings) == 1
    assert warnings[0].startswith("skills/demo/tmp_pages/ — ")
    assert "(파일 3개)" in warnings[0]


def test_tmp_file_is_reported_by_its_own_path():
    warnings = bc.find_artifacts(["skills/demo/tmp_shot.png"])
    assert len(warnings) == 1
    assert warnings[0].startswith("skills/demo/tmp_shot.png — ")
    assert "(파일" not in warnings[0]  # 파일 하나는 개수 표시 없음


def test_generated_rows_is_reported():
    warnings = bc.find_artifacts(["skills/demo/generated_rows/a.json", "skills/demo/generated_rows_1.csv"])
    assert [w.split(" — ")[0] for w in warnings] == [
        "skills/demo/generated_rows/",
        "skills/demo/generated_rows_1.csv",
    ]


@pytest.mark.parametrize("name", ["보고서.pdf", "Report.PDF", "a b.pdf"])
def test_pdf_files_are_reported_in_any_case(name):
    warnings = bc.find_artifacts([f"skills/demo/data/{name}"])
    assert len(warnings) == 1 and warnings[0].startswith(f"skills/demo/data/{name} — ")


def test_pdf_only_counts_for_the_file_name_not_a_folder_name():
    assert bc.find_artifacts(["skills/demo/notes.pdf/readme.txt"]) == []


def test_results_are_sorted_and_deduplicated_per_group():
    paths = ["skills/b/tmp_x/1.png", "skills/a/x.pdf", "skills/b/tmp_x/2.png"]
    warnings = bc.find_artifacts(paths)
    assert [w.split(" — ")[0] for w in warnings] == ["skills/a/x.pdf", "skills/b/tmp_x/"]


# ---------- tracked_paths ----------

def test_tracked_paths_returns_empty_when_git_is_missing(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(bc.subprocess, "run", boom)
    assert bc.tracked_paths() == []


@pytest.mark.skipif(shutil.which("git") is None, reason="git 이 없음")
def test_tracked_paths_reads_a_real_repo_including_korean_names(tmp_path, monkeypatch):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    (tmp_path / "skills" / "demo").mkdir(parents=True)
    (tmp_path / "skills" / "demo" / "한글 파일.pdf").write_bytes(b"x")
    (tmp_path / "skills" / "demo" / "tmp_a.png").write_bytes(b"x")
    (tmp_path / "skills" / "demo" / "not_added.txt").write_text("x")
    git("add", "skills/demo/한글 파일.pdf", "skills/demo/tmp_a.png")

    monkeypatch.setattr(bc, "ROOT", tmp_path)
    paths = bc.tracked_paths()
    assert sorted(paths) == ["skills/demo/tmp_a.png", "skills/demo/한글 파일.pdf"]
    assert len(bc.find_artifacts(paths)) == 2


# ---------- main: 경고는 종료값을 바꾸지 않는다 ----------

def run_main(monkeypatch, capsys, *, argv, problems, tracked):
    monkeypatch.setattr(bc, "collect", lambda: ([], problems))
    monkeypatch.setattr(bc, "tracked_paths", lambda: tracked)
    monkeypatch.setattr(sys, "argv", ["build_catalog.py", *argv])
    code = bc.main()
    return code, capsys.readouterr().out


def test_check_with_only_warnings_still_passes(monkeypatch, capsys):
    code, out = run_main(monkeypatch, capsys, argv=["--check"], problems=[], tracked=["skills/demo/tmp_a.png"])
    assert code == 0
    assert out.startswith("문제 없음")
    assert "⚠ 경고" in out and "skills/demo/tmp_a.png" in out


def test_check_with_problems_still_fails_and_shows_both(monkeypatch, capsys):
    code, out = run_main(
        monkeypatch, capsys, argv=["--check"], problems=["demo: SKILL.md 없음"], tracked=["skills/demo/a.pdf"]
    )
    assert code == 1
    assert "demo: SKILL.md 없음" in out and "skills/demo/a.pdf" in out


def test_check_clean_has_no_warning_section(monkeypatch, capsys):
    code, out = run_main(monkeypatch, capsys, argv=["--check"], problems=[], tracked=["skills/demo/SKILL.md"])
    assert code == 0
    assert out.strip() == "문제 없음"


def test_build_mode_also_shows_warnings_and_writes_catalog(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(bc, "CATALOG", tmp_path / "CATALOG.md")
    code, out = run_main(monkeypatch, capsys, argv=[], problems=[], tracked=["skills/demo/a.pdf"])
    assert code == 0
    assert (tmp_path / "CATALOG.md").is_file()
    assert "⚠ 경고" in out


# ---------- 기존 점검이 그대로인지 (SKILL.md 없는 폴더 등) ----------

def make_skill(root, name, *, skill_md=True, issues=True):
    d = root / name
    d.mkdir(parents=True)
    (d / "code.py").write_text("print('x')\n", encoding="utf-8")
    if skill_md:
        (d / "SKILL.md").write_text(
            "---\nname: " + name + "\ndescription: 시험용\nmetadata:\n  category: 공통 유틸\n"
            "  status: 개발\n  summary: 시험용 스킬\n---\n본문\n",
            encoding="utf-8",
        )
    if issues:
        (d / "ISSUES.md").write_text("# 이슈\n", encoding="utf-8")


def test_existing_checks_still_flag_folder_without_skill_md(monkeypatch, tmp_path):
    make_skill(tmp_path, "good")
    make_skill(tmp_path, "no-skill-md", skill_md=False)
    make_skill(tmp_path, "no-issues", issues=False)
    monkeypatch.setattr(bc, "SKILLS", tmp_path)
    _, problems = bc.collect()
    assert "no-skill-md: SKILL.md 없음" in problems
    assert "no-issues: ISSUES.md 없음" in problems
    assert not any(p.startswith("good:") for p in problems)
