"""util-web-scraper scripts/add_urls.py 시험 (T13)

- 실제 EduSearch 폴더·scraper.py·indexer.py·네트워크 없이: 설정 파일은 tmp_path 의 가짜 config.json,
  subprocess.run 은 가짜로 바꾼다.
- EDUSEARCH_DIR(EduSearch 위치)는 중앙 .env·환경변수 또는 my-skills 옆 폴더로 정해지므로, 시험에서는
  환경변수로 임시 폴더를 가리키게 한다. 중앙 .env(load_env)는 시험에 섞이지 않게 꺼 둔다.
- 버그로 보이는 것은 xfail(strict) 로 남기고 ISSUES.md 에 적었다.

실행: python -m pytest skills/util-web-scraper/tests -q
"""

from __future__ import annotations

import importlib.util
import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "add_urls.py"
SKILLS_DIR = SCRIPT.parents[2]


def _disable_central_env():
    """중앙 .env(교사 PC 의 실제 설정)가 시험에 섞이지 않게 load_env 를 빈 함수로 바꾼다."""
    sys.path.insert(0, str(SKILLS_DIR / "_shared"))
    import skill_env

    skill_env.load_env = lambda *args, **kwargs: None


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    _disable_central_env()
    monkeypatch.delenv("EDUSEARCH_DIR", raising=False)


@pytest.fixture()
def mod(tmp_path, monkeypatch):
    monkeypatch.setenv("EDUSEARCH_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location("add_urls_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_as_main(monkeypatch, *argv):
    """add_urls.py 를 `python add_urls.py <argv>` 처럼 실행한다(EDUSEARCH_DIR 환경변수는 호출 전에 정해 둔다)."""
    monkeypatch.setattr(sys, "argv", ["add_urls.py", *argv])
    runpy.run_path(str(SCRIPT), run_name="__main__")


def write_config(tmp_path: Path, config: dict) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return path


def read_config(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))


# ───────── load_config / save_config ─────────

def test_save_config_한글을_그대로_들여쓰기_2칸으로_저장한다(mod, tmp_path):
    mod.save_config({"target_sites": [{"url": "https://example.invalid/가", "use_selenium": False}]})
    raw = (tmp_path / "config.json").read_text(encoding="utf-8")
    assert "가" in raw and "\\u" not in raw
    assert raw.startswith('{\n  "target_sites"')


def test_load_config_save_config_왕복(mod, tmp_path):
    config = {"target_sites": [], "delay": 5, "메모": "한글"}
    mod.save_config(config)
    assert mod.load_config() == config


def test_load_config_파일이_없으면_FileNotFoundError(mod):
    """설정 파일이 없을 때의 현재 동작(안내 없이 오류로 멈춤)."""
    with pytest.raises(FileNotFoundError):
        mod.load_config()


# ───────── add_urls ─────────

def test_새_URL은_추가하고_저장하고_추가된_목록을_돌려준다(mod, tmp_path, capsys):
    write_config(tmp_path, {"target_sites": []})
    added = mod.add_urls(["https://a.example.invalid", "https://b.example.invalid"])
    assert added == ["https://a.example.invalid", "https://b.example.invalid"]
    assert read_config(tmp_path)["target_sites"] == [
        {"url": "https://a.example.invalid", "use_selenium": False},
        {"url": "https://b.example.invalid", "use_selenium": False},
    ]
    out = capsys.readouterr().out
    assert "[추가] https://a.example.invalid" in out
    assert "2개 URL 추가됨" in out


def test_selenium_옵션은_새로_추가하는_모든_URL에_붙는다(mod, tmp_path):
    write_config(tmp_path, {"target_sites": []})
    mod.add_urls(["https://a.example.invalid", "https://b.example.invalid"], use_selenium=True)
    assert [s["use_selenium"] for s in read_config(tmp_path)["target_sites"]] == [True, True]


def test_이미_있는_URL은_건너뛰고_기존_항목을_바꾸지_않는다(mod, tmp_path, capsys):
    existing = {"url": "https://a.example.invalid", "use_selenium": False}
    write_config(tmp_path, {"target_sites": [existing]})
    added = mod.add_urls(["https://a.example.invalid"], use_selenium=True)
    assert added == []
    assert read_config(tmp_path)["target_sites"] == [existing]  # selenium 값도 그대로
    out = capsys.readouterr().out
    assert "[SKIP] 이미 있음" in out and "변경 없음" in out


def test_변경이_없으면_설정_파일을_다시_쓰지_않는다(mod, tmp_path):
    path = write_config(tmp_path, {"target_sites": [{"url": "https://a.example.invalid"}]})
    before = path.stat().st_mtime_ns
    raw_before = path.read_text(encoding="utf-8")
    mod.add_urls(["https://a.example.invalid"])
    assert path.read_text(encoding="utf-8") == raw_before
    assert path.stat().st_mtime_ns == before


