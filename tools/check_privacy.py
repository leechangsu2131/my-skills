#!/usr/bin/env python3
"""커밋 전 개인정보·비밀값 검사 도구.

`git diff --staged` 에서 **새로 추가된 줄**만 읽어, 아래처럼 생긴 것이 있으면 경고합니다.
  - 전화번호 모양 (휴대전화·지역번호)
  - 주민등록번호 모양 (앞 6자리-뒤 7자리)
  - API 키·토큰 모양 (sk-, AIza, ghp_, github_pat_, xox*, AKIA, ntn_, secret_, GOCSPX-, JWT, 데이터베이스 ID)
  - 실제 사용자 폴더 경로 (Windows 경로, /c/Users/<이름>)
  - .env 파일 자체 (예시용 .env.example 등은 제외)

쓰는 법:
  python tools/check_privacy.py              # 커밋 올릴 변경(staged)을 검사
  python tools/check_privacy.py --diff-args HEAD~1   # 다른 diff 를 검사
  git diff --staged | python tools/check_privacy.py --stdin
  python tools/check_privacy.py --warn-only  # 경고만 하고 항상 0 으로 끝냄

끝내는 값: 의심 줄이 없으면 0, 있으면 1 (--warn-only 면 항상 0).

알아 둘 점:
  - 찾은 값은 화면에 **가려서** 보여 줍니다(앞 2글자만). 경고 글이 또 다른 유출이 되지 않게.
  - 예시용 값(000-0000, <이름>, example.com, %USERNAME% 등)은 통과시킵니다.
  - 일부러 넣은 줄이면 그 줄 끝에 `privacy-ok` 를 적으면 건너뜁니다.
  - 학생·교사 **이름**은 모양만으로 알 수 없어 찾지 못합니다. diff 를 눈으로도 꼭 확인하세요.
  - 비밀값이 한 번이라도 푸시됐다면 이 도구로는 되돌릴 수 없습니다. 키를 새로 발급하세요.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from dataclasses import dataclass
from typing import Iterable, Iterator

SKIP_MARK = "privacy-ok"

# C:\Users\<여기> 자리에 이런 값이 있으면 예시로 본다
SAFE_USER_DIRS = {
    "public",
    "default",
    "default user",
    "all users",
    "username",
    "user",
    "name",
    "me",
    "you",
    "yourname",
    "your-name",
    "이름",
    "사용자",
    "계정",
    "내이름",
}

PHONE_RE = re.compile(
    r"(?<![0-9A-Za-z])("
    r"01[016789][-. ]?\d{3,4}[-. ]?\d{4}"  # 휴대전화
    r"|0(?:2|[3-6][1-5]|70)[-. ]?\d{3,4}[-. ]?\d{4}"  # 서울·지역·인터넷전화
    r")(?![0-9A-Za-z])"
)
# 주민번호는 구분 기호가 있고 앞 6자리가 실제 달력 날짜인 경우만 찾는다.
RRN_RE = re.compile(r"(?<![0-9A-Za-z])(\d{6})[- ]([0-9]\d{6})(?![0-9A-Za-z])")
WIN_USER_RE = re.compile(r"(?i)(?<![A-Za-z0-9])[A-Z]:[\\/]+Users[\\/]+([^\\/\s\"'<>|:*?%]+)")
GIT_BASH_USER_RE = re.compile(r"(?i)(?<![A-Za-z0-9])/[a-z]/Users/([^/\s\"'<>|:*?%]+)")
ENV_SAFE_NAMES = {".env.example", ".env.sample", ".env.template", ".env.dist"}

# (이름, 정규식) — 키·토큰 모양
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("sk- 로 시작하는 키", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("구글 API 키(AIza)", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("GitHub 토큰", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("GitHub 토큰(github_pat_)", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}")),
    ("Slack 토큰", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("AWS 접근 키", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("비공개 키 머리말", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("JWT 토큰", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}")),
    ("Notion API 토큰(ntn_)", re.compile(r"\bntn_[A-Za-z0-9_-]{16,}\b")),
    ("Notion 비밀 토큰(secret_)", re.compile(r"\bsecret_[A-Za-z0-9_-]{16,}\b")),
    ("Google OAuth 클라이언트 비밀값", re.compile(r"\bGOCSPX-[A-Za-z0-9_-]{20,}\b")),
    ("Notion 데이터베이스 ID", re.compile(r"(?i)\b(?:notion[_ -]?)?(?:database|db)[_ -]?id\s*[:=]\s*([0-9a-f]{32})\b")),
]


@dataclass(frozen=True)
class Finding:
    path: str
    line_no: int
    kind: str
    masked: str

    def render(self) -> str:
        where = f"{self.path}:{self.line_no}" if self.line_no else self.path
        return f"⚠ {where}  [{self.kind}]  {self.masked}"


def mask(value: str) -> str:
    """찾은 값을 앞 2글자만 남기고 가린다."""
    value = value.strip()
    if len(value) <= 2:
        return "*" * len(value)
    return value[:2] + "*" * min(len(value) - 2, 8) + f" (길이 {len(value)})"


def _is_placeholder_digits(text: str) -> bool:
    """숫자가 전부 같은 수(0000…)거나 0·1 로만 이뤄진 자리표시용 값인지."""
    digits = re.sub(r"\D", "", text)
    return not digits or len(set(digits)) == 1


def _valid_rrn_date(value: str, code: str) -> bool:
    """주민번호 앞 6자리 YYMMDD와 뒷자리 첫 숫자로 실제 생년월일인지 확인한다."""
    try:
        yy, mm, dd = int(value[:2]), int(value[2:4]), int(value[4:6])
        digit = int(code[0])
        if digit in (1, 2, 5, 6):
            year = 1900 + yy
        elif digit in (3, 4, 7, 8):
            year = 2000 + yy
        elif digit in (0, 9):
            year = 1800 + yy
        else:
            return False
        return _valid_date(year, mm, dd)
    except (TypeError, ValueError):
        return False


def _valid_date(year: int, month: int, day: int) -> bool:
    try:
        date(year, month, day)
        return True
    except ValueError:
        return False


def _is_safe_user_dir(value: str) -> bool:
    user = value.strip().lower()
    return (
        user in SAFE_USER_DIRS
        or user.startswith("<")
        or user.startswith("$")
        or user.startswith("{")
    )


def _is_env_file(path: str) -> bool:
    name = path.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return name.startswith(".env") and name not in ENV_SAFE_NAMES and not name.endswith(
        (".example", ".sample", ".template", ".dist")
    )


def scan_line(text: str) -> list[tuple[str, str]]:
    """한 줄을 검사해 (종류, 찾은 값) 목록을 돌려준다."""
    if SKIP_MARK in text:
        return []
    found: list[tuple[str, str]] = []

    for name, pattern in SECRET_PATTERNS:
        for m in pattern.finditer(text):
            value = m.group(1) if m.lastindex else m.group(0)
            found.append((name, value))

    valid_rrns = [
        m for m in RRN_RE.finditer(text)
        if _valid_rrn_date(m.group(1), m.group(2)) and not _is_placeholder_digits(m.group(0))
    ]
    for m in valid_rrns:
        found.append(("주민등록번호 모양", m.group(0)))

    rrn_spans = [m.span() for m in valid_rrns]
    for m in PHONE_RE.finditer(text):
        if _is_placeholder_digits(re.sub(r"\D", "", m.group(0))[-7:]):
            continue
        if any(start <= m.start() and m.end() <= end for start, end in rrn_spans):
            continue
        found.append(("전화번호 모양", m.group(0)))

    for pattern in (WIN_USER_RE, GIT_BASH_USER_RE):
        for m in pattern.finditer(text):
            if _is_safe_user_dir(m.group(1)):
                continue
            found.append(("실제 사용자 폴더 경로", m.group(0)))

    return found


def iter_changed_paths(diff_text: str) -> Iterator[str]:
    """diff 에서 변경된 파일 경로를 돌려준다."""
    in_hunk = False
    for raw in diff_text.splitlines():
        if raw.startswith("diff --git "):
            in_hunk = False
            continue
        if raw.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk and raw.startswith("+++ "):
            target = raw[4:].strip()
            if target == "/dev/null":
                continue
            yield target[2:] if target.startswith("b/") else target


def iter_added_lines(diff_text: str) -> Iterator[tuple[str, int, str]]:
    """unified diff 에서 새로 추가된 줄만 (파일, 줄 번호, 내용) 으로 돌려준다."""
    path = "(알 수 없음)"
    new_line = 0
    in_hunk = False
    for raw in diff_text.splitlines():
        if raw.startswith("diff --git "):
            in_hunk = False
            path = "(알 수 없음)"
            continue
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
        if hunk:
            new_line = int(hunk.group(1))
            in_hunk = True
            continue
        if in_hunk:
            # hunk 안의 +++ 로 시작하는 실제 추가 줄도 파일 헤더로 오인하지 않는다.
            if raw.startswith("+"):
                yield path, new_line, raw[1:]
                new_line += 1
            elif raw.startswith("-") or raw.startswith("\\"):
                continue
            else:
                new_line += 1
            continue
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            if target == "/dev/null":
                continue
            path = target[2:] if target.startswith("b/") else target


def scan_diff(diff_text: str) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_changed_paths(diff_text):
        if _is_env_file(path):
            findings.append(Finding(path, 0, "환경변수 파일", "파일 자체"))
    for path, line_no, text in iter_added_lines(diff_text):
        for kind, value in scan_line(text):
            findings.append(Finding(path, line_no, kind, mask(value)))
    return findings


def read_staged_diff(extra_args: Iterable[str] = ()) -> str:
    cmd = ["git", "diff", "--staged", "-U0", "--no-color", "--no-ext-diff", *extra_args]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"git diff 실패: {result.stderr.strip() or result.returncode}")
    return result.stdout


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # 윈도우 콘솔에서도 한글이 깨지지 않게
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="커밋 전 개인정보·비밀값 모양 검사")
    parser.add_argument("--stdin", action="store_true", help="git diff 결과를 표준 입력에서 읽기")
    parser.add_argument("--diff-args", nargs="*", default=[], metavar="ARG", help="git diff --staged 뒤에 붙일 인자")
    parser.add_argument("--warn-only", action="store_true", help="경고만 하고 항상 0 으로 끝냄")
    args, unknown_args = parser.parse_known_args(argv)
    diff_args = [*args.diff_args, *unknown_args]

    try:
        if args.stdin:
            buffer = getattr(sys.stdin, "buffer", None)
            diff_text = buffer.read().decode("utf-8", errors="replace") if buffer is not None else sys.stdin.read()
        else:
            diff_text = read_staged_diff(diff_args)
    except RuntimeError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 2

    findings = scan_diff(diff_text)
    if not findings:
        print("✅ 개인정보·비밀값 모양을 찾지 못했어요. (이름은 못 찾으니 diff 를 눈으로도 확인하세요)")
        return 0

    print(f"🚨 의심되는 줄 {len(findings)}곳 (찾은 값은 가려서 보여 줍니다):")
    for f in findings:
        print("  " + f.render())
    print("\n진짜 값이면 지우고 '학생A', '000-0000', '<이름>' 같은 예시로 바꾸세요.")
    print(f"예시·일부러 넣은 줄이면 줄 끝에 `{SKIP_MARK}` 를 적으면 건너뜁니다.")
    return 0 if args.warn_only else 1


if __name__ == "__main__":
    sys.exit(main())
