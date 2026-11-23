#!/usr/bin/env python3
"""학생선수 대회 참가 처리 — 공문 읽기 → 나이스 학교장확인서 결재요청 → 출석인정결석 처리 기안문.

절차·화면 정보: references/student-athlete-workflow.md

사용법 (모든 결과는 짧게 출력하고 자세한 내용은 data_dir 파일에 저장 — 토큰 절약)
  python neis_student_athlete.py run <공문 파일...> [--students 이름,이름] [--days ...]
      한 번에: case → draft → request(체크만). 대부분 이것 하나면 됨
  python neis_student_athlete.py status
      나이스 [체육]>학생선수출결관리 조회 → 학생선수·출석인정결석 허용/사용/잔여일수 캐시(athletes.json)
  python neis_student_athlete.py case <공문 파일...> [--students 이름,이름] [--days 2026-10-21~2026-10-23] [--no-cert]
      공문(odt/hwpx/pdf/xlsx/txt) 읽기 → 대회명·기간·장소·관련문서·대상 학생 추출 → cases/<날짜>_<대회>.json
  python neis_student_athlete.py draft <case.json> [--edufine]
      출석인정결석 처리 기안 제목·본문 + 담임 안내 메시지 생성(txt, 클립보드). --edufine: 에듀파인 기안기에 주입
  python neis_student_athlete.py request <case.json> [--apply --confirm APPLY_NEIS] [--sancr 이름:결재,이름:검토]
      [체육]>학교장확인서출력관리 > 결재요청 팝업에서 대상 학생 체크(기본은 여기서 멈춤)
      --apply: 승인요청 → 기안창. --sancr 를 주면 결재선 지정·저장까지. 상신은 submit 명령으로 따로.
  python neis_student_athlete.py submit [--confirm APPLY_NEIS]
      열려 있는 기안창(wam_woapm07_p00)의 결재선을 출력하고, --confirm 시 [상신]
  python neis_student_athlete.py register <이름> --item 축구 [--personal] [--start 2026-03-02] [--apply --confirm APPLY_NEIS]
      [체육]>학생선수관리 > 등록: 학생 찾기·종목·운동시작일 입력(기본은 저장 전 멈춤)

탭: 같은 9222 Chrome을 다른 세션도 쓰므로 전용 NEIS 탭을 만들어 data_dir/tab.txt 에 고정한다(--tab 으로 지정 가능).
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import glob
import html
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(next(p / "_shared" for p in _pl.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import load_env, data_dir  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.environ["no_proxy"] = "localhost,127.0.0.1"

load_env()
DATA = data_dir("admin-neis-bot", "student_athlete")
CASES = DATA / "cases"
CASES.mkdir(parents=True, exist_ok=True)
CDP = "http://127.0.0.1:9222"
NEIS_MAIN = "https://gbe.neis.go.kr/jsp/main.jsp"
WD = "월화수목금토일"
ROLE = {"결재": "2", "검토": "7", "협조": "4", "공람": "5"}

APP_ATTEND = "phe_pheam09_m00"   # 학생선수출결관리
APP_ATHLETE = "phe_pheam07_m00"  # 학생선수관리
APP_CERT = "phe_pheam10_m00"     # 학교장확인서출력관리
APP_CERT_POP = "phe_pheam10_p00"  # 학교장확인서 결재요청 팝업
APP_DRAFT = "wam_woapm07_p00"    # 기안(상신) 창
APP_SANCR = "wam_woapm07_p04"    # 결재자지정 창


def log(*a):
    print(*a, flush=True)


# ─────────────────────────── CDP ───────────────────────────
class Tab:
    """전용 NEIS 탭 하나에 붙어서 연결을 유지(가려진 창에서도 그리도록 focus emulation)."""

    def __init__(self, tab_id: str | None = None):
        import websocket  # noqa: F401
        self.id = tab_id or self._pick_tab()
        self.ws = None
        self.n = 0
        self._connect()

    @staticmethod
    def _targets():
        return json.loads(urllib.request.urlopen(f"{CDP}/json", timeout=5).read())

    def _pick_tab(self) -> str:
        saved = DATA / "tab.txt"
        ids = {t["id"]: t for t in self._targets() if t.get("type") == "page"}
        env = os.environ.get("NEIS_TAB")
        for cand in (env, saved.read_text().strip() if saved.exists() else None):
            if cand and cand in ids:
                return cand
        req = urllib.request.Request(f"{CDP}/json/new?{NEIS_MAIN}", method="PUT")
        t = json.loads(urllib.request.urlopen(req, timeout=10).read())
        saved.write_text(t["id"])
        log(f"[tab] 전용 NEIS 탭 새로 만듦: {t['id']}")
        time.sleep(6)
        return t["id"]

    def _connect(self):
        import websocket
        t = next(x for x in self._targets() if x["id"] == self.id)
        self.ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=90, suppress_origin=True)
        self.cmd("Emulation.setFocusEmulationEnabled", {"enabled": True})

    def cmd(self, method, params=None):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params or {}}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == self.n:
                return m.get("result", m)

    def js(self, expr: str, timeout_ms=60000):
        r = self.cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True, "timeout": timeout_ms})
        if "exceptionDetails" in r:
            raise RuntimeError(str(r["exceptionDetails"].get("exception", {}).get("description", r))[:400])
        return r.get("result", {}).get("value")

    def click(self, x, y):
        for t in ("mouseMoved", "mousePressed", "mouseReleased"):
            self.cmd("Input.dispatchMouseEvent", {"type": t, "x": x, "y": y, "button": "left", "clickCount": 1})

    def shot(self, name: str) -> Path:
        p = DATA / f"{name}.png"
        p.write_bytes(base64.b64decode(self.cmd("Page.captureScreenshot", {"format": "png"})["data"]))
        return p


# 페이지 안 공용 함수(한 번 주입)
HELPERS = r"""
window.__sa = {
  apps: () => cpr.core.Platform.INSTANCE.getAllRunningAppInstances(),
  app: k => __sa.apps().filter(a => a.app && a.app.id.includes(k)).pop(),
  sleep: ms => new Promise(r => setTimeout(r, ms)),
  // cpr 알림/확인창: 메시지 읽고 '확인/예' 클릭
  dialogs: (click) => {
    const out = [];
    __sa.apps().forEach(a => {
      if (!a.app || !/app\/cmn\/(alert|confirm)/.test(a.app.id)) return;
      let msg = '';
      try { a.getContainer().getAllRecursiveChildren().forEach(c => { const v = (c.value ?? c.text ?? ''); if (c.type === 'output' && v) msg += String(v) + ' '; }); } catch (e) {}
      out.push(a.app.id.split('/').pop() + ': ' + msg.trim().slice(0, 200));
      if (click) { try { a.getContainer().getAllRecursiveChildren().some(c => { const v = c.value || c.text || ''; if (c.type === 'button' && (v === '확인' || v === '예')) { c.click(); return true; } }); } catch (e) {} }
    });
    return out;
  },
  // 화면에 보이는 글자 요소의 중심 좌표(가장 작은 요소 우선, 영역 필터)
  findText: (t, xmin, xmax, ymin, ymax) => {
    // 메뉴 글자 뒤에 숨은 접근성 문구("0단계 메뉴항목")가 붙으므로 첫 줄만 비교
    const first = e => (e.innerText || '').trim().split('\n')[0].replace(/\s*\d단계.*$/, '').trim();
    const els = [...document.querySelectorAll('div,span,a,li,p,button')].filter(e => {
      if (!e.getClientRects().length || first(e) !== t) return false;
      const r = e.getBoundingClientRect();
      const cx = r.x + r.width / 2, cy = r.y + r.height / 2;
      return r.width > 0 && cx >= (xmin ?? 0) && cx <= (xmax ?? 1e5) && cy >= (ymin ?? 0) && cy <= (ymax ?? 1e5);
    }).map(e => e.getBoundingClientRect()).sort((a, b) => a.width * a.height - b.width * b.height);
    return els.length ? [Math.round(els[0].x + els[0].width / 2), Math.round(els[0].y + els[0].height / 2)] : null;
  },
  rows: (app, ds, cols) => { const d = app.lookup(ds); const o = []; for (let i = 0; i < d.getRowCount(); i++) { const r = d.getRowData(i); o.push(cols ? Object.fromEntries(cols.map(c => [c, r[c]])) : r); } return o; },
};
true
"""


class Neis:
    def __init__(self, tab_id=None):
        self.t = Tab(tab_id)
        self.ensure_login()
        self.t.js(HELPERS)

    def ensure_login(self):
        ok = self.t.js("Boolean(window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE && document.title !== '로그인')")
        if ok:
            return
        log("[login] 나이스 세션 없음 → 업무포털 SSO 링크로 이동")
        portal = next((x for x in Tab._targets() if "eduptl.kr" in x.get("url", "") and x.get("type") == "page"), None)
        if not portal:
            sys.exit("업무포털 탭이 없습니다. 9222 Chrome에서 업무포털에 로그인해 주세요.")
        p = Tab(portal["id"])
        url = p.js("(document.querySelector('a.menuBtn[id*=\"gbe.neis.go.kr/cmc_fcm\"]')||{}).id||null")
        if not url:
            sys.exit("업무포털에서 나이스 SSO 링크를 찾지 못했습니다.")
        self.t.js(f"location.href={json.dumps(url)}; 1")
        for _ in range(30):
            time.sleep(2)
            try:
                if self.t.js("Boolean(window.cpr && cpr.core.Platform.INSTANCE && document.title !== '로그인' && cpr.core.Platform.INSTANCE.getAllRunningAppInstances().length > 1)"):
                    time.sleep(3)
                    return
            except Exception:
                pass
        sys.exit("나이스 로그인 대기 시간 초과")

    def js(self, body: str, timeout_ms=60000):
        return self.t.js("(async()=>{ if(!window.__sa){" + HELPERS + "} " + body + " })()", timeout_ms)

    def running(self, key) -> bool:
        return bool(self.js(f"return Boolean(__sa.app({json.dumps(key)}));"))

    def click_text(self, text, **area) -> bool:
        pos = self.js(f"return __sa.findText({json.dumps(text)}, {area.get('xmin', 'undefined')}, {area.get('xmax', 'undefined')}, {area.get('ymin', 'undefined')}, {area.get('ymax', 'undefined')});")
        if not pos:
            return False
        self.t.click(*pos)
        return True

    def dialogs(self, click=True, wait=0.0):
        time.sleep(wait)
        return self.js(f"return __sa.dialogs({str(click).lower()});") or []

    def open_screen(self, app_key: str, leaf: str):
        """[체육] > 학생선수관리 트리의 화면 열기. 이미 떠 있으면 하단 MDI 탭만 누른다."""
        if self.running(app_key):
            self.click_text(leaf, ymin=880)  # 하단 MDI 탭
            time.sleep(1)
            return
        if not self.click_text(leaf, xmax=280, ymin=170):  # 왼쪽 트리에 이미 보이면 바로
            self.click_text("체육", ymin=40, ymax=80)
            time.sleep(1.5)
            self.click_text("학생선수관리", xmin=200, xmax=450, ymin=90, ymax=360)  # 메가메뉴
            time.sleep(2)
            if not self.click_text(leaf, xmax=280, ymin=170):
                raise RuntimeError(f"메뉴 '{leaf}'를 찾지 못했습니다")
        for _ in range(20):
            time.sleep(1)
            if self.running(app_key):
                time.sleep(2)
                return
        raise RuntimeError(f"화면 {app_key} 가 열리지 않았습니다")


# ─────────────────────────── status ───────────────────────────
def cmd_status(a):
    n = Neis(a.tab)
    n.open_screen(APP_ATTEND, "학생선수출결관리")
    rows = n.js(f"""const app=__sa.app('{APP_ATTEND}'); app.lookup('btnSearch').click(); await __sa.sleep(4000);
      return __sa.rows(app,'dsList',['stuNm','grd','clsNm','stuClsNo','itemCdNm','pheStuInvlNo','stuInvlNo','gijunil','dspAbeDdCnt','dspRestAbeDdCnt']);""")
    msgs = n.dialogs(True, 1.5)
    ath = [{"name": r["stuNm"], "grade": r["grd"], "class": r["clsNm"], "no": r["stuClsNo"], "item": r["itemCdNm"],
            "allow": r["gijunil"], "used": r["dspAbeDdCnt"], "left": r["dspRestAbeDdCnt"], "pheNo": r["pheStuInvlNo"]} for r in rows or []]
    (DATA / "athletes.json").write_text(json.dumps({"updated": dt.datetime.now().isoformat(timespec="minutes"), "athletes": ath}, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"학생선수 {len(ath)}명 (허용/사용/잔여 출석인정결석일)")
    for x in ath:
        log(f"  {x['grade']}-{x['class']} {x['name']} {x['item']}  {x['allow']}/{x['used']}/{x['left']}")
    if msgs:
        log("  [알림] " + " / ".join(msgs))


# ─────────────────────────── 공문 읽기 ───────────────────────────
def read_text(path: Path) -> str:
    s = path.suffix.lower()
    try:
        if s == ".odt":
            x = zipfile.ZipFile(path).read("content.xml").decode("utf8")
            x = re.sub(r"<text:(p|h)[^>]*>", "\n", x)
            x = re.sub(r"<text:tab/>", "\t", x)
        elif s == ".hwpx":
            z = zipfile.ZipFile(path)
            x = "".join(z.read(n).decode("utf8") for n in sorted(z.namelist()) if re.match(r"Contents/section\d+\.xml", n))
            x = re.sub(r"</hp:p>", "\n", x)
            x = re.sub(r"</hp:tc>", " | ", x)
        elif s == ".pdf":
            import fitz
            return "\n".join(p.get_text() for p in fitz.open(path))
        elif s in (".xlsx", ".xlsm"):
            try:
                import openpyxl
                wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
                return "\n".join(" | ".join("" if v is None else str(v) for v in row) for ws in wb for row in ws.iter_rows(values_only=True))
            except zipfile.BadZipFile:
                return path.read_text(encoding="utf8", errors="replace")  # 확장자만 xlsx인 텍스트 덤프
        elif s in (".txt", ".md", ".csv"):
            return path.read_text(encoding="utf8", errors="replace")
        else:
            return ""
    except Exception as e:  # noqa: BLE001
        return f"[읽기 실패 {path.name}: {e}]"
    x = html.unescape(re.sub(r"<[^>]+>", "", x))
    return re.sub(r"\n\s*\n+", "\n", x)


DATE_RE = re.compile(r"(20\d\d)\s*[.\-년]\s*(\d{1,2})\s*[.\-월]\s*(\d{1,2})\s*[.일]?")


def parse_dates(s: str) -> list[dt.date]:
    out, year = [], None
    # "2026. 10. 21.(수) ~ 10. 25.(일)" 처럼 뒤쪽 연도 생략도 처리
    for m in re.finditer(r"(?:(20\d\d)\s*[.\-년]\s*)?(\d{1,2})\s*[.\-월]\s*(\d{1,2})\s*[.일]?", s):
        if m.group(1):
            year = int(m.group(1))
        if not year:
            continue
        try:
            out.append(dt.date(year, int(m.group(2)), int(m.group(3))))
        except ValueError:
            pass
    return out


def field(text: str, *keys) -> str:
    for k in keys:
        m = re.search(rf"{k}\s*[:：]\s*(.+)", text)
        if m:
            return m.group(1).strip()
    return ""


def parse_gongmun(main: str) -> dict:
    lines = [l.strip() for l in main.splitlines() if l.strip()]
    title = ""
    for i, l in enumerate(lines):
        m = re.match(r"^제\s*목\s*(.*)$", l)
        if m:
            title = m.group(1).strip() or (lines[i + 1] if i + 1 < len(lines) else "")
            break
    sender = lines[0] if lines else ""
    for l in lines[:4]:
        if not re.search(r"교육|따뜻|함께", l) or re.search(r"(청|회|협회|연맹|학교)$", l):
            sender = l
            break
    m = re.search(r"『([^』]+)』|「([^」]+)」", title)
    contest = field(main, "대회명", "대 회 명", "행사명") or (m.group(1) or m.group(2) if m else "") or title
    contest = re.sub(r"^[『「]|[』」]$", "", contest.strip())
    period_line = field(main, "대회기간", "대회일시", "대회일자", "기\s*간", "일\s*시", "일\s*자")
    place = field(main, "대회장소", "장\s*소")
    # 시행번호: '시행'(또는 '시  행') 다음 줄, 날짜는 그 뒤 괄호 안
    docno, docdate = "", ""
    i = next((k for k, l in enumerate(lines) if re.fullmatch(r"시\s*행", l)), None)
    if i is not None:
        docno = lines[i + 1] if i + 1 < len(lines) else ""
        ds = parse_dates(" ".join(lines[i + 1:i + 5]))
        docdate = ds[0].isoformat() if ds else ""
    return {"title": title, "sender": sender, "contest": contest, "period_text": period_line,
            "period": [d.isoformat() for d in parse_dates(period_line)], "place": place,
            "docno": docno, "docdate": docdate}


def weekdays(d1: dt.date, d2: dt.date) -> list[dt.date]:
    return [d1 + dt.timedelta(i) for i in range((d2 - d1).days + 1) if (d1 + dt.timedelta(i)).weekday() < 5]


def kdate(d: dt.date, with_year=True) -> str:
    s = f"{d.year}. {d.month}. {d.day}.({WD[d.weekday()]})" if with_year else f"{d.month}. {d.day}.({WD[d.weekday()]})"
    return s


def krange(d1: dt.date, d2: dt.date) -> str:
    return kdate(d1) if d1 == d2 else f"{kdate(d1)} ~ {kdate(d2, d1.year != d2.year)}"


def load_athletes() -> list[dict]:
    p = DATA / "athletes.json"
    return json.loads(p.read_text(encoding="utf-8"))["athletes"] if p.exists() else []


def cmd_case(a):
    files = [Path(f) for pat in a.files for f in (glob.glob(pat) or [pat])]
    texts = {f.name: read_text(f) for f in files if f.exists()}
    if not texts:
        sys.exit("읽을 공문 파일이 없습니다.")
    main_name = next((k for k in texts if "(본문)" in k), next(iter(texts)))
    info = parse_gongmun(texts[main_name])
    ath = load_athletes()
    allt = "\n".join(texts.values())
    if a.students:
        names = [s.strip() for s in a.students.split(",") if s.strip()]
    else:
        names = [x["name"] for x in ath if x["name"] in allt]
    students = []
    for nm in names:
        x = next((y for y in ath if y["name"] == nm), None)
        students.append({"name": nm, "grade": x["grade"] if x else "", "class": x["class"] if x else "",
                         "item": x["item"] if x else "", "left": x["left"] if x else "", "registered": bool(x)})
    if a.days:
        d = parse_dates(a.days.replace("~", " ~ "))
        d1, d2 = d[0], d[-1]
    elif info["period"]:
        d1, d2 = dt.date.fromisoformat(info["period"][0]), dt.date.fromisoformat(info["period"][-1])
    else:
        d1 = d2 = None
    days = weekdays(d1, d2) if d1 else []
    items = sorted({s["item"] for s in students if s["item"]})
    case = {
        **info,
        "item": a.item or (items[0] if len(items) == 1 else "/".join(items)),
        "students": students,
        "recog_days": [d.isoformat() for d in days],
        "cert": not a.no_cert,
        "attach_name": a.attach or "대회 공문",
        "files": [str(f) for f in files],
        "warnings": [],
    }
    if not students:
        case["warnings"].append("대상 학생을 찾지 못함 → --students 로 지정 (명단이 붙임 hwp 등 못 읽는 파일에 있을 수 있음)")
    for s in students:
        if not s["registered"]:
            case["warnings"].append(f"{s['name']}: 나이스 학생선수 미등록 → register 먼저")
        elif s["left"] not in ("", None) and days and int(str(s["left"]).split()[0] or 0) < len(days):
            case["warnings"].append(f"{s['name']}: 출석인정결석 잔여 {s['left']}일 < 인정일 {len(days)}일")
    if d1 and len(weekdays(d1, d2)) != (d2 - d1).days + 1:
        case["warnings"].append("대회 기간에 주말 포함 → 평일만 인정일로 잡음(공휴일·재량휴업일은 직접 확인)")
    slug = re.sub(r"[^\w가-힣]+", "_", case["contest"])[:30].strip("_")
    out = CASES / f"{(d1 or dt.date.today()).strftime('%Y%m%d')}_{slug}.json"
    out.write_text(json.dumps(case, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"[case] {out}")
    log(f"  대회: {case['contest']} | 장소: {case['place']} | 기간: {case['period_text']}")
    log(f"  관련: {case['sender']} {case['docno']}({case['docdate']})")
    log(f"  학생: " + ", ".join(f"{s['grade']}-{s['class']} {s['name']}({s['item'] or '?'})" for s in students))
    log(f"  인정일: {len(days)}일 " + (krange(days[0], days[-1]) if days else "(기간 못 찾음 → --days)"))
    for w in case["warnings"]:
        log(f"  ⚠ {w}")


# ─────────────────────────── 기안문 ───────────────────────────
def build_draft(c: dict) -> tuple[str, str, str]:
    item = c.get("item") or "종목"
    contest = c["contest"]
    cert = c.get("cert", True)
    tail = " 및 학교장 확인서 발급" if cert else ""
    title = f"학생선수({item})의 『{contest}』 참가에 따른 출석인정결석 처리{tail}"
    days = [dt.date.fromisoformat(d) for d in c.get("recog_days", [])]
    per = [dt.date.fromisoformat(d) for d in c.get("period", [])]
    period = krange(per[0], per[-1]) if per else c.get("period_text", "")
    plabel = "일자" if per and per[0] == per[-1] else "기간"
    rel_date = ""
    if c.get("docdate"):
        d = dt.date.fromisoformat(c["docdate"])
        rel_date = f"({d.year}. {d.month}. {d.day}.)"
    rel = f"{c.get('sender', '')} {c.get('docno', '')}{rel_date}".strip()
    st = c["students"]
    if st and all(s["grade"] and s["class"] for s in st):
        who = ", ".join(f"{s['grade']}-{s['class']} {s['name']}" for s in st)
    else:
        who = ", ".join(s["name"] for s in st)
    if days:
        cnt = f"({len(days)}일)" if len(days) == 1 else f"({len(days)}일간)"
        recog = f"{krange(days[0], days[-1])} {cnt}"
    else:
        recog = "(인정 기간 입력)"
    verb = "출석인정결석 처리 및 학교장 확인서 발급을" if cert else "출석인정결석을"
    body = [
        f"1. 관련: {rel}",
        f"2. 위 호와 관련하여, 본교 학생선수({item})의 『{contest}』 참가에 따른 {verb} 다음과 같이 처리하고자 합니다.",
        "  가. 대회 개요",
        f"    1) 대회명: {contest}",
        f"    2) {plabel}: {period}",
        f"    3) 장소: {c.get('place', '')}",
        f"  나. 대상 학생: {who}",
        "  다. 출석인정결석 처리 내역",
        f"    1) 인정 기간: {recog}",
        f"    2) 내용: {contest} 참가",
        "  라. 학생선수 학습권 보장 계획",
        "    1) 대회 참가 전후 담임교사 주관 기초학력 보충지도 실시함.",
    ]
    if cert:
        body += ["  마. 학교장 확인서 발급",
                 "    1) 본교는 위 학생선수에 대한 학교장 확인서를 나이스시스템으로 발급해서 발송하고자 함."]
    body.append(f"붙임  {c.get('attach_name', '대회 공문')} 1부.  끝.")
    msg = (f"[학생선수 출석인정결석 안내] {who} 학생이 『{contest}』 참가로 {recog} 출석인정결석 대상입니다. "
           f"나이스 출결에 '출석인정(학생선수 대회 참가)'로 처리 부탁드리며, 대회 전후 기초학력 보충지도도 부탁드립니다. (체육 담당)")
    return title, "\n".join(body), msg


def set_clipboard(text: str):
    try:
        subprocess.run(["clip"], input=text.encode("utf-16le"), check=True)
    except Exception:  # noqa: BLE001
        pass


def cmd_draft(a):
    c = json.loads(Path(a.case).read_text(encoding="utf-8"))
    title, body, msg = build_draft(c)
    out = Path(a.case).with_suffix(".draft.txt")
    out.write_text(f"[제목]\n{title}\n\n[본문]\n{body}\n\n[담임 안내 메시지]\n{msg}\n", encoding="utf-8")
    set_clipboard(body)
    log(f"[draft] {out} (본문 클립보드 복사됨)")
    log(f"  제목: {title}")
    if a.edufine:
        bot = Path(__file__).resolve().parents[1] / "admin-edufine" / "playwright_gongmun_draft.py"
        log("[draft] 에듀파인 기안기 주입 실행…")
        subprocess.run([sys.executable, str(bot), title, body], check=False)


# ─────────────────────────── 학교장확인서 결재요청 ───────────────────────────
def need_confirm(a):
    if getattr(a, "apply", False) and a.confirm != "APPLY_NEIS":
        sys.exit("실제 실행은 --confirm APPLY_NEIS 가 필요합니다.")


def cmd_request(a):
    need_confirm(a)
    c = json.loads(Path(a.case).read_text(encoding="utf-8"))
    names = [s["name"] for s in c["students"]]
    n = Neis(a.tab)
    n.open_screen(APP_CERT, "학교장확인서출력관리")
    if not n.running(APP_CERT_POP):
        n.js(f"__sa.app('{APP_CERT}').lookup('btnReq').click(); return 1;")
        for _ in range(20):
            time.sleep(1)
            if n.running(APP_CERT_POP):
                break
        else:
            sys.exit("결재요청 팝업이 열리지 않았습니다.")
        time.sleep(2)
    res = n.js(f"""const p=__sa.app('{APP_CERT_POP}'); p.lookup('btnSearch').click(); await __sa.sleep(4000);
      const g=p.lookup('grdList'); const want={json.dumps(names)}; const hit=[], all=[];
      const ds=p.lookup('dsList');
      for(let i=0;i<ds.getRowCount();i++){{ const nm=ds.getValue(i,'stuNm'); all.push(nm);
        const on=want.includes(nm); try{{ g.setCheckRowIndex(i,on); }}catch(e){{}} if(on) hit.push(ds.getValue(i,'grdCd')+'-'+Number(ds.getValue(i,'clsCd'))+' '+nm+'('+ds.getValue(i,'itemCdNm')+')'); }}
      return {{hit, all, checked: g.getCheckRowIndices ? g.getCheckRowIndices() : null}};""")
    n.dialogs(True, 1)
    miss = [x for x in names if not any(x in h for h in res["hit"])]
    log(f"[request] 체크: {', '.join(res['hit']) or '없음'}" + (f" | 목록에 없음: {', '.join(miss)}" if miss else ""))
    shot = n.t.shot("request_checked")
    log(f"  화면: {shot}")
    if miss:
        sys.exit("나이스 학생선수 목록에 없는 학생이 있습니다 → register 후 다시.")
    if not a.apply:
        log("  (확인만 함. 실제 요청: --apply --confirm APPLY_NEIS)")
        return
    n.js(f"__sa.app('{APP_CERT_POP}').lookup('btnAprv').click(); return 1;")
    draft_open = False
    for _ in range(25):  # 확인창 → 저장 → 기안창 (5~20초 늦게 뜸)
        time.sleep(1.5)
        for m in n.dialogs(True):
            log(f"  [대화상자] {m}")
            if "alert" in m and ("불가능" in m or "없습니다" in m or "초과" in m):
                sys.exit("나이스가 요청을 거부했습니다(위 메시지 참고).")
        if n.running(APP_DRAFT):
            draft_open = True
            break
    if not draft_open:
        n.t.shot("request_after")
        sys.exit("기안창이 뜨지 않았습니다. 화면을 확인하세요.")
    log("[request] 기안창 열림")
    cfg = DATA / "config.json"
    sancr = a.sancr or (json.loads(cfg.read_text(encoding="utf-8")).get("cert_sancr") if cfg.exists() else None)
    if sancr:
        set_sancr(n, sancr)
        if a.sancr and a.save_sancr:
            c0 = json.loads(cfg.read_text(encoding="utf-8")) if cfg.exists() else {}
            c0["cert_sancr"] = a.sancr
            cfg.write_text(json.dumps(c0, ensure_ascii=False, indent=1), encoding="utf-8")
            log(f"  결재선 기본값 저장: {cfg}")
    show_draft(n)
    log("  상신: python neis_student_athlete.py submit --confirm APPLY_NEIS")


def set_sancr(n: Neis, spec: str):
    """결재자지정(p04)에서 '이름:구분' 목록대로 추가 후 저장(ISSUE-005 검증 순서)."""
    n.js(f"__sa.app('{APP_DRAFT}').lookup('btnSelectSancr').click(); return 1;")
    for _ in range(20):
        time.sleep(1)
        if n.running(APP_SANCR):
            break
    else:
        sys.exit("결재자지정 창이 열리지 않았습니다.")
    time.sleep(2)
    for part in spec.split(","):
        name, _, role = part.partition(":")
        code = ROLE.get(role.strip() or "결재", "2")
        r = n.js(f"""const p=__sa.app('{APP_SANCR}'); const ds=p.lookup('dsMain'); let row=-1, note='';
          for(let i=0;i<ds.getRowCount();i++){{ if(ds.getValue(i,'userNm')=={json.dumps(name.strip())}){{ row=i; note=String(Object.values(ds.getRowData(i)).join(' ')); break; }} }}
          if(row<0) return {{err:'not found'}};
          const rd=p.lookup('rdbCn'); rd.value='{code}'; try{{ rd.dispatchEvent(new cpr.events.CSelectionEvent('selection-change',{{}})); }}catch(e){{}}
          await __sa.sleep(500); p.lookup('grdUserListFrom').selectRows([row]); p.lookup('btn1').click(); await __sa.sleep(1500);
          const to=p.lookup('grdUserListTo').dataSet; const line=[]; for(let i=0;i<to.getRowCount();i++) line.push(to.getValue(i,'userNm')+'/'+to.getValue(i,'atrzScNm'));
          return {{line, absent: /부재/.test(note)}};""")
        if r.get("err"):
            sys.exit(f"결재자 '{name}' 를 찾지 못했습니다.")
        log(f"  결재선: {' → '.join(r['line'])}" + ("  ⚠ 부재중 표시" if r.get("absent") else ""))
    n.js(f"__sa.app('{APP_SANCR}').lookup('btn4').click(); return 1;")
    time.sleep(3)
    n.dialogs(True, 1)


def show_draft(n: Neis):
    line = n.js(f"""const p=__sa.app('{APP_DRAFT}'); const ds=p.lookup('dsSancr'); const o=[];
      for(let i=0;i<ds.getRowCount();i++){{ const r=ds.getRowData(i); o.push((r.userNm||r.sancrNm||r.atrzUserNm||'?')+'/'+(r.atrzScNm||r.atrzKndNm||'')); }} return o;""")
    log(f"  기안창 결재선: {' → '.join(line) if line else '(비어 있음 → --sancr 필요)'}")
    log(f"  화면: {n.t.shot('draft_window')}")


def cmd_submit(a):
    n = Neis(a.tab)
    if not n.running(APP_DRAFT):
        sys.exit("열려 있는 기안창이 없습니다.")
    show_draft(n)
    if a.confirm != "APPLY_NEIS":
        log("  (상신하려면 --confirm APPLY_NEIS)")
        return
    n.js(f"__sa.app('{APP_DRAFT}').lookup('btnDrft').click(); return 1;")
    for _ in range(20):  # 부재중 경고 → 상신 확인 → 완료 알림
        time.sleep(2)
        for m in n.dialogs(True):
            log(f"  [대화상자] {m}")
            if "완료" in m:
                log("[submit] 상신 완료")
                return
        if not n.running(APP_DRAFT):
            log("[submit] 기안창 닫힘(상신된 것으로 보임) → 학교장확인서출력관리에서 확인")
            return
    log(f"[submit] 완료 메시지를 못 봄. 화면: {n.t.shot('submit_after')}")


# ─────────────────────────── 신규 학생선수 등록 ───────────────────────────
def cmd_register(a):
    need_confirm(a)
    if any(x["name"] == a.name for x in load_athletes()) and not a.force:
        sys.exit(f"{a.name} 은(는) 이미 학생선수로 등록돼 있습니다(athletes.json). 종목 추가면 --force.")
    n = Neis(a.tab)
    n.open_screen(APP_ATHLETE, "학생선수관리")
    # 이전 실행의 입력폼이 열려 있으면 저장 없이 목록으로("변경사항이 반영되지 않았습니다" 확인창은 늦게 뜸)
    n.js(f"""const m=__sa.app('{APP_ATHLETE}'); const g=m.lookup('grpInsert');
      if(g&&g.visible){{ m.lookup('btnBack1').click(); for(let i=0;i<20&&g.visible;i++){{ await __sa.sleep(700); __sa.dialogs(true); }} }}
      m.lookup('btnIns').click(); return 1;""")
    pop = None
    for _ in range(20):
        time.sleep(1)
        pop = n.js("const a=__sa.apps().filter(x=>/phe_pheam07_p0\\d/.test(x.app.id)).pop(); return a?a.app.id:null;")
        if pop:
            break
    if not pop:
        sys.exit("학생 찾기 팝업이 열리지 않았습니다.")
    time.sleep(2)
    key = pop.split("/")[-1]
    # 1) 학생 찾기 팝업: 성명 조회 → 행 선택 → 확인
    # 학년 콤보가 필수(기본 1학년) → 학년을 모르면 1~6학년 차례로 조회
    rows = []
    for g in ([str(a.grade)] if a.grade else ["1", "2", "3", "4", "5", "6"]):
        r = n.js(f"""const p=__sa.app('{key}'); p.lookup('cmbGrd').value='{g}'; await __sa.sleep(500); p.lookup('ipbStuFlnm').value={json.dumps(a.name)};
          p.lookup('btnSearch').click(); await __sa.sleep(2500);
          const ds=p.lookup('dsStuList'); const rows=[]; for(let i=0;i<ds.getRowCount();i++) rows.push({{i, nm:ds.getValue(i,'stuFlnm'), g:ds.getValue(i,'grd'), c:ds.getValue(i,'clsNm'), no:ds.getValue(i,'clsNo')}});
          return rows;""")
        n.dialogs(True)
        hit = [x for x in r if x["nm"] == a.name]
        if hit:
            rows, grade_found = hit, g
            break
    if len(rows) != 1:
        sys.exit(f"학생 '{a.name}' 후보 {len(rows)}명 → --grade 로 좁히세요.")
    s0 = rows[0]
    n.js(f"const p=__sa.app('{key}'); p.lookup('grdStuList').selectRows([{s0['i']}]); await __sa.sleep(300); p.lookup('btnSubmit').click(); return 1;")
    time.sleep(3)
    n.dialogs(True, 0.5)
    # 2) 입력폼: 종목·개인운동선수·운동시작일자
    start = (a.start or dt.date.today().isoformat()).replace("-", "")
    # 개인운동선수 체크 → 전체 종목 콤보(cmbItemCd2), 아니면 학교운동부 종목 콤보(cmbItemCd3). 체크 먼저, 보이는 콤보에 종목.
    # 주의: 이벤트를 JS로 강제 발생시키면 콤보 항목이 두 번 붙어 "value of the item is duplicated" 오류 → 체크박스는 실제 마우스 클릭
    cbx = n.js(f"""const m=__sa.app('{APP_ATHLETE}'); const cb=m.lookup('cbxSptsYn'); const r=document.getElementById('uuid-'+cb.uuid).getBoundingClientRect();
      return {{v: cb.value, x: Math.round(r.x+10), y: Math.round(r.y+r.height/2)}};""")
    if (cbx["v"] == "Y") != bool(a.personal):
        n.t.click(cbx["x"], cbx["y"])
        time.sleep(1.5)
    form = n.js(f"""const m=__sa.app('{APP_ATHLETE}'); const it={json.dumps(a.item or '')}, dt={json.dumps(a.detail or '')};
      const cb=m.lookup('cbxSptsYn');
      const pick=(c,t)=>{{ if(!t) return c.getSelectionFirst? (c.getSelectionFirst()||{{}}).label : c.value; const items=c.getItems(); const hit=items.find(x=>x.label===t)||items.find(x=>x.label.includes(t));
        if(!hit) return 'X:'+items.slice(0,30).map(x=>x.label).join('/'); c.selectItemByValue(hit.value); return hit.label; }};
      const combo=['cmbItemCd2','cmbItemCd3'].map(id=>m.lookup(id)).find(c=>c.visible);
      const item=pick(combo,it); await __sa.sleep(1500);
      const detail=pick(m.lookup('cmbDtlItemCd'),dt);
      m.lookup('dti8').value='{start}';
      const ins=m.lookup('dsInsert'); return {{item, detail, stu: ins.getRowCount()? (ins.getValue(0,'grdCdNm')+' '+ins.getValue(0,'clsNm')+' '+ins.getValue(0,'stuNm')) : '', start: m.lookup('dti8').value, personal: cb.value}};""")
    log(f"[register] {form['stu']} | 종목 {form['item']} / {form['detail']} | 개인운동선수 {form['personal']} | 운동시작 {form['start']}")
    if str(form["item"]).startswith("X:") or not a.item:
        log("  ⚠ 종목을 못 골랐습니다(--item 확인). 화면에서 직접 고르세요.")
    log(f"  화면: {n.t.shot('register_form')}")
    if not a.apply:
        log("  (저장 전 멈춤. 세부종목·비고는 화면에서 확인. 저장: --apply --confirm APPLY_NEIS)")
        return
    n.js(f"__sa.app('{APP_ATHLETE}').lookup('btnSave').click(); return 1;")
    for _ in range(10):
        time.sleep(1.5)
        for m in n.dialogs(True):
            log(f"  [대화상자] {m}")
    log(f"  저장 후 화면: {n.t.shot('register_after')} → status 로 다시 확인")


def cmd_run(a):
    """case → draft → request(체크만) 한 번에. 끝에 다음 할 명령만 알려 줌."""
    before = set(CASES.glob("*.json"))
    cmd_case(a)
    made = sorted(set(CASES.glob("*.json")) - before) or sorted(CASES.glob("*.json"), key=lambda p: p.stat().st_mtime)[-1:]
    case = str(made[-1])
    c = json.loads(Path(case).read_text(encoding="utf-8"))
    if not c["students"] or any(not s["registered"] for s in c["students"]):
        log("→ 학생 지정/등록부터: --students 또는 register")
        return
    cmd_draft(argparse.Namespace(case=case, edufine=False))
    if not a.no_neis:
        cmd_request(argparse.Namespace(case=case, tab=a.tab, apply=False, confirm="", sancr=None, save_sancr=False))
    log(f"다음: request \"{case}\" --apply --confirm APPLY_NEIS  /  draft \"{case}\" --edufine")


# ─────────────────────────── main ───────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tab", help="NEIS 탭 target id (기본: data_dir/tab.txt 또는 새 탭)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("status")
    for name in ("case", "run"):
        p = sp.add_parser(name)
        p.add_argument("files", nargs="+")
        p.add_argument("--students")
        p.add_argument("--days", help="인정기간 YYYY-MM-DD~YYYY-MM-DD (평일만 셈)")
        p.add_argument("--item", help="종목(기본: 학생 종목)")
        p.add_argument("--attach", help="붙임 이름(기본: 대회 공문)")
        p.add_argument("--no-cert", action="store_true", help="학교장 확인서 발급 문구 빼기")
        if name == "run":
            p.add_argument("--no-neis", action="store_true", help="나이스 결재요청 체크 생략")
    p = sp.add_parser("draft")
    p.add_argument("case")
    p.add_argument("--edufine", action="store_true")
    p = sp.add_parser("request")
    p.add_argument("case")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--confirm", default="")
    p.add_argument("--sancr", help="결재선 '이름:검토,이름:결재' (구분: 결재/검토/협조/공람). 없으면 data_dir/config.json 의 cert_sancr")
    p.add_argument("--save-sancr", action="store_true", help="--sancr 값을 기본 결재선으로 저장")
    p = sp.add_parser("submit")
    p.add_argument("--confirm", default="")
    p = sp.add_parser("register")
    p.add_argument("name")
    p.add_argument("--item")
    p.add_argument("--grade", help="학년(주면 조회가 빠름, 동명이인 구분)")
    p.add_argument("--detail", help="세부종목(예: 개인전)")
    p.add_argument("--force", action="store_true", help="이미 등록된 학생도 진행(다른 종목 추가 등)")
    p.add_argument("--personal", action="store_true")
    p.add_argument("--start")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--confirm", default="")
    a = ap.parse_args()
    {"status": cmd_status, "case": cmd_case, "run": cmd_run, "draft": cmd_draft, "request": cmd_request,
     "submit": cmd_submit, "register": cmd_register}[a.cmd](a)


if __name__ == "__main__":
    main()
