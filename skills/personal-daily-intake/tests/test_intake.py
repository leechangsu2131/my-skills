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

    def add_diary(self, p, day):
        if "일기:" + p.title in self.books:
            return "이미 있음"
        self.books.append("일기:" + p.title)
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
                    ("생각", "vault-note"), ("독서", "notion-reading"), ("학생", "candidate"), ("일기", "notion-diary")]
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
    assert notion.books == ["가르칠 수 있는 용기", "일기:저녁 산책"]
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
    assert fails2 == 0 and len(sheet.data) == 2 and notion.books == ["가르칠 수 있는 용기", "일기:저녁 산책"]
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


def test_collect_downloads(tmp_path):
    dl, inbox, arch = tmp_path / "Downloads", tmp_path / "inbox", tmp_path / "gemini"
    dl.mkdir()
    (dl / "하루기록-2026-11-28.md").write_text("---\ndate: 2026-11-28\n---\n", encoding="utf-8")
    (dl / "gemini-2026-11-28-대화.json").write_text("{}", encoding="utf-8")
    (dl / "다른파일.md").write_text("x", encoding="utf-8")
    (inbox / "done").mkdir(parents=True)
    (inbox / "done" / "2026-11-28.md").write_text("앞서 넣은 것", encoding="utf-8")  # 같은 날 두 번째
    moved = intake.collect_downloads(dl, inbox, arch)
    assert moved == ["2026-11-28-2.md", "gemini-2026-11-28-대화.json"]
    assert (inbox / "2026-11-28-2.md").exists() and (dl / "다른파일.md").exists()
    assert intake.collect_downloads(tmp_path / "없는폴더", inbox, arch) == []


def test_bookmarklet_one_line():
    url = intake.bookmarklet()
    assert url.startswith("javascript:(function") and "\n" not in url and "/*" not in url
    assert "#" not in url and "%23" in url  # 즐겨찾기 주소에서 # 은 잘림
    assert url.isascii() and "\\ud558\\ub8e8" in url  # '하루' — 한글은 \uXXXX 로(복사하다 깨지지 않게)


def test_convert_old_gemini_chat(tmp_path):
    import json
    src = tmp_path / "gemini-2026-11-28-하루.json"
    src.write_text(json.dumps({"title": "하루", "exported": "2026-11-28T05:00:00Z", "turns": [
        {"user": "어제 국어 시간에 시화를 찾았다", "model": "좋네요"}, {"user": "", "model": "x"}]}, ensure_ascii=False),
        encoding="utf-8")
    seen = {}

    def fake_ask(f, prompt):
        seen["text"], seen["prompt"] = f.read_text(encoding="utf-8"), prompt
        return "정리했어요\n```markdown\n---\ndate: 2026-11-27\nsource: gemini\n---\n# 하루\n\n## 조각\n### [수업] 시화 찾기\n- 민감: 아니오\n\n## 원문\n어제…\n```"

    out = intake.convert(src, tmp_path / "inbox", tmp_path / "gemini", ask=fake_ask)
    assert out.name == "2026-11-27.md" and intake.parse(out.read_text(encoding="utf-8")).pieces[0].kind == "수업"
    assert "어제 국어 시간에 시화를 찾았다" in seen["text"] and "좋네요" not in seen["text"]  # 제미나이 답은 빼고
    assert "2026-11-28 로 두고" in seen["prompt"] and "[갈래]" in seen["prompt"]
    assert (tmp_path / "gemini" / src.name).exists() and src.exists()  # 교사 폴더 원본은 그대로


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


def test_collect_from_drop_folder_keeps_originals(tmp_path):
    drop, inbox, arch = tmp_path / "노트", tmp_path / "inbox", tmp_path / "gemini"
    drop.mkdir()
    (drop / "gemini-2026-11-28-a.json").write_text("{}", encoding="utf-8")
    assert intake.collect_downloads(drop, inbox, arch, keep=True) == ["gemini-2026-11-28-a.json"]
    assert (drop / "gemini-2026-11-28-a.json").exists()
    assert intake.collect_downloads(drop, inbox, arch, keep=True) == []  # 두 번 가져오지 않음


def test_notion_status_lists_missing_dbs():
    def call(path, body):
        if path == "users/me":
            return {"name": "book manage"}
        return {"results": [{"title": [{"plain_text": "독서 DB"}]}, {"title": [{"plain_text": "2026 업무일지"}]}], "has_more": False}

    bot, rows = intake.notion_status(call)
    assert bot == "book manage"
    assert {k: t for k, _, t in rows} == {"독서": "독서 DB", "업무": "2026 업무일지", "일기": None, "습관": None}


class RecNotion(intake.Notion):
    """Notion API 대신 부른 것을 적어 두는 가짜."""

    def __init__(self, existing=()):
        super().__init__("t", "read", {"work": "W", "diary": "D", "habit": "H", "project": "P"})
        self.calls, self.existing = [], set(existing)

    def _call(self, path, body=None, method=None):
        self.calls.append((method or "POST", path, body))
        if path == "databases/D" and method == "GET":
            return {"properties": {"Emotion": {"type": "multi_select", "multi_select": {"options": [{"name": "😤"}, {"name": "😀"}]}}}}
        if path == "databases/W" and method == "GET":
            return {"properties": {"프로젝트 DB": {"type": "relation"}}}
        if path == "databases/H" and method == "GET":
            return {"properties": {"🏃‍♀️ 운동": {"type": "checkbox"}, "📖 독서": {"type": "checkbox"}, "Date": {"type": "date"}}}
        if path == "databases/P/query":
            return {"results": [{"id": "p1", "properties": {"업무": {"title": [{"plain_text": "운동회 준비"}]},
                                                             "프로젝트": {"select": {"name": "운동회"}}}}]}
        if path.endswith("/query"):
            return {"results": [{"id": "row1"}] if path in self.existing else []}
        return {}


def test_notion_writers():
    p = intake.Piece("업무", "운동회 자리 배치 불만", {"내용": "운동회 때 자리가…"})
    nt = RecNotion()
    assert nt.add_work(p, "2026-11-27") == "새 행 (프로젝트 '운동회')"  # 프로젝트 이름(select)으로 맞음
    page = [c for c in nt.calls if c[1] == "pages"][-1][2]
    assert page["parent"]["database_id"] == "W" and page["properties"]["프로젝트 DB"] == {"relation": [{"id": "p1"}]}
    assert "원문: Obsidian daily/2026-11-27.md" in str(page["children"])

    d = intake.Piece("일기", "속상했던 날", {"감정": "😤 화남", "내용": "…"})
    assert intake.Notion.add_diary(nt, d, "2026-11-27") == "새 행 😤"

    h = intake.Piece("습관", "저녁 운동", {"습관": "운동"})
    assert nt.add_habit(h, "2026-11-27") == "새 줄에 체크: 🏃‍♀️ 운동"
    nt2 = RecNotion(existing={"databases/H/query"})
    assert nt2.add_habit(h, "2026-11-27") == "그날 줄에 체크: 🏃‍♀️ 운동"
    assert nt2.calls[-1][:2] == ("PATCH", "pages/row1")
    assert nt.add_habit(intake.Piece("습관", "산책", {}), "2026-11-27").startswith("체크할 습관 칸을 못 찾음")
    assert RecNotion(existing={"databases/W/query"}).add_work(p, "2026-11-27") == "이미 있음"
