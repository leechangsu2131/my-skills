"""교사 본인 연락처(휴대전화)를 저장소·중앙 .env 밖에서 읽는다.

번호는 구글 드라이브 개인 공간의 txt 한 파일에 둔다(교사 결정 2026-11-27 — .env 에는 비밀값만):
    <구글 드라이브>/my-skills-개인자료/연락처.txt
    예)  휴대전화: 010-0000-0000

구글 드라이브 위치는 PC 마다 다를 수 있어 흔한 곳을 차례로 찾는다(G:\\내 드라이브, 다른 드라이브 문자,
%USERPROFILE%\\Google Drive 등). 파일이 없으면 예전 방식(중앙 .env 의 NEIS_EMERGENCY_CONTACT,
ADMIN_NEIS_BOT__TRIP_CONTACT)을 본다. 그래도 없으면 빈 문자열.

    python contact_info.py      # 어디서 찾았는지만 보여 줌(번호는 가림)
"""
from __future__ import annotations

import os
import re
import string
from pathlib import Path

FOLDER = "my-skills-개인자료"
FILE = "연락처.txt"
LABELS = ("휴대전화", "연락처", "비상연락처", "출장")
PHONE = re.compile(r"0\d{1,2}-?\d{3,4}-?\d{4}")


def _drive_roots() -> list[Path]:
    roots: list[Path] = []
    for letter in string.ascii_uppercase[3:]:  # D: ~ Z:
        for name in ("내 드라이브", "My Drive"):
            roots.append(Path(f"{letter}:/{name}"))
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    for base in (home / "Google Drive", home / "GoogleDrive", home):
        for name in ("내 드라이브", "My Drive"):
            roots.append(base / name)
    return roots


def find_contact_file() -> Path | None:
    for root in _drive_roots():
        p = root / FOLDER / FILE
        try:
            if p.is_file():
                return p
        except OSError:
            continue
    return None


def _parse(text: str) -> str:
    first = ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = PHONE.search(line)
        if not m:
            continue
        if any(label in line for label in LABELS):
            return m.group(0)
        first = first or m.group(0)
    return first


def my_phone() -> str:
    """교사 휴대전화 번호(010-0000-0000 꼴, 없으면 '')."""
    p = find_contact_file()
    if p:
        number = _parse(p.read_text(encoding="utf-8-sig", errors="replace"))
        if number:
            return number
    # 예전 방식: 중앙 .env (남아 있는 PC 를 위해)
    for key in ("NEIS_EMERGENCY_CONTACT", "TRIP_CONTACT", "ADMIN_NEIS_BOT__TRIP_CONTACT"):
        if os.environ.get(key):
            return os.environ[key].strip()
    return ""


if __name__ == "__main__":
    f = find_contact_file()
    n = my_phone()
    print("연락처 파일:", f or "못 찾음")
    print("번호:", (n[:3] + "-****-" + n[-4:]) if n else "없음")
