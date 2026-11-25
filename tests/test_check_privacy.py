"""tools/check_privacy.py 시험 — 네트워크·비밀값 없이, 전부 가짜 예시로 한다.

시험 파일 자체가 개인정보 검사에 걸리지 않도록, 위험해 보이는 예시는
조각을 이어 붙여 실행할 때 만든다(소스에는 완성된 모양이 없다).
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_privacy as cp  # noqa: E402


def kinds(text):
    return [k for k, _ in cp.scan_line(text)]


# ---------- 전화번호 ----------

def test_mobile_phone_is_found():
    fake = "010" + "-1234-" + "5678"
    assert kinds(f"연락처: {fake}") == ["전화번호 모양"]


def test_phone_without_dashes_is_found():
    fake = "010" + "12345678"
    assert "전화번호 모양" in kinds(f"tel={fake}")


def test_seoul_and_area_phone_are_found():
    assert "전화번호 모양" in kinds("02" + "-345-" + "6789")
    assert "전화번호 모양" in kinds("031" + "-345-" + "6789")


@pytest.mark.parametrize("text", ["000-0000", "010-0000-0000", "010-1111-1111", "전화 000-0000 으로"])
def test_placeholder_phone_is_ignored(text):
    assert kinds(text) == []


def test_dates_and_versions_are_not_phones():
    assert kinds("2026-11-25 에 v1.2.3 배포, 줄 번호 12345678") == []


# ---------- 주민등록번호 ----------

def test_rrn_shape_is_found_once():
    fake = "900101" + "-" + "1234567"
    assert kinds(f"번호 {fake}") == ["주민등록번호 모양"]


def test_placeholder_rrn_is_ignored():
    assert kinds("000000-0000000") == []


# ---------- 이메일 ----------

def test_email_is_found():
    fake = "student" + "@" + "school.go.kr"
    assert kinds(f"문의 {fake}") == ["이메일 주소"]


@pytest.mark.parametrize(
    "text",
    ["a@example.com", "a@mail.example.org", "12345+name@users.noreply.github.com", "git@localhost"],
)
def test_example_email_is_ignored(text):
    assert kinds(text) == []


# ---------- 키·토큰 ----------

@pytest.mark.parametrize(
    "fake, label",
    [
        ("sk-" + "a1" * 12, "sk- 로 시작하는 키"),
        ("AIza" + "B" * 35, "구글 API 키(AIza)"),
        ("ghp_" + "c" * 36, "GitHub 토큰"),
        ("github_pat_" + "d" * 30, "GitHub 토큰(github_pat_)"),
        ("xoxb-" + "1234567890-abcdef", "Slack 토큰"),
        ("AKIA" + "E" * 16, "AWS 접근 키"),
        ("-----BEGIN " + "RSA PRIVATE KEY-----", "비공개 키 머리말"),
        ("eyJ" + "a" * 12 + ".eyJ" + "b" * 12 + "." + "c" * 8, "JWT 토큰"),
    ],
)
def test_secret_shapes_are_found(fake, label):
    assert label in kinds(f'KEY="{fake}"')


def test_short_sk_word_is_not_a_key():
    assert kinds("sk-learn 과 task-list 는 키가 아니다") == []


# ---------- 사용자 폴더 경로 ----------

@pytest.mark.parametrize(
    "path",
    [
        "C:" + "\\Users\\" + "tester\\Documents",
        "c:" + "\\\\Users\\\\" + "tester\\\\Documents",
        "D:" + "/Users/" + "tester/Documents",
    ],
)
def test_real_user_path_is_found(path):
    assert "실제 사용자 폴더 경로" in kinds(f"path = r'{path}'")


@pytest.mark.parametrize(
    "path",
    [
        "C:" + "\\Users\\" + "<이름>\\Documents",
        "C:" + "\\Users\\" + "Public",
        "C:" + "\\Users\\" + "%USERNAME%\\x",
        "%USERPROFILE%\\Documents",
        "C:" + "\\Users\\" + "{user}\\x",
    ],
)
def test_example_path_is_ignored(path):
    assert kinds(path) == []


# ---------- 건너뛰기·가리기 ----------

def test_privacy_ok_marker_skips_the_line():
    fake = "010" + "-1234-" + "5678"
    assert kinds(f"{fake}  # privacy-ok") == []


def test_mask_hides_most_of_the_value():
    secret = "sk-" + "z9" * 12
    masked = cp.mask(secret)
    assert secret not in masked
    assert masked.startswith("sk")
    assert "길이 27" in masked


def test_rendered_finding_never_contains_full_secret():
    secret = "ghp_" + "q" * 36
    diff = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -0,0 +1 @@\n+T = '" + secret + "'\n"
    out = "\n".join(f.render() for f in cp.scan_diff(diff))
    assert out and secret not in out


# ---------- diff 읽기 ----------

SAMPLE_DIFF = (
    "diff --git a/a.py b/a.py\n"
    "index 111..222 100644\n"
    "--- a/a.py\n"
    "+++ b/a.py\n"
    "@@ -3,2 +10,3 @@ def f():\n"
    " 안 바뀐 줄 " + "010" + "-1234-" + "5678\n"          # 맥락 줄: 검사 안 함
    "-지운 줄 " + "010" + "-1234-" + "5678\n"              # 지운 줄: 검사 안 함
    "+새 줄 정상\n"
    "+새 줄 " + "010" + "-1234-" + "5678\n"                # 추가 줄: 검사함(줄 번호 12)
    "diff --git a/b.md b/b.md\n"
    "new file mode 100644\n"
    "--- /dev/null\n"
    "+++ b/b.md\n"
    "@@ -0,0 +1,2 @@\n"
    "+# 제목\n"
    "+" + "student" + "@" + "school.go.kr\n"
)


def test_only_added_lines_are_checked_with_right_positions():
    findings = cp.scan_diff(SAMPLE_DIFF)
    assert [(f.path, f.line_no, f.kind) for f in findings] == [
        ("a.py", 12, "전화번호 모양"),
        ("b.md", 2, "이메일 주소"),
    ]


def test_empty_diff_has_no_findings():
    assert cp.scan_diff("") == []


def test_deleted_secret_is_not_reported():
    secret = "sk-" + "a1" * 12
    diff = "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +0,0 @@\n-KEY=" + secret + "\n"
    assert cp.scan_diff(diff) == []


# ---------- 명령줄(main) ----------

def test_main_stdin_clean_returns_0(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(""))
    assert cp.main(["--stdin"]) == 0
    assert "찾지 못했어요" in capsys.readouterr().out


def test_main_stdin_finding_returns_1_and_warn_only_returns_0(monkeypatch, capsys):
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO(SAMPLE_DIFF))
    assert cp.main(["--stdin"]) == 1
    out = capsys.readouterr().out
    assert "a.py:12" in out and "2곳" in out

    monkeypatch.setattr(sys, "stdin", io.StringIO(SAMPLE_DIFF))
    assert cp.main(["--stdin", "--warn-only"]) == 0


@pytest.mark.skipif(shutil.which("git") is None, reason="git 이 없음")
def test_main_reads_staged_changes_from_a_real_repo(tmp_path, monkeypatch, capsys):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    fake = "010" + "-1234-" + "5678"
    (tmp_path / "memo.txt").write_text(f"학생A 연락처 {fake}\n", encoding="utf-8")
    (tmp_path / "ok.txt").write_text("학생A 연락처 000-0000\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    git("add", "ok.txt")
    assert cp.main([]) == 0  # 올릴 것에는 예시만 있음

    git("add", "memo.txt")
    assert cp.main([]) == 1
    out = capsys.readouterr().out
    assert "memo.txt:1" in out and fake not in out
