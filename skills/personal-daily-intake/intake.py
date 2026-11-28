"""하루 기록(제미나이 정리본 md) → 갈래별로 나눠 일정DB 시트·Notion·옵시디언 볼트에 넣는다.

    python intake.py plan  [파일]                       # 어디에 무엇을 넣을지 표만 (아무것도 안 바꿈)
    python intake.py apply [파일] [--skip sheet,notion]   # 표대로 넣기 — 교사가 표를 보고 동의한 뒤에만

- 파일을 안 주면 데이터 폴더(내 문서\\my-skills-data\\personal-daily-intake\\inbox)의 가장 최근 .md.
- 여러 번 돌려도 같은 것을 두 번 넣지 않는다: 일정DB는 키, Notion 독서는 책 제목, 볼트 노트는 파일 이름,
  daily 노트는 입력 지문(<!-- intake:... -->)으로 확인한다. 실패가 없으면 입력 파일을 inbox\\done 으로 옮긴다.
- 기존 노트는 고치지 않는다(볼트 규칙). 과목 노트에 덧붙일 요령, 학생 기록, 투자 일지 등은 '후보'로만 보여 준다.
- 민감 조각(학생 이름·가족·건강 등)은 화면에 제목을 내지 않는다. 볼트에는 그대로 넣되 `민감: true`를 단다
  (볼트는 비공개 — 공개 전에 그 표시로 찾아 뺀다. 운용지침 v15 보완 2026-11-27).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
SKILLS = SKILL_DIR.parent
sys.path.insert(0, str(SKILLS / "_shared"))
sys.path.insert(0, str(SKILLS / "school-todo-kakao"))
from skill_env import data_dir, env_values, load_env  # noqa: E402
from schooltodo.sync import make_key  # noqa: E402  일정DB 키를 sync 와 똑같이 만든다

SKILL = "personal-daily-intake"
DOMAINS = ("수업", "학급", "투자", "자기", "관계", "DIY", "생산성", "횡단")
SOURCE = "하루기록"  # 일정DB '출처' 칸 — 직접 쓴 행·자동 행과 구분
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass
class Piece:
    kind: str
    title: str
    fields: dict = field(default_factory=dict)

    @property
    def sensitive(self) -> bool:
        return self.fields.get("민감", "").strip().startswith("예") or self.kind == "학생"

    def get(self, key: str) -> str:
        return self.fields.get(key, "").strip()


@dataclass
class Doc:
    date: str
    pieces: list
    body: str  # 앞머리를 뺀 본문(제미나이 정리본 그대로)
    digest: str


@dataclass
class Action:
    dest: str  # sheet | notion-reading | vault-note | candidate | daily
    where: str
    piece: Piece
    data: dict = field(default_factory=dict)


# ---------- 읽기 ----------

def _strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines)
    return t.strip() + "\n"


def parse(text: str, fallback_date: str = "") -> Doc:
    text = _strip_fence(text.replace("\r\n", "\n"))
    fm, body = {}, text
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            for line in text[4:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
            body = text[end + 4:].lstrip("\n")
    day = fm.get("date") or fallback_date
    if not DATE_RE.fullmatch(day or ""):
        raise SystemExit("날짜를 알 수 없어요 — 앞머리에 date: YYYY-MM-DD 를 넣거나 파일 이름을 날짜로 하세요.")
    sections = {}
    for chunk in re.split(r"^## ", body, flags=re.M)[1:]:
        name, _, rest = chunk.partition("\n")
        sections[name.strip()] = rest
    pieces = []
    for chunk in re.split(r"^### ", sections.get("조각", ""), flags=re.M)[1:]:
        head, _, rest = chunk.partition("\n")
        m = re.match(r"\s*\[([^\]]+)\]\s*(.*)", head)
        if not m:
            continue
        p, last = Piece(m.group(1).strip(), m.group(2).strip()), None
        for line in rest.splitlines():
            f = re.match(r"^\s*[-*]\s*([^:：]{1,12})[:：]\s*(.*)$", line)
            if f and f.group(1).strip() not in p.fields:
                last = f.group(1).strip()
                p.fields[last] = f.group(2).strip()
            elif last and line.strip():
                p.fields[last] += " " + line.strip()
        pieces.append(p)
    return Doc(day, pieces, body, hashlib.sha256(text.encode("utf-8")).hexdigest()[:12])


# ---------- 나누기 ----------

def safe_name(title: str) -> str:
    name = re.sub(r'[\\/:*?"<>|#^\[\]]+', " ", title)
    return re.sub(r"\s+", " ", name).strip(" .")[:80] or "제목 없음"


# [개선] 조각의 대상 → 이슈를 적을 곳(스킬 폴더 또는 저장소). 위에서부터 먼저 맞는 것.
TARGETS = (
    (r"수업\s*비서|교시|수업\s*흐름|수업\s*준비|녹음|받아쓰기", "teacherlesson-assistant"),
    (r"지도서|차시\s*나누", "teacherlesson-guide"),
    (r"진도|시간표", "teacherlesson-schedule"),
    (r"하루\s*기록|제미나이\s*스킬|정리기", "personal-daily-intake"),
    (r"일정\s*DB|일정\s*시트|카톡\s*알림|아침\s*알림|할\s*일\s*알림", "school-todo-kakao"),
    (r"투자\s*시트|매매|포트폴리오", "invest-sheet(GitLab)"),
    (r"옵시디언|볼트|PKM|노트\s*정리", "personal-obsidansystem-main"),
    (r"홈페이지|웹\s*사이트|HomePage", "HomePage"),
    (r"나이스|NEIS", "admin-neis-bot"),
    (r"에듀파인|품의|기안|공문", "admin-edufine"),
    (r"하이톡|하이클래스|알림장", "admin-hitalk-sender"),
    (r"노트북\s*LM|NotebookLM", "util-notebooklm"),
    (r"크롬\s*프로필|크롬\s*창", "util-chrome-profiles"),
    (r"학생\s*기록|누가\s*기록|평가", "classmanage-student-classifier"),
)


def guess_target(text: str) -> str:
    for pat, target in TARGETS:
        if re.search(pat, text or "", re.I):
            return target
    return "(대상 확인 필요)"


def add_idea(path: Path, doc: Doc, p: Piece, target: str) -> bool:
    """개선 아이디어를 데이터 폴더 ideas.json 에 적는다(같은 날·같은 제목이면 건너뜀). 새로 적었으면 True."""
    ideas = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    if any(x["date"] == doc.date and x["title"] == p.title for x in ideas):
        return False
    ideas.append({"no": max((x["no"] for x in ideas), default=0) + 1, "date": doc.date, "title": p.title,
                  "content": p.get("내용"), "target": target, "sensitive": p.sensitive, "status": "new"})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ideas, ensure_ascii=False, indent=1), encoding="utf-8")
    return True


def plan(doc: Doc) -> list:
    acts = []
    for p in doc.pieces:
        k, nat = p.kind, p.get("성격")
        if k in ("할일", "일정"):
            m = DATE_RE.search(p.get("날짜·기한") or p.get("날짜") or p.get("기한"))
            cat = "개인" if k == "할일" else ("출장" if "출장" in p.get("종류") else "학교")
            day = m.group(0) if m else doc.date
            acts.append(Action("sheet", f"일정DB · {cat} · {day}", p, {"date": day, "cat": cat, "text": p.title}))
        elif k == "수업" and "후기" in nat:
            acts.append(Action("vault-note", f"10_NOTE/수업/{safe_name(p.title)}.md", p,
                               {"domain": "수업", "engine": "experiment", "type": "후기", "topic": p.get("과목·차시")}))
        elif k == "수업" and "아이디어" in nat:
            acts.append(Action("vault-note", f"00_Inbox/{safe_name(p.title)}.md", p,
                               {"domain": "수업", "engine": "", "type": "idea", "topic": p.get("과목·차시")}))
        elif k == "수업" and "요령" in nat:
            acts.append(Action("candidate", "과목 노트 '진행 방식'에 덧붙일 후보 (기존 노트 — 교사 확인 뒤)", p))
        elif k == "생각":
            dom = p.get("domain")
            acts.append(Action("vault-note", f"00_Inbox/{safe_name(p.title)}.md", p,
                               {"domain": dom if dom in DOMAINS else "", "engine": "", "type": "단상", "topic": ""}))
        elif k == "독서":
            acts.append(Action("notion-reading", "Notion 독서 DB", p, {"book": p.get("책") or p.title}))
        elif k == "학생":
            acts.append(Action("candidate", "학생 기록 DB 후보 — classmanage-student-classifier 로", p))
        elif k == "투자":
            acts.append(Action("candidate", "투자시트 분위기 일지 후보 — personal-invest-sheet 로", p))
        elif k in NOTION_KINDS:
            acts.append(Action("notion-" + NOTION_KINDS[k][0], f"Notion {NOTION_KINDS[k][1]}", p))
        elif k == "개선":
            tgt = guess_target(" ".join((p.get("대상"), p.title, p.get("내용"))))
            acts.append(Action("idea", f"개선 아이디어 → {tgt} ISSUES 후보", p, {"target": tgt}))
        else:
            acts.append(Action("daily", "daily 에만", p))
    return acts


def shown(p: Piece, i: int) -> str:
    return f"(민감 조각 {i} — 제목 숨김)" if p.sensitive else p.title


def table(doc: Doc, acts: list) -> str:
    out = [f"{doc.date} 하루 기록 — 조각 {len(doc.pieces)}개 (민감 {sum(p.sensitive for p in doc.pieces)}개)",
           f"모든 조각 → 볼트 daily/{doc.date}.md", "", "| # | 갈래 | 조각 | 보낼 곳 |", "|---|---|---|---|"]
    for i, a in enumerate(acts, 1):
        out.append(f"| {i} | {a.piece.kind} | {shown(a.piece, i)} | {a.where} |")
    return "\n".join(out)


# ---------- 쓰기 ----------

def note_text(doc: Doc, a: Action) -> str:
    d, p = a.data, a.piece
    fm = ["---", f"domain: {d['domain']}", f"engine: {d['engine']}",
          f"topic: [{d['topic']}]" if d["topic"] else "topic:", f"type: {d['type']}"]
    if p.sensitive:
        fm.append("민감: true")
    fm.append("---")
    body = [f"# {p.title}", ""]
    if p.get("내용"):
        body += [p.get("내용"), ""]
    res = p.get("공명")
    if res and not res.startswith("없음"):
        body += ["## 공명", res, ""]
    body += [f"원문: [[daily/{doc.date}]]", ""]
    return "\n".join(fm + body)


def write_daily(vault: Path, doc: Doc, sent: list, now: datetime) -> str:
    path = vault / "daily" / f"{doc.date}.md"
    marker = f"<!-- intake:{doc.digest} -->"
    sens = any(p.sensitive for p in doc.pieces)
    tail = "\n## 보낸 곳\n" + ("\n".join(sent) if sent else "- 없음 (daily 에만)") + f"\n{marker}\n"
    if path.exists():
        old = path.read_text(encoding="utf-8")
        if marker in old:
            return f"daily/{doc.date}.md — 이미 넣은 기록, 건너뜀"
        if sens and "\n민감: true" not in old.split("\n---", 1)[0] and old.startswith("---\n"):
            old = old.replace("---\n", "---\n민감: true\n", 1)
        body = re.sub(r"^# .*\n", "", doc.body, count=1)
        path.write_text(old.rstrip("\n") + f"\n\n---\n# 추가 기록 ({now:%H:%M})\n\n" + body.rstrip("\n") + "\n" + tail,
                        encoding="utf-8")
        return f"daily/{doc.date}.md — 덧붙임"
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = ["---", "type: 일지", f"date: {doc.date}", "source: gemini"] + (["민감: true"] if sens else []) + ["---", ""]
    path.write_text("\n".join(fm) + doc.body.rstrip("\n") + "\n" + tail, encoding="utf-8")
    return f"daily/{doc.date}.md — 새로 만듦"


# 갈래 → (Notion 쓰기 종류, 표에 보일 이름). DB id 는 중앙 .env PERSONAL_DAILY_INTAKE__NOTION_<종류>_DB_ID
NOTION_KINDS = {"업무": ("work", "업무일지"), "일기": ("diary", "일기"), "습관": ("habit", "습관기록")}
HABIT_WORDS = ("운동", "독서", "명상", "물", "일찍", "감사")  # 습관기록 체크 칸 이름에 든 낱말


def _title(text: str) -> dict:
    return {"title": [{"text": {"content": text[:1900]}}]}


class Notion:
    def __init__(self, token: str, reading_db: str, ids: dict | None = None):
        self.token, self.reading_db, self.ids = token, reading_db, ids or {}
        self._schemas, self._projects = {}, None

    def _call(self, path: str, body: dict | None = None, method: str | None = None) -> dict:
        req = urllib.request.Request(
            "https://api.notion.com/v1/" + path, data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers={"Authorization": "Bearer " + self.token, "Notion-Version": "2022-06-28",
                     "Content-Type": "application/json"}, method=method)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)

    # --- 공용 ---
    def db(self, kind: str) -> str:
        if not self.ids.get(kind):
            raise RuntimeError(f"중앙 .env 에 PERSONAL_DAILY_INTAKE__NOTION_{kind.upper()}_DB_ID 가 없어요(python intake.py notion)")
        return self.ids[kind]

    def schema(self, db: str) -> dict:
        if db not in self._schemas:
            self._schemas[db] = self._call(f"databases/{db}", method="GET")["properties"]
        return self._schemas[db]

    def query(self, db: str, flt: dict) -> list:
        return self._call(f"databases/{db}/query", {"filter": flt, "page_size": 5}).get("results", [])

    def create(self, db: str, props: dict, lines: list[str]) -> None:
        children = [{"object": "block", "type": "paragraph",
                     "paragraph": {"rich_text": [{"type": "text", "text": {"content": ln[:1900]}}]}} for ln in lines if ln]
        self._call("pages", {"parent": {"database_id": db}, "properties": props, "children": children})

    def projects(self) -> list[tuple[str, str]]:
        """(프로젝트 이름, page id) — 업무 조각을 프로젝트에 이을 때. 프로젝트 DB 가 없으면 빈 목록."""
        if self._projects is None:
            self._projects = []
            db, cursor = self.ids.get("project"), None
            while db:
                body = {"page_size": 100, **({"start_cursor": cursor} if cursor else {})}
                d = self._call(f"databases/{db}/query", body)
                for pg in d.get("results", []):
                    props = pg.get("properties", {})
                    name = "".join(x.get("plain_text", "") for x in props.get("업무", {}).get("title", []))
                    sel = (props.get("프로젝트", {}).get("select") or {}).get("name", "")
                    for n in {name.strip(), sel.strip()}:
                        if len(n) >= 2:
                            self._projects.append((n, pg["id"]))
                if not d.get("has_more"):
                    break
                cursor = d.get("next_cursor")
        return self._projects

    # --- 갈래별 ---
    def add_work(self, p: "Piece", day: str) -> str:
        db = self.db("work")
        if self.query(db, {"and": [{"property": "이름", "title": {"equals": p.title}},
                                   {"property": "날짜", "date": {"equals": day}}]}):
            return "이미 있음"
        props = {"이름": _title(p.title), "날짜": {"date": {"start": day}}}
        text = " ".join((p.title, p.get("내용"), p.get("관련")))
        hits = sorted((n for n in self.projects() if n[0].lower() in text.lower()), key=lambda n: -len(n[0]))
        if hits and "프로젝트 DB" in self.schema(db):
            props["프로젝트 DB"] = {"relation": [{"id": hits[0][1]}]}
        self.create(db, props, [p.get("내용"), f"원문: Obsidian daily/{day}.md"])
        return "새 행" + (f" (프로젝트 '{hits[0][0]}')" if hits else "")

    def add_diary(self, p: "Piece", day: str) -> str:
        db = self.db("diary")
        if self.query(db, {"and": [{"property": "Name", "title": {"equals": p.title}},
                                   {"property": "Date", "date": {"equals": day}}]}):
            return "이미 있음"
        props = {"Name": _title(p.title), "Date": {"date": {"start": day}}}
        opts = [o["name"] for o in self.schema(db).get("Emotion", {}).get("multi_select", {}).get("options", [])]
        feel = [o for o in opts if o in p.get("감정")]
        if feel:
            props["Emotion"] = {"multi_select": [{"name": o} for o in feel]}
        self.create(db, props, [p.get("내용"), f"원문: Obsidian daily/{day}.md"])
        return "새 행" + (f" {''.join(feel)}" if feel else "")

    def add_habit(self, p: "Piece", day: str) -> str:
        db = self.db("habit")
        boxes = [k for k, v in self.schema(db).items() if v.get("type") == "checkbox"]
        said = p.get("습관") or f"{p.title} {p.get('내용')}"
        tick = [b for b in boxes if any(w in b and w in said for w in HABIT_WORDS)]
        if not tick:
            return "체크할 습관 칸을 못 찾음 — daily 에만"
        props = {b: {"checkbox": True} for b in tick}
        rows = self.query(db, {"property": "Date", "date": {"equals": day}})
        if rows:
            self._call(f"pages/{rows[0]['id']}", {"properties": props}, method="PATCH")
            return "그날 줄에 체크: " + ", ".join(tick)
        self.create(db, {"Name": _title(day), "Date": {"date": {"start": day}}, **props}, [])
        return "새 줄에 체크: " + ", ".join(tick)

    def add_book(self, book: str, review: str, day: str) -> str:
        found = self._call(f"databases/{self.reading_db}/query",
                           {"filter": {"property": "책제목", "title": {"equals": book}}, "page_size": 1})
        if found.get("results"):
            return "이미 있음 — 건너뜀(기존 행은 손으로)"
        props = {"책제목": {"title": [{"text": {"content": book}}]},
                 "읽은기간": {"date": {"start": day}}}
        if review:
            props["한줄평"] = {"rich_text": [{"text": {"content": review[:1900]}}]}
        self._call("pages", {"parent": {"database_id": self.reading_db}, "properties": props})
        return "새 행"


# 하루 기록이 Notion 에 넣고 싶은 DB — (갈래, 제목에 들어갈 낱말). 아직 쓰기는 독서만, 나머지는 공유 확인부터(ISSUE-001)
NOTION_WANTED = (("독서", "독서"), ("업무", "업무일지"), ("일기", "일기"), ("습관", "습관"))
NOTION_HOWTO = """Notion 에서 연결하는 법(DB 마다 한 번):
  1. Notion 에서 그 DB(또는 DB 가 든 페이지 — 예: '2026 업무일지', '생활습관 및 일기')를 연다
  2. 오른쪽 위 ··· → '연결'(Connections) → '{bot}' 를 찾아 누르고 '확인'
     (페이지에 연결하면 그 안의 DB 들이 함께 열린다)
  3. 다시 python intake.py notion 으로 ✅ 가 되는지 본다"""


def notion_status(call) -> tuple[str, list[tuple[str, str, str | None]]]:
    """(연결 이름, [(갈래, 찾는 낱말, 찾은 DB 제목 또는 None)]). call(경로, 본문 또는 None) → JSON."""
    me = call("users/me", None)
    found, cursor = [], None
    while True:
        body = {"filter": {"property": "object", "value": "database"}, "page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        d = call("search", body)
        found += ["".join(x.get("plain_text", "") for x in db.get("title", [])) for db in d.get("results", [])]
        if not d.get("has_more"):
            break
        cursor = d.get("next_cursor")
    rows = [(kind, word, next((t for t in found if word in t), None)) for kind, word in NOTION_WANTED]
    return me.get("name") or "(이름 모름)", rows


def show_notion() -> int:
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("중앙 .env 에 NOTION_TOKEN 이 없어요.")
        return 1

    def call(path, body):
        req = urllib.request.Request(
            "https://api.notion.com/v1/" + path, data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers={"Authorization": "Bearer " + token, "Notion-Version": "2022-06-28", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)

    bot, rows = notion_status(call)
    print(f"Notion 연결 이름: {bot}")
    for kind, word, title in rows:
        print(f"{'✅' if title else '❌'} {kind}: " + (f"'{title}' 보임" if title else f"'{word}' 가 든 DB 가 안 보임 — 공유 필요"))
    if any(t is None for _, _, t in rows):
        print("\n" + NOTION_HOWTO.format(bot=bot))
        print("\n공유한 뒤에도 업무·일기·습관에 실제로 쓰는 기능은 아직 없어요 — 공유가 되면 Claude 에게 'Notion 쓰기 붙여 줘'(ISSUE-001).")
    return 0


def open_sheet():
    from schooltodo.db import SheetsDb
    return SheetsDb.from_env()


def open_notion() -> Notion:
    token = os.environ.get("NOTION_TOKEN", "").strip()
    db = os.environ.get("NOTION_READING_DB_ID", "").strip()  # .env 의 PERSONAL_DAILY_INTAKE__ 접두어는 load_env 가 뗀다
    if not token or not db:
        raise RuntimeError("중앙 .env 에 NOTION_TOKEN 과 PERSONAL_DAILY_INTAKE__NOTION_READING_DB_ID 가 필요해요")
    ids = {k: os.environ.get(f"NOTION_{k.upper()}_DB_ID", "").strip() for k in ("work", "diary", "habit", "project")}
    return Notion(token, db, ids)


def apply(doc: Doc, acts: list, vault: Path, sheet=None, notion=None, skip=(), now=None, ideas: Path | None = None):
    """(보낸 곳 줄들, 화면 줄들, 실패 수). sheet·notion 은 필요할 때 여는 함수나 객체. ideas: 개선 아이디어 목록 파일."""
    now = now or datetime.now()
    ideas = ideas or data_dir(SKILL) / "ideas.json"
    sent, screen, fails = [], [], 0

    def note(i, a, result, ok=True):
        nonlocal fails
        fails += 0 if ok else 1
        screen.append(f"{'✅' if ok else '❌'} {i}. {shown(a.piece, i)} → {a.where}: {result}")
        if ok and a.dest != "daily":
            label = f"[{a.piece.kind}] {a.piece.title}"
            sent.append(f"- {label} → " + (f"[[{a.where[:-3]}]]" if a.dest == "vault-note" else a.where)
                        + ("" if a.dest in ("candidate", "idea") else f" ({result})"))

    # 일정DB: 한 번에 읽고 한 번에 넣는다
    sheet_acts = [(i, a) for i, a in enumerate(acts, 1) if a.dest == "sheet"]
    if sheet_acts and "sheet" in skip:
        for i, a in sheet_acts:
            note(i, a, "건너뜀(--skip)", ok=False)
    elif sheet_acts:
        try:
            db = sheet() if callable(sheet) else sheet
            have = {r.get("키", "") for r in db.rows()}
            rows = []
            for i, a in sheet_acts:
                d = a.data
                key = make_key(date.fromisoformat(d["date"]), d["text"])
                if key in have:
                    note(i, a, "이미 있음")
                    continue
                have.add(key)
                rows.append({"키": key, "날짜": d["date"], "구분": d["cat"], "내용": d["text"], "상태": "", "출처": SOURCE})
                note(i, a, "새 행")
            db.append(rows)
        except Exception as e:  # noqa: BLE001 — 시트가 안 돼도 나머지는 넣는다
            for i, a in sheet_acts:
                note(i, a, f"실패: {e}", ok=False)

    nt = None
    for i, a in enumerate(acts, 1):
        if a.dest == "sheet":
            continue
        try:
            if a.dest == "vault-note":
                path = vault / a.where
                if path.exists():
                    note(i, a, "같은 이름 노트가 있어 건너뜀")
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(note_text(doc, a), encoding="utf-8")
                note(i, a, "새 노트")
            elif a.dest.startswith("notion-"):
                if "notion" in skip:
                    note(i, a, "건너뜀(--skip)", ok=False)
                    continue
                nt = nt or (notion() if callable(notion) else notion)
                if a.dest == "notion-reading":
                    note(i, a, nt.add_book(a.data["book"], a.piece.get("내용"), doc.date))
                else:
                    note(i, a, getattr(nt, "add_" + a.dest[len("notion-"):])(a.piece, doc.date))
            elif a.dest == "idea":
                new = add_idea(ideas, doc, a.piece, a.data["target"])
                note(i, a, "아이디어 목록에 적음 (python intake.py ideas)" if new else "이미 적혀 있음")
            else:
                note(i, a, "후보" if a.dest == "candidate" else "daily 에만")
        except Exception as e:  # noqa: BLE001
            note(i, a, f"실패: {e}", ok=False)

    screen.insert(0, "✅ " + write_daily(vault, doc, sent, now))
    return sent, screen, fails


# ---------- 명령 ----------

def downloads_dir() -> Path:
    raw = os.environ.get("DOWNLOADS", "").strip()  # .env 의 PERSONAL_DAILY_INTAKE__DOWNLOADS (다운로드 폴더를 옮겼을 때)
    return Path(os.path.expandvars(raw)) if raw else Path.home() / "Downloads"


def collect_downloads(downloads: Path, inbox: Path, archive: Path, keep: bool = False) -> list[str]:
    """북마클릿이 받은 파일을 가져온다: 하루기록-*.md → inbox, gemini-*.json → 대화 보관 폴더. 가져온 이름들.
    keep=True(교사가 정한 DROP 폴더, 예: 구글 드라이브 노트)면 원본은 두고 복사만, 이미 가져온 이름은 건너뜀."""
    moved = []
    for pattern, dest in (("하루기록-*.md", inbox), ("gemini-*.json", archive)):
        for f in sorted(downloads.glob(pattern)) if downloads.is_dir() else []:
            dest.mkdir(parents=True, exist_ok=True)
            name = f.name[len("하루기록-"):] if f.name.startswith("하루기록-") else f.name
            target, n = dest / name, 2
            if keep:
                if target.exists() or (dest / "done" / name).exists():
                    continue
                shutil.copy2(f, target)
                moved.append(target.name)
                continue
            while target.exists() or (dest / "done" / target.name).exists():  # 같은 날 두 번째 기록
                target, n = dest / f"{Path(name).stem}-{n}{Path(name).suffix}", n + 1
            f.replace(target)
            moved.append(target.name)
    return moved


def drop_dirs() -> list[Path]:
    """북마클릿 파일을 찾을 곳: 다운로드 폴더 + (있으면) .env PERSONAL_DAILY_INTAKE__DROP 폴더(예: 구글 드라이브 노트 폴더)."""
    out = [downloads_dir()]
    raw = os.environ.get("DROP", "").strip()
    if raw:
        out.append(Path(os.path.expandvars(raw)))
    return out


def gem_instructions() -> str:
    """gem_prompt.md 의 상자 안 지침(제미나이 스킬과 같은 글)."""
    t = (SKILL_DIR / "gem_prompt.md").read_text(encoding="utf-8")
    return t.split("````text", 1)[1].rsplit("````", 1)[0].strip()


def conversation_text(data: dict) -> str:
    """내보낸 대화 json → 선생님이 한 말만(제미나이 답은 원문이 아니므로 뺀다)."""
    parts = [f"# {data.get('title', '대화')}"]
    for i, t in enumerate(data.get("turns", []), 1):
        if (t.get("user") or "").strip():
            parts.append(f"## 내가 한 말 {i}\n{t['user'].strip()}")
    return "\n\n".join(parts) + "\n"


def extract_md(answer: str) -> str:
    """Gemini 답에서 정리본 md 만(코드 상자를 벗김)."""
    m = re.search(r"```(?:markdown|md)?\s*\n(---\s*\n.*?)```", answer, re.S)
    text = m.group(1) if m else answer
    i = text.find("---")
    return text[i:].strip() + "\n" if i != -1 else ""


def convert(src: Path, inbox: Path, archive: Path, ask=None) -> Path:
    """지난 Gemini 대화 json 을 제미나이 스킬과 같은 지침으로 다시 정리해 inbox 에 md 로. ask(파일, 지침) → 답."""
    data = json.loads(src.read_text(encoding="utf-8"))
    exported = (data.get("exported") or "")[:10] or date.today().isoformat()
    body = archive / "convert" / (src.stem + ".md")
    body.parent.mkdir(parents=True, exist_ok=True)
    body.write_text(conversation_text(data), encoding="utf-8")
    prompt = (gem_instructions() + "\n\n[이번 일] 파일 @{file} 은 선생님이 그날 제미나이에게 한 말을 모은 것이다(받아쓴 글로 본다). "
              f"위 형식의 md 한 장으로만 답하라. 기록 날짜(date)는 글에서 알 수 있으면 그 날짜, 모르면 {exported} 로 두고 "
              "'확인 필요'에 '날짜 확인'을 적어라. '원문' 절에는 파일의 '내가 한 말' 글을 그대로 옮긴다.")
    if ask is None:
        sys.path.insert(0, str(SKILLS / "util-notebooklm"))
        from nlm import gemini_ask  # Gemini CLI — 지침·글을 넘겨 답을 받음
        ask = lambda f, p: gemini_ask(f, p)[0]  # noqa: E731
    md = extract_md(ask(body, prompt))
    doc = parse(md)  # 날짜·조각이 없으면 여기서 멈춤
    if not doc.pieces:
        raise SystemExit(f"{src.name}: 조각을 하나도 못 받았어요 — 다시 해 보거나 손으로 고치세요.")
    inbox.mkdir(parents=True, exist_ok=True)
    out, n = inbox / f"{doc.date}.md", 2
    while out.exists() or (inbox / "done" / out.name).exists():
        out, n = inbox / f"{doc.date}-{n}.md", n + 1
    out.write_text(md, encoding="utf-8")
    archive.mkdir(parents=True, exist_ok=True)
    if src.parent != archive:  # 다운로드 폴더 것은 옮기고, 그 밖(교사 폴더)은 복사만
        (src.replace if src.parent == downloads_dir() else lambda t: shutil.copy2(src, t))(archive / src.name)
    return out


def bookmarklet() -> str:
    """gemini_bookmarklet.js → 즐겨찾기 주소(javascript:…) 한 줄."""
    js = (SKILL_DIR / "gemini_bookmarklet.js").read_text(encoding="utf-8")
    js = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
    js = " ".join(line.strip() for line in js.splitlines() if line.strip())
    # 한글은 \uXXXX 로 — 클립보드·콘솔 인코딩을 거치며 깨지지 않게(2026-11-28 붙여 넣으니 끝부분이 깨짐). 한글은 문자열 안에만 있다
    js = "".join(c if ord(c) < 128 else _u_escape(c) for c in js)
    return "javascript:" + js.replace("%", "%25").replace("#", "%23")


def _u_escape(c: str) -> str:
    b = c.encode("utf-16-be")
    return "".join(f"\\u{int.from_bytes(b[i:i + 2], 'big'):04x}" for i in range(0, len(b), 2))


def find_input(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    inbox = data_dir(SKILL, "inbox")
    dl = downloads_dir()
    moved = [n for d in drop_dirs() for n in collect_downloads(d, inbox, data_dir(SKILL, "gemini"), keep=d != dl)]
    if moved:
        print(f"다운로드 폴더에서 옮김: {', '.join(moved)}")
    files = sorted(inbox.glob("*.md"), key=lambda f: f.stat().st_mtime)
    if not files:
        raise SystemExit(f"넣을 파일이 없어요 — 제미나이 정리본을 {inbox} 에 .md 로 저장하세요.")
    return files[-1]


def vault_path() -> Path:
    # 이 스킬 전용 VAULT(PERSONAL_DAILY_INTAKE__VAULT)가 없으면 옵시디언 스킬의 값을 빌린다
    raw = os.environ.get("VAULT") or env_values("personal-obsidansystem-main").get("VAULT", "")
    v = Path(os.path.expandvars(raw.strip())) if raw.strip() else None
    if not v or not (v / "PKM_Rules").is_dir():
        raise SystemExit("볼트 경로를 모르겠어요 — 중앙 .env 의 PERSONAL_OBSIDANSYSTEM_MAIN__VAULT 를 확인하세요.")
    return v


def show_ideas(path: Path, done: str = "", show_all: bool = False) -> int:
    """개선 아이디어 목록. --done 번호면 '옮김'으로 표시. 민감 아이디어는 제목을 가린다."""
    ideas = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    marks = {int(x) for x in re.findall(r"\d+", done)}
    for x in ideas:
        if x["no"] in marks:
            x["status"] = "moved"
    if marks:
        path.write_text(json.dumps(ideas, ensure_ascii=False, indent=1), encoding="utf-8")
    rows = [x for x in ideas if show_all or x["status"] == "new"]
    if not rows:
        print("옮길 개선 아이디어가 없어요.")
        return 0
    print("| 번호 | 날짜 | 대상 | 아이디어 | 상태 |\n|---|---|---|---|---|")
    for x in rows:
        title = "(민감 — 제목 숨김)" if x.get("sensitive") else x["title"]
        print(f"| {x['no']} | {x['date']} | {x['target']} | {title} | {'옮김' if x['status'] == 'moved' else '새것'} |")
    return 0


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="하루 기록을 갈래별로 나눠 넣기")
    ap.add_argument("cmd", choices=["plan", "apply", "ideas", "bookmarklet", "convert", "notion"])
    ap.add_argument("file", nargs="?")
    ap.add_argument("files", nargs="*", help="convert: 여러 json")
    ap.add_argument("--skip", default="", help="쉼표로: sheet,notion")
    ap.add_argument("--done", default="", help="ideas: ISSUES 에 옮긴 번호(쉼표로)")
    ap.add_argument("--all", action="store_true", help="ideas: 옮긴 것도 보기")
    a = ap.parse_args(argv)
    if a.cmd == "ideas":
        return show_ideas(data_dir(SKILL) / "ideas.json", a.done, a.all)
    if a.cmd == "notion":
        load_env()
        return show_notion()
    if a.cmd == "convert":
        load_env()
        inbox, archive = data_dir(SKILL, "inbox"), data_dir(SKILL, "gemini")
        srcs = [Path(x) for x in ([a.file] if a.file else []) + a.files]
        if not srcs:  # 안 주면: 다운로드·DROP 폴더와 보관 폴더에서 아직 안 바꾼 gemini-*.json
            done = {p.stem for p in (archive / "convert").glob("*.md")} if (archive / "convert").is_dir() else set()
            srcs = [p for d in drop_dirs() + [archive] if d.is_dir() for p in sorted(d.glob("gemini-*.json"))
                    if p.stem not in done]
        if not srcs:
            print("바꿀 Gemini 대화(json)가 없어요.")
            return 1
        for s in srcs:
            out = convert(s, inbox, archive)
            print(f"✅ {s.name[:50]} → inbox\\{out.name}")
        print("이제 python intake.py plan <파일> 로 표를 보고 apply 하세요(날짜가 '확인 필요'면 md 의 date 를 고친 뒤).")
        return 0
    if a.cmd == "bookmarklet":
        url = bookmarklet()
        try:
            import subprocess
            subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $input"],
                           input=url, text=True, encoding="utf-8", check=True)
            print("즐겨찾기 주소를 클립보드에 넣었어요 — Chrome 즐겨찾기 추가 → 이름 '제미나이 내보내기', URL 칸에 붙여 넣기.")
        except (OSError, subprocess.CalledProcessError):
            print(url)
        return 0
    load_env()
    src = find_input(a.file)
    m = DATE_RE.search(src.stem)
    raw = src.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp949")  # 메모장 옛 저장 방식(ANSI)
    doc = parse(text, m.group(0) if m else "")
    acts = plan(doc)
    print(f"입력: {src.name}")
    print(table(doc, acts))
    if a.cmd == "plan":
        print("\n아무것도 바꾸지 않았어요. 표가 맞으면 apply 로 넣습니다.")
        return 0
    skip = {s.strip() for s in a.skip.split(",") if s.strip()}
    _, screen, fails = apply(doc, acts, vault_path(), open_sheet, open_notion, skip)
    print("\n" + "\n".join(screen))
    if fails:
        print(f"\n실패 {fails}건 — 고친 뒤 다시 apply 하면 이미 넣은 것은 건너뜁니다.")
        return 1
    if src.parent == data_dir(SKILL) / "inbox":
        done = src.parent / "done"
        done.mkdir(exist_ok=True)
        src.replace(done / src.name)
        print(f"\n입력 파일을 inbox\\done 으로 옮겼어요. 볼트 파일은 Obsidian Git 자동 백업이 올립니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
