import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import intake  # noqa: E402

SAMPLE = """```markdown
---
date: 2026-11-27
source: gemini
---
# 2026-11-27 하루 기록

## 조각
### [할일] 체육대회 물품 확인
- 내용: 다음 주 화요일까지 물품 확인
- 날짜·기한: 2026-12-01 (다음 주 화요일)
- 민감: 아니오

### [일정] 교육청 출장
- 날짜·기한: 2026-12-03
- 종류: 출장
- 민감: 아니오

### [수업] 짧은 안내가 3학년 집중을 살렸다
- 내용: 안내를 두 문장으로 줄이니
  아이들이 바로 움직였다
- 과목·차시: 국어
- 성격: 후기
- 공명: "말을 줄이니까 애들이 살더라"
- 민감: 아니오

### [수업] 분수 막대 미리 나눠 두기
- 성격: 요령
- 민감: 아니오

### [생각] 기록은 말로 남겨야 오래 간다
- domain: 생산성
- 공명: 없음
- 민감: 아니오

### [독서] 가르칠 수 있는 용기
- 책: 가르칠 수 있는 용기
- 내용: 교사의 내면이 수업이다
- 민감: 아니오

### [학생] 김가나 발표
- 내용: 김가나가 처음 손을 들었다
- 민감: 예

### [일기] 저녁 산책
- 민감: 아니오

## 확인 필요
- 없음

## 원문
오늘은 ...
```"""


class FakeSheet:
    def __init__(self, rows=()):
        self.data = [dict(r) for r in rows]

    def rows(self):
        return list(self.data)

    def append(self, rows):
        self.data += rows


class FakeNotion:
    def __init__(self):
        self.books = []

    def add_book(self, book, review, day):
        if book in self.books:
            return "이미 있음"
        self.books.append(book)
        return "새 행"


def test_parse_fields_and_continuation():
    doc = intake.parse(SAMPLE)
    assert doc.date == "2026-11-27" and len(doc.pieces) == 8
    lesson = doc.pieces[2]
    assert lesson.get("내용") == "안내를 두 문장으로 줄이니 아이들이 바로 움직였다"
    assert doc.pieces[6].sensitive and not doc.pieces[0].sensitive


def test_plan_routes():
    acts = intake.plan(intake.parse(SAMPLE))
    dest = [(a.piece.kind, a.dest) for a in acts]
    assert dest == [("할일", "sheet"), ("일정", "sheet"), ("수업", "vault-note"), ("수업", "candidate"),
                    ("생각", "vault-note"), ("독서", "notion-reading"), ("학생", "candidate"), ("일기", "candidate")]
    assert acts[0].data == {"date": "2026-12-01", "cat": "개인", "text": "체육대회 물품 확인"}
    assert acts[1].data["cat"] == "출장"
    assert acts[2].where == "10_NOTE/수업/짧은 안내가 3학년 집중을 살렸다.md"


def test_table_hides_sensitive_titles():
    doc = intake.parse(SAMPLE)
    out = intake.table(doc, intake.plan(doc))
    assert "김가나" not in out and "민감 조각 7" in out


def test_apply_writes_everything_once(tmp_path):
    doc = intake.parse(SAMPLE)
    acts = intake.plan(doc)
    sheet, notion = FakeSheet(), FakeNotion()
    now = datetime(2026, 11, 27, 21, 0)
    sent, screen, fails = intake.apply(doc, acts, tmp_path, sheet, notion, now=now)
    assert fails == 0
    assert [r["구분"] for r in sheet.data] == ["개인", "출장"] and sheet.data[0]["출처"] == "하루기록"
    assert notion.books == ["가르칠 수 있는 용기"]
    note = (tmp_path / "10_NOTE/수업/짧은 안내가 3학년 집중을 살렸다.md").read_text(encoding="utf-8")
    assert "type: 후기" in note and "topic: [국어]" in note and "## 공명" in note and "[[daily/2026-11-27]]" in note
    idea = (tmp_path / "00_Inbox/기록은 말로 남겨야 오래 간다.md").read_text(encoding="utf-8")
    assert "domain: 생산성" in idea and "## 공명" not in idea
    daily = (tmp_path / "daily/2026-11-27.md").read_text(encoding="utf-8")
    assert daily.startswith("---\ntype: 일지\n") and "민감: true" in daily and "## 보낸 곳" in daily
    assert "```" not in daily
    assert not any("김가나" in s for s in screen)

    # 다시 돌려도 두 번 넣지 않는다
    _, screen2, fails2 = intake.apply(doc, acts, tmp_path, sheet, notion, now=now)
    assert fails2 == 0 and len(sheet.data) == 2 and notion.books == ["가르칠 수 있는 용기"]
    assert "이미 넣은 기록" in screen2[0]
    assert (tmp_path / "daily/2026-11-27.md").read_text(encoding="utf-8") == daily