def test_같은_URL을_한_번에_두_번_주면_한_번만_추가한다(mod, tmp_path):
    write_config(tmp_path, {"target_sites": []})
    added = mod.add_urls(["https://a.example.invalid", "https://a.example.invalid"])
    assert added == ["https://a.example.invalid"]
    assert len(read_config(tmp_path)["target_sites"]) == 1


def test_새것과_기존것이_섞여_있으면_새것만_추가한다(mod, tmp_path):
    write_config(tmp_path, {"target_sites": [{"url": "https://old.example.invalid", "use_selenium": False}]})
    added = mod.add_urls(["https://old.example.invalid", "https://new.example.invalid"])
    assert added == ["https://new.example.invalid"]
    assert [s["url"] for s in read_config(tmp_path)["target_sites"]] == [
        "https://old.example.invalid", "https://new.example.invalid"]


def test_설정의_다른_항목은_그대로_보존한다(mod, tmp_path):
    write_config(tmp_path, {"target_sites": [], "delay": 5, "user_agent": "테스트", "nested": {"a": [1, 2]}})
    mod.add_urls(["https://a.example.invalid"])
    config = read_config(tmp_path)
    assert config["delay"] == 5 and config["user_agent"] == "테스트" and config["nested"] == {"a": [1, 2]}


def test_빈_URL_목록이면_변경_없음(mod, tmp_path, capsys):
    write_config(tmp_path, {"target_sites": []})
    assert mod.add_urls([]) == []
    assert "변경 없음" in capsys.readouterr().out


def test_주소_끝_슬래시나_대소문자가_다르면_다른_주소로_본다(mod, tmp_path):
    """현재 동작: 문자열이 정확히 같을 때만 중복. 같은 사이트가 두 번 들어갈 수 있다(ISSUE-003)."""
    write_config(tmp_path, {"target_sites": [{"url": "https://a.example.invalid", "use_selenium": False}]})
    added = mod.add_urls(["https://a.example.invalid/", "HTTPS://A.EXAMPLE.INVALID"])
    assert len(added) == 2


@pytest.mark.xfail(strict=True, reason="ISSUE-002: 설정 파일에 target_sites 가 없으면 KeyError 로 멈춤(읽을 때는 기본값을 쓰면서 추가할 때는 안 씀)")
def test_target_sites_가_없는_설정에도_추가할_수_있어야_한다(mod, tmp_path):
    write_config(tmp_path, {"delay": 5})
    added = mod.add_urls(["https://a.example.invalid"])
    assert added == ["https://a.example.invalid"]


@pytest.mark.xfail(strict=True, reason="ISSUE-003: 같은 사이트인데 끝 슬래시·대소문자만 다른 주소가 중복으로 들어감")
def test_끝_슬래시만_다른_주소는_중복으로_봐야_한다(mod, tmp_path):
    write_config(tmp_path, {"target_sites": [{"url": "https://a.example.invalid", "use_selenium": False}]})
    assert mod.add_urls(["https://a.example.invalid/"]) == []


# ───────── run_scraper_and_indexer ─────────

def fake_run_factory(codes, calls):
    queue = list(codes)

    def fake_run(cmd, cwd=None):
        calls.append({"cmd": cmd, "cwd": cwd})
        return SimpleNamespace(returncode=queue.pop(0))

    return fake_run


def test_스크래퍼_다음_인덱서_순서로_EduSearch_폴더에서_실행한다(mod, monkeypatch, tmp_path, capsys):
    calls = []
    monkeypatch.setattr(mod.subprocess, "run", fake_run_factory([0, 0], calls))
    mod.run_scraper_and_indexer()
    assert calls == [
        {"cmd": [sys.executable, "scraper.py"], "cwd": str(tmp_path)},
        {"cmd": [sys.executable, "indexer.py"], "cwd": str(tmp_path)},
    ]
    assert "완료" in capsys.readouterr().out


