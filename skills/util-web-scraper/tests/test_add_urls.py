"""util-web-scraper scripts/add_urls.py 시험 (T13)

- 실제 EduSearch 폴더·scraper.py·indexer.py·네트워크 없이: 설정 파일은 tmp_path 의 가짜 config.json,
  subprocess.run 은 가짜로 바꾼다.
- add_urls.py 는 EDUSEARCH_DIR/CONFIG_PATH 를 코드에 고정해 두었으므로(ISSUE-001) 시험에서는 그 값을 바꿔 끼운다.
- 소스는 고치지 않는다. 버그로 보이는 것은 xfail(strict) 로 남기고 ISSUES.md 에 적었다.
- 맨 아래 `if __name__ == "__main__":` 부분(argparse)은 고정 경로 때문에 불러서 시험할 수 없어 제외했다.

실행: python -m pytest skills/util-web-scraper/tests -q
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "add_urls.py"


@pytest.fixture()
def mod(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("add_urls_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # 고정 경로(교사 PC)를 시험용 임시 폴더로 바꿔 끼운다
    monkeypatch.setattr(module, "EDUSEARCH_DIR", str(tmp_path))
    monkeypatch.setattr(module, "CONFIG_PATH", str(tmp_path / "config.json"))
    return module


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
