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
    assert kinds("setup-python@v5.1.0 lodash@4.17.21 git@github.com") == []


@pytest.mark.parametrize("text", ["v010-1234-5678", "010-1234-5678x", "build010-1234-5678"])
def test_phone_attached_to_letters_is_ignored(text):
    assert kinds(text) == []


@pytest.mark.parametrize("text", [
    "기관코드 0201234567",        # 가운데 묶음이 0 으로 시작 (NEIS 10자리 코드 모양)
    "코드 7010012345 와 0310234567",
    "02-0123-4567",
])
def test_ten_digit_codes_with_zero_middle_group_are_not_phones(text):
    # T78: 전화번호 가운데 묶음은 1~9 로 시작한다
    assert kinds(text) == []


def test_real_looking_phone_with_nonzero_middle_group_is_still_found():
    assert "전화번호 모양" in kinds("02" + "-1234-" + "5678")
    assert "전화번호 모양" in kinds("010" + "-9876-" + "5432")


# ---------- 주민등록번호 ----------

def test_rrn_shape_is_found_once():
    fake = "900101" + "-" + "1234567"
    assert kinds(f"번호 {fake}") == ["주민등록번호 모양"]


def test_placeholder_rrn_is_ignored():
    assert kinds("000000-0000000") == []


@pytest.mark.parametrize("text", ["991332-1234567", "9001011234567", "2026112512345", "x900101-1234567y"])
def test_invalid_date_or_alphanumeric_rrn_boundary_is_ignored(text):
    assert kinds(text) == []


def test_rrn_leap_day_uses_century_digit():
    before_1900_leap = "000229" + "-" + "1234567"
    year_2000_leap = "000229" + "-" + "3234567"
    assert kinds(before_1900_leap) == []
    assert kinds(year_2000_leap) == ["주민등록번호 모양"]


def _make_rrn(front12: str) -> str:
    """앞 12자리에 맞는 검증 숫자를 붙여 13자리를 만든다(시험용 가짜 번호)."""
    total = sum(int(d) * w for d, w in zip(front12, cp.RRN_WEIGHTS))
    return front12 + str((11 - total % 11) % 10)


def test_compact_rrn_with_valid_date_and_checksum_is_found():
    fake = _make_rrn("900101" + "123456")
    assert cp._valid_rrn_checksum(fake)
    assert kinds(f"번호 {fake}") == ["주민등록번호 모양"]


def test_compact_13_digits_with_wrong_checksum_is_ignored():
    good = _make_rrn("900101" + "123456")
    bad = good[:-1] + str((int(good[-1]) + 1) % 10)
    assert kinds(f"번호 {bad}") == []


@pytest.mark.parametrize("text", ["1732000000000", "견적 2026112512345", "id 1710123456780x"])
def test_timestamps_and_codes_are_not_compact_rrn(text):
    assert kinds(text) == []


def test_compact_rrn_checksum_helper_rejects_bad_input():
    assert cp._valid_rrn_checksum("123") is False
    assert cp._valid_rrn_checksum("abcdefghijklm") is False


# ---------- 이메일 ----------

def test_email_is_not_scanned():
    fake = "student" + "@" + "school.go.kr"
    assert kinds(f"문의 {fake}") == []


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
        ("ntn_" + "f" * 24, "Notion API 토큰(ntn_)"),
        ("secret_" + "g" * 43, "Notion 비밀 토큰(secret_)"),
        ("GOCSPX-" + "h" * 24, "Google OAuth 클라이언트 비밀값"),
        ("db_id=" + "a" * 32, "Notion 데이터베이스 ID"),
    ],
)
def test_secret_shapes_are_found(fake, label):
    assert label in kinds(f'KEY="{fake}"')


@pytest.mark.parametrize("text", [
    "secret_key_name = 1",
    "client_secret_id",
    "secret_" + "g" * 24,          # 짧은 변수명·자리표시는 Notion 토큰 길이(43자)가 아님
    "secret_" + "g" * 30 + "-x",
])
def test_short_secret_words_are_not_notion_tokens(text):
    assert "Notion 비밀 토큰(secret_)" not in kinds(text)


def test_secret_with_notion_token_length_is_found():
    assert "Notion 비밀 토큰(secret_)" in kinds("secret_" + "A1" * 22)


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


@pytest.mark.parametrize("name", ["…", "...", "xxx", "XXXX", "***"])
def test_filler_user_names_in_paths_are_examples(name):
    # T78: 자리를 채워 둔 표시는 예시로 본다
    assert kinds("C:" + "\\Users\\" + name + "\\Documents") == []
    assert kinds("/c/Users/" + name + "/x") == []


def test_filler_user_name_followed_by_punctuation_is_still_an_example():
    # 설명 글 속 "C:\\Users\\xxx, C:\\Users\\..." 처럼 구두점이 붙어도 예시
    text = "예: C:" + "\\Users\\" + "xxx, C:" + "\\Users\\" + "..., (C:" + "\\Users\\" + "…)"
    assert kinds(text) == []