def test_스크래퍼가_실패하면_인덱서는_실행하지_않는다(mod, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(mod.subprocess, "run", fake_run_factory([1], calls))
    mod.run_scraper_and_indexer()
    assert [c["cmd"][1] for c in calls] == ["scraper.py"]
    out = capsys.readouterr().out
    assert "scraper.py 실패" in out and "완료" not in out


@pytest.mark.xfail(strict=True, reason="ISSUE-004: 인덱서가 실패해도 종료 코드를 안 보고 '완료! 검색 가능' 이라고만 알림(검색이 옛 인덱스일 수 있음)")
def test_인덱서가_실패하면_완료라고_하지_않아야_한다(mod, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(mod.subprocess, "run", fake_run_factory([0, 1], calls))
    mod.run_scraper_and_indexer()
    assert "완료" not in capsys.readouterr().out


# ───────── EduSearch 위치 찾기 (ISSUE-001 해결) ─────────

def test_환경변수로_위치를_정하면_그_폴더를_쓴다(mod, tmp_path):
    assert mod.EDUSEARCH_DIR == str(tmp_path)
    assert mod.CONFIG_PATH == str(tmp_path / "config.json")


def test_환경변수가_없으면_my_skills_옆_edusearch_폴더(mod, monkeypatch):
    monkeypatch.delenv("EDUSEARCH_DIR", raising=False)
    repo_root = SCRIPT.parents[3]  # my-skills 저장소 폴더
    assert mod.find_edusearch_dir() == str(repo_root.parent / "edusearch")


def test_환경변수가_공백뿐이면_옆_폴더로_본다(mod, monkeypatch):
    monkeypatch.setenv("EDUSEARCH_DIR", "   ")
    assert mod.find_edusearch_dir() == str(SCRIPT.parents[3].parent / "edusearch")


def test_위치에_홈_표시와_환경변수를_풀어서_쓴다(mod, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("MY_GITHUB_DIR_FOR_TEST", str(tmp_path / "gh"))
    monkeypatch.setenv("EDUSEARCH_DIR", "$MY_GITHUB_DIR_FOR_TEST/edusearch")
    assert mod.find_edusearch_dir() == str(tmp_path / "gh" / "edusearch")
    monkeypatch.setenv("EDUSEARCH_DIR", "~/edusearch")
    assert mod.find_edusearch_dir() == str(tmp_path / "edusearch")


def test_소스에_특정_PC의_절대_경로가_남아_있지_않다():
    text = SCRIPT.read_text(encoding="utf-8") + (SCRIPT.parents[1] / "SKILL.md").read_text(encoding="utf-8")
    assert "C:\\Users" not in text


def test_EduSearch_폴더가_없으면_설치_방법을_알리고_종료(mod, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(mod, "EDUSEARCH_DIR", str(tmp_path / "없는폴더"))
    with pytest.raises(SystemExit) as exc:
        mod.check_edusearch_dir()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "찾을 수 없습니다" in out and "git clone" in out and "UTIL_WEB_SCRAPER__EDUSEARCH_DIR" in out


def test_EduSearch_폴더가_있으면_조용히_통과(mod, capsys):
    mod.check_edusearch_dir()
    assert capsys.readouterr().out == ""


# ───────── 명령줄 실행 (__main__) ─────────

@pytest.fixture()
def main_env(monkeypatch, tmp_path):
    """명령줄 시험 공통: EduSearch 폴더 = tmp_path, subprocess.run 가짜(성공)."""
    monkeypatch.setenv("EDUSEARCH_DIR", str(tmp_path))
    write_config(tmp_path, {"target_sites": []})
    calls = []
    monkeypatch.setattr(subprocess_module(), "run", fake_run_factory([0, 0, 0, 0], calls))
    return calls


def subprocess_module():
    import subprocess

    return subprocess


def test_명령줄_urls_는_추가하고_스크래핑_인덱싱까지_한다(main_env, monkeypatch, tmp_path):
    run_as_main(monkeypatch, "--urls", "https://a.example.invalid", "https://b.example.invalid")
    assert [s["url"] for s in read_config(tmp_path)["target_sites"]] == ["https://a.example.invalid", "https://b.example.invalid"]
    assert [c["cmd"][1] for c in main_env] == ["scraper.py", "indexer.py"]
    assert all(c["cwd"] == str(tmp_path) for c in main_env)


def test_명령줄_selenium_옵션은_새_항목에_붙는다(main_env, monkeypatch, tmp_path):
    run_as_main(monkeypatch, "--urls", "https://a.example.invalid", "--selenium")
    assert read_config(tmp_path)["target_sites"] == [{"url": "https://a.example.invalid", "use_selenium": True}]


def test_명령줄_no_run_은_추가만_하고_실행하지_않는다(main_env, monkeypatch, tmp_path):
    run_as_main(monkeypatch, "--urls", "https://a.example.invalid", "--no-run")
    assert len(read_config(tmp_path)["target_sites"]) == 1
    assert main_env == []


def test_명령줄_새로_추가된_것이_없으면_스크래핑도_하지_않는다(main_env, monkeypatch, tmp_path):
    write_config(tmp_path, {"target_sites": [{"url": "https://a.example.invalid", "use_selenium": False}]})
    run_as_main(monkeypatch, "--urls", "https://a.example.invalid")
    assert main_env == []


def test_명령줄_urls_가_없으면_사용법_오류(main_env, monkeypatch):
    with pytest.raises(SystemExit) as exc:
        run_as_main(monkeypatch)
    assert exc.value.code == 2
    assert main_env == []


def test_명령줄_EduSearch_폴더가_없으면_설정을_건드리지_않고_종료(monkeypatch, tmp_path):
    missing = tmp_path / "없는폴더"
    monkeypatch.setenv("EDUSEARCH_DIR", str(missing))
    with pytest.raises(SystemExit) as exc:
        run_as_main(monkeypatch, "--urls", "https://a.example.invalid")
    assert exc.value.code == 1
    assert not missing.exists()
