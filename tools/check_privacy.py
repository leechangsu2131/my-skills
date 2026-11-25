#!/usr/bin/env python3
"""커밋 전 개인정보·비밀값 검사 도구.

`git diff --staged` 에서 **새로 추가된 줄**만 읽어, 아래처럼 생긴 것이 있으면 경고합니다.
  - 전화번호 모양 (휴대전화·지역번호)
  - 주민등록번호 모양 (앞 6자리-뒤 7자리)
  - 이메일 주소
  - API 키·토큰 모양 (sk-, AIza, ghp_, github_pat_, xox*, AKIA, 비공개 키 머리말, JWT)
  - 실제 사용자 폴더 경로 (C:\\Users\\<이름>\\…)

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
from dataclasses import dataclass
from typing import Iterable, Iterator

SKIP_MARK = "privacy-ok"

# 예시·가짜 값으로 보고 통과시킬 이메일 주소 끝부분
SAFE_EMAIL_DOMAINS = (
    "example.com",
    "example.org",
    "example.net",
    "users.noreply.github.com",
    "localhost",
    "test.com",
    "anthropic.com",
)

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
    r"(?<![\d-])("
    r"01[016789][-. ]?\d{3,4}[-. ]?\d{4}"  # 휴대전화
    r"|0(?:2|[3-6][1-5]|70)[-. ]?\d{3,4}[-. ]?\d{4}"  # 서울·지역·인터넷전화
    r")(?![\d-])"
)
RRN_RE = re.compile(r"(?<!\d)(\d{6})[- ]?([1-4]\d{6})(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
WIN_USER_RE = re.compile(r"(?i)\b[A-Z]:(?:\\\\|\\|/)Users(?:\\\\|\\|/)([^\\/\s\"'<>|:*?%]+)")

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


def _email_is_safe(domain: str) -> bool:
    domain = domain.lower()
    return any(domain == d or domain.endswith("." + d) for d in SAFE_EMAIL_DOMAINS)


def scan_line(text: str) -> list[tuple[str, str]]:
    """한 줄을 검사해 (종류, 찾은 값) 목록을 돌려준다."""
    if SKIP_MARK in text:
        return []
    found: list[tuple[str, str]] = []

    for name, pattern in SECRET_PATTERNS:
        for m in pattern.finditer(text):
            found.append((name, m.group(0)))

    for m in RRN_RE.finditer(text):
        if not _is_placeholder_digits(m.group(0)):
            found.append(("주민등록번호 모양", m.group(0)))

    rrn_spans = [m.span() for m in RRN_RE.finditer(text) if not _is_placeholder_digits(m.group(0))]
    for m in PHONE_RE.finditer(text):
        # 010-0000-0000 처럼 끝 7자리가 같은 수뿐이면 자리표시용으로 본다
        if _is_placeholder_digits(re.sub(r"\D", "", m.group(0))[-7:]):
            continue
        # 같은 자리가 주민번호 모양으로 이미 잡혔으면 중복으로 세지 않는다
        if any(s <= m.start() and m.end() <= e for s, e in rrn_spans):
            continue
        found.append(("전화번호 모양", m.group(0)))

    for m in EMAIL_RE.finditer(text):
        if not _email_is_safe(m.group(1)):
            found.append(("이메일 주소", m.group(0)))

    for m in WIN_USER_RE.finditer(text):
        user = m.group(1).strip().lower()
        if user in SAFE_USER_DIRS or user.startswith("<") or user.startswith("$") or user.startswith("{"):
            continue
        found.append(("실제 사용자 폴더 경로", m.group(0)))

    return found


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
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            if target == "/dev/null":
                continue
            path = target[2:] if target.startswith("b/") else target
            continue
        if raw.startswith("--- ") and not in_hunk:
            continue
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
        if hunk:
            new_line = int(hunk.group(1))
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if raw.startswith("+"):
            yield path, new_line, raw[1:]
            new_line += 1
        elif raw.startswith("-"):
            continue
        elif raw.startswith("\\"):  # "\ No newline at end of file"
            continue
        else:
            new_line += 1


def scan_diff(diff_text: str) -> list[Finding]:
    findings: list[Finding] = []
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
    parser.add_argument("--diff-args", nargs=argparse.REMAINDER, default=[], help="git diff --staged 뒤에 붙일 인자")
    parser.add_argument("--warn-only", action="store_true", help="경고만 하고 항상 0 으로 끝냄")
    args = parser.parse_args(argv)

    try:
        diff_text = sys.stdin.read() if args.stdin else read_staged_diff(args.diff_args)
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