def test_second_record_same_day_appends(tmp_path):
    doc = intake.parse(SAMPLE)
    intake.apply(doc, intake.plan(doc), tmp_path, FakeSheet(), FakeNotion(), now=datetime(2026, 11, 27, 9))
    doc2 = intake.parse(SAMPLE.replace("오늘은 ...", "저녁에 하나 더"))
    _, screen, _ = intake.apply(doc2, intake.plan(doc2), tmp_path, FakeSheet(), FakeNotion(),
                                now=datetime(2026, 11, 27, 22, 5))
    daily = (tmp_path / "daily/2026-11-27.md").read_text(encoding="utf-8")
    assert "# 추가 기록 (22:05)" in daily and daily.count("<!-- intake:") == 2
    assert "같은 이름 노트가 있어 건너뜀" in "\n".join(screen)


def test_sheet_failure_does_not_stop_rest(tmp_path):
    doc = intake.parse(SAMPLE)

    def broken():
        raise RuntimeError("인터넷 없음")

    _, screen, fails = intake.apply(doc, intake.plan(doc), tmp_path, broken, FakeNotion(), now=datetime(2026, 11, 27))
    assert fails == 2 and (tmp_path / "daily/2026-11-27.md").exists()
    assert "실패: 인터넷 없음" in "\n".join(screen)


IDEAS = """---
date: 2026-11-28
---
## 조각
### [개선] 수업 비서에 다음 교시 준비물 알림
- 대상: 수업 비서
- 내용: 쉬는 시간에 다음 교시 준비물을 띄워 주면 좋겠다
- 민감: 아니오

### [개선] 카톡 아침 알림에 날씨도
- 내용: 일정 시트 알림에 우산 챙기기
- 민감: 아니오

### [개선] 뭔가 불편했던 것
- 내용: 김가나 일 처리할 때 불편
- 민감: 예
"""


def test_improvement_ideas_go_to_list(tmp_path, capsys):
    doc = intake.parse(IDEAS)
    acts = intake.plan(doc)
    assert [a.data["target"] for a in acts] == ["teacherlesson-assistant", "school-todo-kakao", "(대상 확인 필요)"]
    ideas = tmp_path / "ideas.json"
    _, screen, fails = intake.apply(doc, acts, tmp_path, FakeSheet(), FakeNotion(), now=datetime(2026, 11, 28), ideas=ideas)
    assert fails == 0 and "아이디어 목록에 적음" in screen[1]
    daily = (tmp_path / "daily/2026-11-28.md").read_text(encoding="utf-8")
    assert "[개선] 수업 비서에 다음 교시 준비물 알림 → 개선 아이디어 → teacherlesson-assistant ISSUES 후보" in daily
    # 다시 넣어도 두 번 적지 않음
    intake.apply(doc, acts, tmp_path, FakeSheet(), FakeNotion(), now=datetime(2026, 11, 28), ideas=ideas)
    assert intake.show_ideas(ideas) == 0
    out = capsys.readouterr().out
    assert out.count("| 새것 |") == 3 and "김가나" not in out
    intake.show_ideas(ideas, done="1,2")
    capsys.readouterr()
    intake.show_ideas(ideas)
    assert capsys.readouterr().out.count("| 새것 |") == 1