def test_user_path_is_warning_only_in_findings():
    finding = cp.Finding("a.py", 1, "실제 사용자 폴더 경로", "C:***")
    assert finding.warn_only is True
    assert cp.Finding("a.py", 1, "전화번호 모양", "01***").warn_only is False


def test_git_bash_user_path_is_found():
    path = "/" + "c" + "/Users/" + "tester" + "/Documents/file.txt"
    assert "실제 사용자 폴더 경로" in kinds(path)


def test_git_bash_placeholder_path_is_ignored():
    assert kinds("/c/Users/<이름>/Documents/file.txt") == []


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
    ]


def test_empty_diff_has_no_findings():
    assert cp.scan_diff("") == []


def test_env_file_is_flagged_by_path_even_without_added_content():
    diff = (
        "diff --git a/.env b/.env\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/.env\n"
    )
    findings = cp.scan_diff(diff)
    assert [(f.path, f.line_no, f.kind) for f in findings] == [
        (".env", 0, "환경변수 파일")
    ]


def test_env_example_file_is_allowed():
    diff = (
        "diff --git a/.env.example b/.env.example\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/.env.example\n"
    )
    assert cp.scan_diff(diff) == []


def test_empty_new_env_file_is_found_from_diff_git_line():
    # 내용이 빈 새 파일은 `---`/`+++` 줄이 없다(T78)
    diff = "diff --git a/skills/x/.env b/skills/x/.env\nnew file mode 100644\nindex 0000000..e69de29\n"
    findings = cp.scan_diff(diff)
    assert [(f.path, f.line_no, f.kind) for f in findings] == [("skills/x/.env", 0, "환경변수 파일")]


def test_env_file_is_reported_once_even_with_plus_header():
    diff = (
        "diff --git a/.env.local b/.env.local\nnew file mode 100644\n"
        "--- /dev/null\n+++ b/.env.local\n@@ -0,0 +1 @@\n+A=1\n"
    )
    assert [f.kind for f in cp.scan_diff(diff)] == ["환경변수 파일"]


def test_deleted_env_file_is_not_flagged():
    diff = "diff --git a/.env b/.env\ndeleted file mode 100644\nindex e69de29..0000000\n"
    assert cp.scan_diff(diff) == []
    diff2 = (
        "diff --git a/.env b/.env\ndeleted file mode 100644\n"
        "--- a/.env\n+++ /dev/null\n@@ -1 +0,0 @@\n-A=1\n"
    )
    assert cp.scan_diff(diff2) == []


def test_env_example_from_diff_git_line_is_allowed_and_spaces_in_path_work():
    assert cp.scan_diff("diff --git a/.env.example b/.env.example\nnew file mode 100644\n") == []
    assert list(cp.iter_changed_paths("diff --git a/a b/x.txt b/a b/x.txt\nnew file mode 100644\n")) == ["a b/x.txt"]


def test_added_line_starting_with_two_plus_signs_is_scanned():
    diff = (
        "diff --git a/a.txt b/a.txt\n"
        "--- a/a.txt\n"
        "+++ b/a.txt\n"
        "@@ -0,0 +1 @@\n"
        "+++" + " " + "010" + "-1234-" + "5678" + "\n"
    )
    findings = cp.scan_diff(diff)
    assert [(f.path, f.line_no, f.kind) for f in findings] == [
        ("a.txt", 1, "전화번호 모양")
    ]


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
    assert "a.py:12" in out and "1곳" in out

    monkeypatch.setattr(sys, "stdin", io.StringIO(SAMPLE_DIFF))
    assert cp.main(["--stdin", "--warn-only"]) == 0




def _path_only_diff():
    path = "C:" + "\\Users\\" + "tester\\Documents"
    return "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -0,0 +1 @@\n+p = r'" + path + "'\n"


def test_main_user_path_only_is_warning_and_returns_0(monkeypatch, capsys):
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO(_path_only_diff()))
    assert cp.main(["--stdin"]) == 0
    out = capsys.readouterr().out
    assert "a.py:1" in out and "경고" in out and "🚨" not in out
    assert "tester" not in out


def test_main_user_path_plus_phone_still_returns_1(monkeypatch, capsys):
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO(_path_only_diff() + SAMPLE_DIFF))
    assert cp.main(["--stdin"]) == 1
    out = capsys.readouterr().out
    assert "🚨 의심되는 줄 1곳" in out and "경고 1곳" in out


def test_main_stdin_decodes_bytes_with_replacement(monkeypatch, capsys):
    import io

    class BinaryStdin:
        buffer = io.BytesIO(SAMPLE_DIFF.encode("utf-8") + b"\xff")

    monkeypatch.setattr(sys, "stdin", BinaryStdin())
    assert cp.main(["--stdin"]) == 1
    assert "a.py:12" in capsys.readouterr().out


def test_diff_args_do_not_consume_script_flags(monkeypatch):
    captured = []

    def fake_read(extra_args):
        captured.extend(extra_args)
        return ""

    monkeypatch.setattr(cp, "read_staged_diff", fake_read)
    assert cp.main(["--diff-args", "HEAD~1", "--cached", "--warn-only"]) == 0
    assert captured == ["HEAD~1", "--cached"]

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
