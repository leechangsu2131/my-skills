"""NotebookLM 에서 받은 md(오빠두엑셀 북마클릿 등)를 차시별 작은 노트로 자르기. 파이썬 기본 기능만 쓴다.

    python split_notes.py 받은파일.md [받은파일2.md ...]

- 제목 줄(# … 또는 **…**)에 "[수학 6단원] 4차시" 나 "[국어 4단원] 3~4차시" 표시가 있으면 거기서 자른다.
  NotebookLM 에 물을 때 "차시마다 '## [과목 N단원] N차시 제목' 형식의 제목을 붙여 줘"라고 하면 된다
  (수업 비서의 NotebookLM 단추가 복사하는 질문에 이미 들어 있다).
- 결과: 데이터 폴더 notebooklm/<과목>/notes/<N단원>_<N>차시.md (3~4차시면 3·4차시 둘 다). 같은 이름이 있으면 새것으로 바꾼다.
- 수업 비서의 '🤖 AI와 수업 준비' 단추가 그 차시 노트가 있으면 함께 폴더에 넣는다.
"""
from __future__ import annotations

import pathlib
import re
import sys

import assistant_server as app

MARK = re.compile(r"\[\s*([^\]\s]+)\s+([^\]\s]+)\s*\]\s*(\d{1,2})(?:\s*[~∼-]\s*(\d{1,2}))?\s*차시")
HEADING = re.compile(r"^\s*(#{1,6}\s|\*\*)")


def split(text: str) -> list[tuple[str, str, int, int, str]]:
    """(과목, 단원표시, 시작, 끝, 내용) 목록."""
    parts, cur, buf = [], None, []
    for line in text.splitlines():
        m = MARK.search(line) if HEADING.match(line) else None
        if m:
            if cur:
                parts.append((*cur, "\n".join(buf).strip()))
            a = int(m.group(3))
            cur, buf = (m.group(1), m.group(2), a, int(m.group(4) or a)), [line]
        elif cur:
            buf.append(line)
    if cur:
        parts.append((*cur, "\n".join(buf).strip()))
    return parts


def main(paths: list[str]) -> None:
    if not paths:
        print(__doc__)
        return
    for p in paths:
        src = pathlib.Path(p)
        parts = split(src.read_text(encoding="utf-8-sig"))
        if not parts:
            print(f"{src.name}: '[과목 N단원] N차시' 제목을 찾지 못했어요.")
            continue
        for subject, label, a, z, body in parts:
            for n in range(a, max(a, z) + 1):
                out = app.lesson_note_path(subject, label, n)
                if not out.resolve().is_relative_to(app.NOTEBOOKLM.resolve()):
                    print(f"  건너뜀(이름 이상): {subject} {label}")
                    continue
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(f"<!-- {src.name} 에서 자름 -->\n{body}\n", encoding="utf-8")
                print(f"  {out.relative_to(app.NOTEBOOKLM)}  ({len(body):,}자)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])
