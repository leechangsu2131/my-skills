"""check_setup.py(학교 PC 점검) 시험. 실제 환경 대신 가짜(mock)로 항목마다 성공·실패 판단을 확인한다.

    python -m pytest tests -v      (teacherlesson-assistant 폴더에서)

임시 폴더만 쓰고, 실제 .env·내 문서·서버·크롬·네트워크는 건드리지 않는다.
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import check_setup as cs  # noqa: E402
from check_setup import FAIL, OK, WARN  # noqa: E402


# ── Python ──

@pytest.mark.parametrize("version,status", [
    ((3, 9, 18), FAIL), ((3, 10, 0), WARN), ((3, 12, 4), WARN), ((3, 13, 1), OK), ((3, 14, 0), OK)])
def test_python_version(version, status):
    assert cs.check_python(version).status == status


def test_python_fail_has_fix():
    assert "python.org" in cs.check_python((3, 8, 0)).fix


def test_python_warn_fix_matches_what_the_bat_really_does():
    # 실행_수업비서.bat 은 서버를 python 으로 켠다 — 'py -3.13 을 먼저 찾는다'고 말하면 틀린 안내
    fix = cs.check_python((3, 12, 4)).fix
    assert "먼저 찾아요" not in fix
    assert "python" in fix and "py -3.13" in fix


# ── Python 실행기 (py -3.13 / python) ──

def _versions(py, plain):
    table = {tuple(cs.PY_LAUNCHER): py, tuple(cs.PY_PLAIN): plain}
    return lambda cmd: table[tuple(cmd)]


def test_launchers_same_minor_is_ok():
    r = cs.check_python_launchers(_versions((3, 13, 1), (3, 13, 5)))
    assert r.status == OK and "3.13.1" in r.detail


def test_launchers_different_minor_is_warn_and_names_both():
    r = cs.check_python_launchers(_versions((3, 13, 1), (3, 11, 4)))
    assert r.status == WARN
    assert "3.13.1" in r.detail and "3.11.4" in r.detail and "달라요" in r.detail
    assert "pip install" in r.fix


def test_launchers_python_missing_is_warn():
    r = cs.check_python_launchers(_versions((3, 13, 1), None))
    assert r.status == WARN and "python 명령" in r.detail and r.fix


def test_launchers_py_launcher_missing_is_warn_about_build_units():
    r = cs.check_python_launchers(_versions(None, (3, 13, 1)))
    assert r.status == WARN and "build_units.py" in r.detail


def test_launchers_neither_found_is_warn():
    r = cs.check_python_launchers(_versions(None, None))
    assert r.status == WARN and "python.org" in r.fix


def test_read_python_version_real_interpreter_and_missing_command():
    assert cs.read_python_version([sys.executable]) == tuple(sys.version_info[:3])
    assert cs.read_python_version(["no-such-python-command-xyz"]) is None


@pytest.mark.parametrize("returncode,stdout", [(9009, ""), (1, "3.13.1"), (0, "Python was not found; run without arguments"), (0, "")])
def test_read_python_version_ignores_failures_and_odd_output(monkeypatch, returncode, stdout):
    class Done:                                   # 윈도우 스토어 가짜 python 같은 경우를 흉내
        pass
    done = Done()
    done.returncode, done.stdout = returncode, stdout
    monkeypatch.setattr(cs.subprocess, "run", lambda *a, **k: done)
    assert cs.read_python_version(["python"]) is None


# ── 패키지 ──

REQ = "requests>=2.31\ntruststore>=0.9\nPyMuPDF>=1.24\n# 주석\n"


def test_parse_requirement_names():
    assert cs.parse_requirement_names(REQ) == ["requests", "truststore", "PyMuPDF"]


def test_import_name_mapping():
    assert cs.import_name_for("PyMuPDF") == "fitz"
    assert cs.import_name_for("requests") == "requests"


def test_packages_all_installed():
    results = cs.check_packages(REQ, find_spec=lambda name: object())
    assert {r.status for r in results} == {OK}
    assert "selenium" in {r.title.split()[-1] for r in results}      # requirements 밖 selenium 도 점검


def test_packages_missing_required_is_fail_and_selenium_is_warn():
    installed = {"requests", "truststore"}                 # fitz, selenium 없음
    results = {r.title.split()[-1]: r for r in cs.check_packages(REQ, find_spec=lambda n: object() if n in installed else None)}
    assert results["PyMuPDF"].status == FAIL
    assert "pip install PyMuPDF" in results["PyMuPDF"].fix
    assert results["selenium"].status == WARN
    assert results["requests"].status == OK


def test_packages_find_spec_error_counts_as_missing():
    def boom(_name):
        raise ValueError("broken")
    assert all(r.status != OK for r in cs.check_packages("requests\n", find_spec=boom))


# ── node / Gemini CLI ──

def test_node_found_and_missing():
    ok = cs.check_node(which=lambda n: "/x/node", version_of=lambda p: "v22.1.0")
    assert (ok.status, ok.detail) == (OK, "v22.1.0")
    assert cs.check_node(which=lambda n: None).status == WARN


def test_gemini_cli_missing():
    r = cs.check_gemini_cli(which=lambda n: None)
    assert r.status == WARN and "@google/gemini-cli" in r.fix


def test_gemini_cli_npm_global_ok(tmp_path):
    js = tmp_path / "node_modules" / "@google" / "gemini-cli" / "bundle" / "gemini.js"
    js.parent.mkdir(parents=True)
    js.write_text("//")
    shim = str(tmp_path / "gemini.cmd")
    assert cs.check_gemini_cli(which=lambda n: shim if n == "gemini.cmd" else None).status == OK


def test_gemini_cli_shim_without_body_is_warn(tmp_path):
    shim = str(tmp_path / "gemini.cmd")
    assert cs.check_gemini_cli(which=lambda n: shim if n == "gemini.cmd" else None).status == WARN


# ── 크롬 ──

def test_chrome_exe_found_in_program_files(tmp_path):
    exe = tmp_path / "Google/Chrome/Application/chrome.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    assert cs.check_chrome_exe({"PROGRAMFILES": str(tmp_path)}, which=lambda n: None).status == OK


def test_chrome_exe_found_on_path():
    assert cs.check_chrome_exe({}, is_file=lambda p: False, which=lambda n: "/usr/bin/chrome").status == OK


def test_chrome_exe_missing_is_fail():
    r = cs.check_chrome_exe({}, is_file=lambda p: False, which=lambda n: None)
    assert r.status == FAIL and r.fix


def test_chrome_profile_exists(tmp_path):
    profile = tmp_path / "prof"
    profile.mkdir()
    assert cs.check_chrome_profile({"chrome_profile": str(profile)}, {}).status == OK


def test_chrome_profile_percent_var_expanded(tmp_path):
    (tmp_path / "MusicClassHelper" / "chrome_profile").mkdir(parents=True)
    cfg = {"chrome_profile": "%LOCALAPPDATA%/MusicClassHelper/chrome_profile"}
    assert cs.check_chrome_profile(cfg, {"LOCALAPPDATA": str(tmp_path)}).status == OK


def test_chrome_profile_missing_folder_is_warn(tmp_path):
    r = cs.check_chrome_profile({"chrome_profile": str(tmp_path / "nope")}, {})
    assert r.status == WARN and "로그인" in r.fix


def test_chrome_profile_unresolved_variable_is_warn():
    assert cs.check_chrome_profile({"chrome_profile": "%NOPE%/x"}, {}).status == WARN


def test_chrome_profile_default_when_not_configured():
    seen = []                                   # 윈도우식 \ 경로라 리눅스에서는 실제 폴더 대신 확인한 경로만 본다
    r = cs.check_chrome_profile({}, {"LOCALAPPDATA": "BASE"}, is_dir=lambda p: seen.append(p) or True)
    assert r.status == OK
    assert seen[0].startswith("BASE") and seen[0].endswith("chrome_profile") and "MusicClassHelper" in seen[0]


# ── 중앙 .env 와 키 이름 ──

def test_central_env_found_and_missing(tmp_path):
    assert cs.check_central_env(tmp_path / ".env").status == OK
    missing = cs.check_central_env(None)
    assert missing.status == FAIL and "OneDrive" in missing.fix


def _by_title(results):
    return {r.title: r for r in results}


def test_env_keys_all_present():
    names = {"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "GEMINI_API_KEY"}
    assert {r.status for r in cs.check_env_keys(names, set())} == {OK}


def test_env_keys_next_public_url_is_accepted():
    r = _by_title(cs.check_env_keys({"NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"}, set()))
    assert r["키 이름 SUPABASE_URL"].status == OK
    assert "NEXT_PUBLIC_SUPABASE_URL" in r["키 이름 SUPABASE_URL"].detail


def test_env_keys_missing_supabase_is_fail():
    r = _by_title(cs.check_env_keys(set(), set()))
    assert r["키 이름 SUPABASE_URL"].status == FAIL
    assert r["키 이름 SUPABASE_SERVICE_ROLE_KEY"].status == FAIL


def test_env_keys_gemini_missing_is_only_warn():
    r = _by_title(cs.check_env_keys({"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"}, set()))
    assert r["키 이름 Gemini 키"].status == WARN


def test_env_keys_gemini_found_via_other_skill_scope():
    r = _by_title(cs.check_env_keys({"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"}, {"GEMINI_API_KEY"}))
    assert r["키 이름 Gemini 키"].status == OK


def test_present_names_ignores_empty_values():
    assert cs._present_names({"A": "x", "B": ""}, {"C": "y", "D": ""}) == {"A", "C"}


def test_env_keys_supabase_missing_is_warn_when_backend_is_not_supabase():
    r = _by_title(cs.check_env_keys(set(), set(), supabase_required=False))
    assert r["키 이름 SUPABASE_URL"].status == WARN
    assert r["키 이름 SUPABASE_SERVICE_ROLE_KEY"].status == WARN
    assert "supabase 가 아니라" in r["키 이름 SUPABASE_URL"].detail
    assert r["키 이름 SUPABASE_URL"].fix                      # 고치는 방법은 그대로 안내


def test_env_keys_supabase_present_is_ok_even_when_not_required():
    r = _by_title(cs.check_env_keys({"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"}, set(), supabase_required=False))
    assert r["키 이름 SUPABASE_URL"].status == OK
    assert r["키 이름 SUPABASE_SERVICE_ROLE_KEY"].status == OK


def test_env_keys_default_still_requires_supabase():
    r = _by_title(cs.check_env_keys(set(), set()))
    assert r["키 이름 SUPABASE_URL"].status == FAIL and "supabase 가 아니라" not in r["키 이름 SUPABASE_URL"].detail


# ── 데이터 폴더·OneDrive ──

def test_data_dir_missing_is_warn(tmp_path):
    results = cs.check_data_dir(tmp_path / "none")
    assert results[0].status == WARN
    assert all(r.status == WARN for r in results)             # 하위 폴더도 모두 없음


def test_data_dir_with_all_subfolders(tmp_path):
    for sub in cs.DATA_SUBFOLDERS:
        (tmp_path / sub).mkdir()
    (tmp_path / "flows" / "a.json").write_text("{}")
    results = cs.check_data_dir(tmp_path)
    assert {r.status for r in results} == {OK}
    assert "1개" in _by_title(results)["데이터 하위 폴더 flows"].detail


def test_data_dir_partial_subfolders(tmp_path):
    (tmp_path / "flows").mkdir()
    r = _by_title(cs.check_data_dir(tmp_path))
    assert r["데이터 하위 폴더 flows"].status == OK
    assert r["데이터 하위 폴더 units"].status == WARN and "build_units.py" in r["데이터 하위 폴더 units"].fix
    assert r["데이터 하위 폴더 notebooklm"].status == WARN


def test_check_data_dir_does_not_create_anything(tmp_path):
    target = tmp_path / "none"
    cs.check_data_dir(target)
    assert not target.exists()


def test_onedrive_from_env_variable(tmp_path):
    assert cs.check_onedrive({"OneDriveCommercial": str(tmp_path)}, home=tmp_path / "h").status == OK


def test_onedrive_from_home_folder(tmp_path):
    (tmp_path / "OneDrive - gyo6.net").mkdir()
    assert cs.check_onedrive({}, home=tmp_path).status == OK


def test_onedrive_missing_is_warn(tmp_path):
    assert cs.check_onedrive({"OneDrive": str(tmp_path / "x")}, home=tmp_path).status == WARN


# ── 포트 ──

def test_port_open_and_closed():
    assert cs.check_port(5180, "수업 비서", "켜세요", probe=lambda p: True).status == OK
    closed = cs.check_port(9233, "수업용 크롬", "수업 사이트 열기를 누르세요", probe=lambda p: False)
    assert closed.status == WARN and "9233" in closed.title and closed.fix


def test_port_is_open_against_real_local_socket():
    import socket
    with socket.socket() as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        assert cs.port_is_open(srv.getsockname()[1]) is True
    assert cs.port_is_open(1) is False                         # 아무도 안 듣는 포트


# ── 포트에 실제로 물어서 수업 비서인지 확인 (진짜 로컬 서버로 시험) ──

import contextlib  # noqa: E402
import http.server  # noqa: E402
import socket  # noqa: E402
import threading  # noqa: E402


@contextlib.contextmanager
def local_http_server(server_version="LessonAssistant/1", status=200):
    """127.0.0.1 의 빈 포트에 작은 HTTP 서버를 잠깐 띄운다. 실제 수업 비서처럼 Server 머리글에 이름을 싣는다."""
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(status)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *a):
            pass
    H.server_version = server_version
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield srv.server_address[1]
    finally:
        srv.shutdown()
        srv.server_close()
        t.join(timeout=5)


def test_identify_assistant_reads_server_name_of_real_assistant_style_server():
    with local_http_server("LessonAssistant/1") as port:
        assert cs.identify_assistant(port).startswith("LessonAssistant")


def test_identify_assistant_reads_name_even_on_403_and_404():
    for status in (403, 404):
        with local_http_server("LessonAssistant/1", status=status) as port:
            assert cs.identify_assistant(port).startswith("LessonAssistant")


def test_identify_assistant_other_http_program_is_not_assistant():
    with local_http_server("SomethingElse/9") as port:
        name = cs.identify_assistant(port)
    assert name is not None and not name.startswith("LessonAssistant")


def test_identify_assistant_ignores_computer_proxy_settings(monkeypatch):
    for var in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
        monkeypatch.setenv(var, "http://127.0.0.1:1")        # 아무도 안 듣는 프록시 — 거치면 실패해야 한다
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)
    with local_http_server("LessonAssistant/1") as port:
        assert cs.identify_assistant(port).startswith("LessonAssistant")


def test_identify_assistant_non_http_listener_returns_none():
    with socket.socket() as srv:                               # 받자마자 HTTP 아닌 글을 보내고 닫는 프로그램
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]

        def talk():
            conn, _ = srv.accept()
            with conn:
                conn.sendall(b"hello, I am not http\r\n")
        t = threading.Thread(target=talk, daemon=True)
        t.start()
        assert cs.identify_assistant(port, timeout=3) is None
        t.join(timeout=5)


def test_identify_assistant_nothing_listening_returns_none():
    with socket.socket() as s:                                 # 빈 포트 하나를 알아낸 뒤 닫아서 아무도 안 듣게 한다
        s.bind(("127.0.0.1", 0))
        free = s.getsockname()[1]
    assert cs.identify_assistant(free, timeout=1) is None


def _never_called(_port):
    raise AssertionError("닫힌 포트에는 HTTP 로 묻지 않아야 해요")


def test_assistant_port_closed_is_warn_and_does_not_ask_http():
    r = cs.check_assistant_port(5180, "bat 를 실행하세요", probe=lambda p: False, identify=_never_called)
    assert r.status == WARN and "5180" in r.title and r.fix == "bat 를 실행하세요"


def test_assistant_port_open_and_is_assistant_is_ok():
    r = cs.check_assistant_port(5180, "x", probe=lambda p: True, identify=lambda p: "LessonAssistant/1 Python/3.13.0")
    assert r.status == OK and "수업 비서" in r.detail


def test_assistant_port_open_but_other_program_is_warn():
    r = cs.check_assistant_port(5180, "x", probe=lambda p: True, identify=lambda p: "nginx/1.25")
    assert r.status == WARN and "수업 비서가 아니에요" in r.detail and "nginx/1.25" in r.detail
    assert "config.json" in r.fix and "port" in r.fix


def test_assistant_port_open_without_server_name_is_warn():
    r = cs.check_assistant_port(5180, "x", probe=lambda p: True, identify=lambda p: "")
    assert r.status == WARN and "수업 비서가 아니에요" in r.detail


def test_assistant_port_open_but_not_http_is_warn():
    r = cs.check_assistant_port(5180, "x", probe=lambda p: True, identify=lambda p: None)
    assert r.status == WARN and "HTTP" in r.detail and r.fix


def test_assistant_port_end_to_end_with_real_local_servers(monkeypatch):
    with local_http_server("LessonAssistant/1") as port:
        assert cs.check_assistant_port(port, "x").status == OK
    with local_http_server("SomethingElse/9") as port:
        assert cs.check_assistant_port(port, "x").status == WARN


# ── config 포트 값 읽기 ──

@pytest.mark.parametrize("cfg,expected", [
    ({}, 5180), ({"port": 6000}, 6000), ({"port": "6001"}, 6001), ({"port": 6002.0}, 6002), ({"port": 65535}, 65535)])
def test_parse_port_accepts_what_the_server_accepts(cfg, expected):
    assert cs.parse_port(cfg, "port", 5180) == (expected, None)


@pytest.mark.parametrize("bad", ["abc", "", None, [5180], {"a": 1}, True, 0, -1, 65536, "70000", float("inf"), float("nan")])
def test_parse_port_rejects_unusable_values_with_fail(bad):
    port, problem = cs.parse_port({"port": bad}, "port", 5180)
    assert port is None and problem.status == FAIL
    assert "port" in problem.title and "1~65535" in problem.fix


def test_parse_port_debug_port_skips_falsy_like_the_server():
    for falsy in (None, 0, ""):
        assert cs.parse_port({"debug_port": falsy}, "debug_port", 9233, falsy_is_default=True) == (9233, None)
    port, problem = cs.parse_port({"debug_port": "abc"}, "debug_port", 9233, falsy_is_default=True)
    assert port is None and problem.status == FAIL and "debug_port" in problem.title


# ── 지도서 폴더 ──

def test_guide_folder_is_never_a_problem(tmp_path):
    here = cs.check_guide_folder(tmp_path)
    gone = cs.check_guide_folder(tmp_path / "없음")
    assert here.status == OK and gone.status == OK
    assert "없어도 됨" in gone.detail


# ── 설정 읽기 ──

def test_load_config_reads_real_file(tmp_path):
    (tmp_path / "config.json").write_text('{"port": 6000}', encoding="utf-8")
    cfg, res = cs.load_config(tmp_path, tmp_path / "config.example.json")
    assert cfg["port"] == 6000 and res.status == OK


def test_load_config_falls_back_to_example_without_writing(tmp_path):
    example = tmp_path / "config.example.json"
    example.write_text('{"port": 5180}', encoding="utf-8")
    data = tmp_path / "data"
    data.mkdir()
    cfg, res = cs.load_config(data, example)
    assert cfg["port"] == 5180 and res.status == WARN
    assert not (data / "config.json").exists()


def test_load_config_broken_json_is_fail(tmp_path):
    (tmp_path / "config.json").write_text("{깨진", encoding="utf-8")
    cfg, res = cs.load_config(tmp_path, tmp_path / "x.json")
    assert cfg == {} and res.status == FAIL


# ── 전체 실행: 값 비출력, 종료 코드 ──

SENTINEL = "SECRET-VALUE-MUST-NOT-APPEAR-123"


@pytest.fixture
def fake_world(tmp_path, monkeypatch):
    env_file = tmp_path / "96. 인증" / ".env"
    env_file.parent.mkdir()
    env_file.write_text("x")
    data = tmp_path / "data"
    data.mkdir()
    values = {"SUPABASE_URL": SENTINEL, "SUPABASE_SERVICE_ROLE_KEY": SENTINEL, "GEMINI_API_KEY": SENTINEL}
    monkeypatch.setattr(cs.skill_env, "central_env_path", lambda: env_file)
    monkeypatch.setattr(cs.skill_env, "env_values", lambda skill=None: dict(values))
    monkeypatch.setattr(cs.skill_env, "data_dir", lambda *a, **k: data)
    monkeypatch.setattr(cs, "port_is_open", lambda *a, **k: True)
    monkeypatch.setattr(cs, "check_port", lambda port, label, note, probe=None: cs.Result(OK, f"{port}번 포트 ({label})", "열림"))
    monkeypatch.setattr(cs, "check_chrome_exe", lambda *a, **k: cs.Result(OK, "크롬 실행 파일", "찾음"))
    monkeypatch.setattr(cs, "check_node", lambda *a, **k: cs.Result(OK, "Node.js", "v22"))
    monkeypatch.setattr(cs, "check_gemini_cli", lambda *a, **k: cs.Result(OK, "Gemini CLI", "ok"))
    monkeypatch.setattr(cs, "check_packages", lambda *a, **k: [cs.Result(OK, "패키지 requests", "설치됨")])
    monkeypatch.setattr(cs, "check_python", lambda *a, **k: cs.Result(OK, "Python 버전", "3.13.0"))
    # T46: 새 점검 두 가지도 실제 python 실행·5180 포트 접속 없이 돌게 한다(검사 내용은 아래 전용 시험에서 따로 확인)
    monkeypatch.setattr(cs, "check_python_launchers", lambda *a, **k: cs.Result(OK, "Python 실행기", "둘 다 3.13.0"))
    monkeypatch.setattr(cs, "check_assistant_port", lambda port, note, probe=None, identify=None: cs.Result(OK, f"{port}번 포트 (수업 비서)", "켜짐"))
    return values


def test_run_checks_never_prints_secret_values(fake_world):
    text = cs.render(cs.run_checks())
    assert SENTINEL not in text
    assert "SUPABASE_SERVICE_ROLE_KEY" in text                # 이름은 보여 준다


def test_main_exit_code_zero_without_fail(fake_world, capsys):
    assert cs.main() == 0
    assert "✅" in capsys.readouterr().out


def test_main_exit_code_one_with_fail(fake_world, monkeypatch, capsys):
    monkeypatch.setattr(cs.skill_env, "env_values", lambda skill=None: {})
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("NEXT_PUBLIC_SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    assert cs.main() == 1
    out = capsys.readouterr().out
    assert "❌" in out and "고치기" in out


def _with_config(monkeypatch, cfg):
    monkeypatch.setattr(cs, "load_config", lambda data, example: (cfg, cs.Result(OK, "설정 파일 config.json", "읽음")))


@pytest.mark.parametrize("bad", ["abc", None, [5180], True, 0, 70000])
def test_run_checks_does_not_crash_on_unusable_port_and_reports_fail(fake_world, monkeypatch, capsys, bad):
    _with_config(monkeypatch, {"port": bad})
    results = cs.run_checks()                                  # 예전에는 int("abc") 에서 멈췄다
    problems = [r for r in results if r.title == "설정 port"]
    assert len(problems) == 1 and problems[0].status == FAIL
    assert not any("수업 비서" in r.title and "번 포트" in r.title for r in results)   # 못 쓰는 포트는 열어 보지 않는다
    assert cs.main() == 1
    assert "설정 port" in capsys.readouterr().out


def test_run_checks_does_not_crash_on_unusable_debug_port(fake_world, monkeypatch):
    _with_config(monkeypatch, {"port": 5180, "debug_port": "abc"})
    results = cs.run_checks()
    assert [r.status for r in results if r.title == "설정 debug_port"] == [FAIL]
    assert any("5180번 포트" in r.title for r in results)      # 멀쩡한 port 점검은 그대로 한다


def test_run_checks_usable_ports_have_no_port_problem(fake_world, monkeypatch):
    _with_config(monkeypatch, {"port": "5180", "debug_port": 9233})
    assert not [r for r in cs.run_checks() if r.title in ("설정 port", "설정 debug_port")]


def _without_supabase_keys(fake_world, monkeypatch):
    monkeypatch.setattr(cs.skill_env, "env_values", lambda skill=None: {})
    for name in ("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("backend", ["http", "schedule_api", None, ""])
def test_run_checks_non_supabase_backend_makes_missing_keys_only_warn(fake_world, monkeypatch, backend):
    _without_supabase_keys(fake_world, monkeypatch)
    _with_config(monkeypatch, {"port": 5180, "schedule_backend": backend})
    by = _by_title(cs.run_checks())
    assert by["키 이름 SUPABASE_URL"].status == WARN
    assert by["키 이름 SUPABASE_SERVICE_ROLE_KEY"].status == WARN
    assert cs.main() == 0                                      # ❌ 가 없으니 종료 코드 0


@pytest.mark.parametrize("cfg", [{"port": 5180}, {"port": 5180, "schedule_backend": "supabase"}])
def test_run_checks_supabase_backend_or_unset_still_fails_without_keys(fake_world, monkeypatch, cfg):
    _without_supabase_keys(fake_world, monkeypatch)
    _with_config(monkeypatch, cfg)
    by = _by_title(cs.run_checks())
    assert by["키 이름 SUPABASE_URL"].status == FAIL
    assert by["키 이름 SUPABASE_SERVICE_ROLE_KEY"].status == FAIL
    assert cs.main() == 1


def test_run_checks_includes_python_launcher_result(fake_world):
    assert any(r.title.startswith("Python 실행기") for r in cs.run_checks())


def test_render_shows_fix_only_for_non_ok():
    text = cs.render([cs.Result(OK, "가", "좋음", "무시되는 방법"), cs.Result(FAIL, "나", "나쁨", "이렇게 고침")])
    assert "무시되는 방법" not in text and "이렇게 고침" in text
    assert "✅ 1  ⚠ 0  ❌ 1" in text
