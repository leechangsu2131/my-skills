"""check_setup.py 의 작은 도우미 함수 시험 (S1): expand_percent·read_node_version·find_chrome·find_onedrive.

    python -m pytest tests -v      (teacherlesson-assistant 폴더에서)

실제 크롬·OneDrive·node 는 찾지 않는다(가짜 환경 값과 가짜 파일 검사 함수만 씀).
"""
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import check_setup as cs  # noqa: E402


# ── expand_percent ──

def test_expand_percent_replaces_known_variables():
    assert cs.expand_percent("%A%\\x\\%B%", {"A": "C:\\a", "B": "b"}) == "C:\\a\\x\\b"


def test_expand_percent_keeps_unknown_variables_as_written():
    assert cs.expand_percent("%없음%\\%NOPE%\\%A%", {"A": "1"}) == "%없음%\\%NOPE%\\1"


@pytest.mark.parametrize("value", ["", "퍼센트 없음", "100%", "50% 할인 30%", "%%", "% A %", "%1A%"])
def test_expand_percent_leaves_text_without_a_variable_alone(value):
    assert cs.expand_percent(value, {"A": "x", "1A": "y"}) == value


def test_expand_percent_is_case_sensitive_and_does_not_expand_inside_values():
    assert cs.expand_percent("%a%", {"A": "x"}) == "%a%"
    assert cs.expand_percent("%A%", {"A": "%B%", "B": "깊은 값"}) == "%B%"      # 값 안의 %B% 는 다시 펼치지 않음


# ── read_node_version ──

def test_read_node_version_returns_stripped_output_of_a_real_command():
    # 파이썬 자신을 가짜 node 로 씀: `python --version` → "Python 3.x.y"
    out = cs.read_node_version(sys.executable)
    assert out.startswith("Python 3.") and out == out.strip()


@pytest.mark.parametrize("path", ["/없는/경로/node", ""])
def test_read_node_version_missing_command_is_empty(path):
    assert cs.read_node_version(path) == ""


def test_read_node_version_nonzero_exit_is_empty(monkeypatch):
    monkeypatch.setattr(cs.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 1, stdout="v20.0.0\n", stderr=""))
    assert cs.read_node_version("node") == ""


def test_read_node_version_timeout_is_empty(monkeypatch):
    def slow(*a, **k):
        raise subprocess.TimeoutExpired("node", 10)
    monkeypatch.setattr(cs.subprocess, "run", slow)
    assert cs.read_node_version("node") == ""


def test_read_node_version_strips_newline(monkeypatch):
    monkeypatch.setattr(cs.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="v22.1.0\n", stderr=""))
    assert cs.read_node_version("node") == "v22.1.0"


# ── find_chrome ──

CHROME = "Google/Chrome/Application/chrome.exe"


def test_find_chrome_checks_program_files_then_x86_then_localappdata():
    env = {"PROGRAMFILES": "C:/PF", "PROGRAMFILES(X86)": "C:/PF86", "LOCALAPPDATA": "C:/LA"}
    asked = []

    def is_file(p):
        asked.append(pathlib.Path(p).as_posix())
        return pathlib.Path(p).as_posix() == "C:/LA/" + CHROME

    found = cs.find_chrome(env, is_file=is_file, which=lambda name: None)
    assert pathlib.Path(found).as_posix() == "C:/LA/" + CHROME
    assert asked == ["C:/PF/" + CHROME, "C:/PF86/" + CHROME, "C:/LA/" + CHROME]


def test_find_chrome_first_hit_wins_and_which_is_not_asked():
    env = {"PROGRAMFILES": "C:/PF", "LOCALAPPDATA": "C:/LA"}
    found = cs.find_chrome(env, is_file=lambda p: True, which=lambda name: pytest.fail("which 를 부르면 안 됨"))
    assert pathlib.Path(found).as_posix() == "C:/PF/" + CHROME


def test_find_chrome_falls_back_to_path_search_for_chrome():
    seen = []
    found = cs.find_chrome({}, is_file=lambda p: False, which=lambda name: seen.append(name) or "/usr/bin/chrome")
    assert found == "/usr/bin/chrome" and seen == ["chrome"]


def test_find_chrome_nothing_found_is_none():
    assert cs.find_chrome({}, is_file=lambda p: False, which=lambda name: None) is None


def test_find_chrome_missing_env_vars_do_not_look_at_the_current_folder_root():
    asked = []
    cs.find_chrome({}, is_file=lambda p: asked.append(pathlib.Path(p).as_posix()) or False, which=lambda name: None)
    assert all(a == CHROME for a in asked)        # 변수가 없으면 상대 경로 한 가지만 물어봄(절대 경로가 아님)


# ── find_onedrive ──

def test_find_onedrive_prefers_commercial_then_personal_then_home_folder(tmp_path):
    home = tmp_path / "home"
    work, personal = tmp_path / "work", tmp_path / "personal"
    all_dirs = {work, personal, home / cs.skill_env.ONEDRIVE_FOLDER_NAME}
    env = {"OneDriveCommercial": str(work), "OneDrive": str(personal)}
    assert cs.find_onedrive(env, home, is_dir=lambda p: pathlib.Path(p) in all_dirs) == work
    assert cs.find_onedrive(env, home, is_dir=lambda p: pathlib.Path(p) in all_dirs - {work}) == personal
    assert cs.find_onedrive(env, home, is_dir=lambda p: pathlib.Path(p) in {home / cs.skill_env.ONEDRIVE_FOLDER_NAME}) \
        == home / cs.skill_env.ONEDRIVE_FOLDER_NAME


def test_find_onedrive_skips_unset_or_empty_variables_and_missing_folders(tmp_path):
    home = tmp_path / "home"
    asked = []
    result = cs.find_onedrive({"OneDriveCommercial": "", "OneDrive": ""}, home, is_dir=lambda p: asked.append(pathlib.Path(p)) or False)
    assert result is None
    assert asked == [home / cs.skill_env.ONEDRIVE_FOLDER_NAME]        # 빈 변수는 후보에서 뺌


def test_find_onedrive_real_folder_check(tmp_path):
    (tmp_path / "OneDrive").mkdir()
    assert cs.find_onedrive({"OneDrive": str(tmp_path / "OneDrive")}, tmp_path) == tmp_path / "OneDrive"
    assert cs.find_onedrive({"OneDrive": str(tmp_path / "없음")}, tmp_path / "집") is None
