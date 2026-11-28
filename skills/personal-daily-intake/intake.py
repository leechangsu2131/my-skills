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
        elif k in ("업무", "일기", "습관"):
            acts.append(Action("candidate", f"Notion {k} DB — 아직 연결 공유 전이라 daily 에만 (ISSUES ISSUE-001)", p))
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


class Notion:
    def __init__(self, token: str, reading_db: str):
        self.token, self.reading_db = token, reading_db

    def _call(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(
            "https://api.notion.com/v1/" + path, data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": "Bearer " + self.token, "Notion-Version": "2022-06-28",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)

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


def open_sheet():
    from schooltodo.db import SheetsDb
    return SheetsDb.from_env()


def open_notion() -> Notion:
    token = os.environ.get("NOTION_TOKEN", "").strip()
    db = os.environ.get("NOTION_READING_DB_ID", "").strip()  # .env 의 PERSONAL_DAILY_INTAKE__ 접두어는 load_env 가 뗀다
    if not token or not db:
        raise RuntimeError("중앙 .env 에 NOTION_TOKEN 과 PERSONAL_DAILY_INTAKE__NOTION_READING_DB_ID 가 필요해요")
    return Notion(token, db)


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
            elif a.dest == "notion-reading":
                if "notion" in skip:
                    note(i, a, "건너뜀(--skip)", ok=False)
                    continue
                nt = nt or (notion() if callable(notion) else notion)
                note(i, a, nt.add_book(a.data["book"], a.piece.get("내용"), doc.date))
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

def find_input(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    inbox = data_dir(SKILL, "inbox")
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
    ap.add_argument("cmd", choices=["plan", "apply", "ideas"])
    ap.add_argument("file", nargs="?")
    ap.add_argument("--skip", default="", help="쉼표로: sheet,notion")
    ap.add_argument("--done", default="", help="ideas: ISSUES 에 옮긴 번호(쉼표로)")
    ap.add_argument("--all", action="store_true", help="ideas: 옮긴 것도 보기")
    a = ap.parse_args(argv)
    if a.cmd == "ideas":
        return show_ideas(data_dir(SKILL) / "ideas.json", a.done, a.all)
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
