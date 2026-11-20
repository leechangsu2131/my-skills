"""출판사 교사 사이트에서 교사용 지도서 PDF를 받아 D:\\지도서 에 저장한다.

    C:\\Python313\\python.exe guide_download.py 수학 사회            # 받기
    C:\\Python313\\python.exe guide_download.py 수학 --list          # 목록만 보기
    C:\\Python313\\python.exe guide_download.py 사회 --with-plan     # 연간지도계획도 받기

- 수업 도우미 전용 크롬(config 의 chrome_profile / debug_port)에 붙어서 동작한다. 꺼져 있으면 켠다.
- 로그인이 풀려 있으면 크롬에 저장된 아이디·비밀번호로 채워진 "로그인하기"만 누른다(비밀번호는 다루지 않음).
- 학년·학기는 사이트의 '내 교과서 설정'을 따른다.
- 지원: 아이스크림(수학·사회 등). 다른 출판사는 PUBLISHERS 에 함수를 추가한다.
- selenium 이 필요하다(C:\\Python313 에 설치되어 있음).
"""
from __future__ import annotations

import argparse
import io
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile

import assistant_server as app  # 설정·크롬 실행 재사용

from selenium import webdriver
from selenium.webdriver.common.by import By

GUIDE_ROOT = pathlib.Path(r"D:\지도서")


def connect(cfg: dict, start_url: str):
    port = int(cfg.get("debug_port") or 9233)
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2)
    except OSError:
        app.open_window(start_url, "right", cfg)
        time.sleep(4)
    opts = webdriver.ChromeOptions()
    opts.debugger_address = f"127.0.0.1:{port}"
    return webdriver.Chrome(options=opts)


def safe(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", text).strip()


# ──────────────────────────── 아이스크림 ────────────────────────────

ISCREAM_LIST = "https://www.i-scream.co.kr/user/subject/SubjectChasiList.do"


def iscream_guides(driver, subject: str, with_plan: bool, grade_term: str = "", hint: str = "") -> tuple[str, list[dict]]:
    handles = driver.window_handles
    driver.switch_to.window(next((h for h in handles if _url(driver, h).startswith("https://www.i-scream")), handles[-1]))
    driver.get(ISCREAM_LIST)
    time.sleep(3)
    if "login" in driver.current_url:
        buttons = [b for b in driver.find_elements(By.XPATH, "//*[contains(normalize-space(.),'로그인하기') or @value='로그인하기']") if b.is_displayed()]
        if not buttons:
            raise RuntimeError("아이스크림 로그인 화면에서 로그인 단추를 찾지 못했어요.")
        buttons[0].click()
        time.sleep(4)
        driver.get(ISCREAM_LIST)
        time.sleep(3)
        if "login" in driver.current_url:
            raise RuntimeError("자동 로그인이 안 됐어요. 크롬에 아이스크림 비밀번호가 저장돼 있는지 확인해 주세요.")

    picked = driver.execute_script(
        r"""const a=[...document.querySelectorAll('[onclick^="fnSearchList"]')].find(x=>x.textContent.trim()===arguments[0]);
            if(!a) return false; a.click(); return true;""", subject)
    if not picked:
        raise RuntimeError(f"아이스크림 차시 화면에 '{subject}' 과목이 없어요.")
    time.sleep(4)
    term = driver.execute_script(
        r"""const t=[...document.querySelectorAll('h2,h3,h4,strong,span')].map(e=>e.textContent.trim()).find(t=>/^\d학년\d학기$/.test(t)); return t||'';""")
    if not driver.execute_script(
            r"""const b=document.querySelector('[onclick^="fnSearchTextbookMaterialList"]'); if(!b) return false; b.click(); return true;"""):
        raise RuntimeError("'전자책등 자료' 단추를 찾지 못했어요.")
    time.sleep(4)
    rows = driver.execute_script(
        r"""return [...document.querySelectorAll('[onclick*="fnPdfView"]')].map(a=>[a.textContent.replace(/\s+/g,' ').trim(), a.getAttribute('onclick')])""")
    wanted = {"교사용 지도서"} | ({"연간지도계획"} if with_plan else set())
    items, seen = [], set()
    for label, onclick in rows:
        m = re.search(r"fnPdfView\('([^']+)'\)", onclick or "")
        if label in wanted and m:
            path = re.sub(r"/{2,}", "/", m.group(1))
            if path not in seen:
                seen.add(path)
                items.append({"label": label, "url": "https://www.i-scream.co.kr" + path, "file": path.rsplit("/", 1)[-1]})
    return term, items


def _url(driver, handle) -> str:
    driver.switch_to.window(handle)
    return driver.current_url


# ──────────────────────────── 미래엔(엠티처) ────────────────────────────
# 교사용 DVD 를 학년·학기별 ZIP(수 GB)으로 준다. 서버가 부분 받기(Range)를 지원하므로
# ZIP 목록만 읽고 지도서 PDF 만 골라 꺼낸다.

MIRAEN_DVD = {"국어": "https://mid.m-teacher.co.kr:444/event/usbdownloadkr.mrn"}


class HttpRangeFile(io.RawIOBase):
    """원격 파일을 필요한 부분만 받아 읽는 파일 객체 (zipfile 에 넘길 수 있음)."""

    def __init__(self, url: str):
        self.url = urllib.parse.quote(url, safe=":/")
        with urllib.request.urlopen(urllib.request.Request(self.url, method="HEAD"), timeout=30) as res:
            self.size = int(res.headers["Content-Length"])
        self.pos = 0

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        end = min(self.size, self.pos + n) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        with urllib.request.urlopen(req, timeout=300) as res:
            data = res.read()
        self.pos += len(data)
        return data

    def readinto(self, buf):
        data = self.read(len(buf))
        buf[:len(data)] = data
        return len(data)


def _zip_name(info: zipfile.ZipInfo) -> str:
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode("cp437").decode("cp949")
    except UnicodeError:
        return info.filename


def pick_google_account(driver, hint: str) -> None:
    """구글 계정 선택 화면이 뜨면 hint 로 시작하는 계정을 누른다. 비밀번호 화면이면 멈춘다."""
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "accounts.google.com" not in driver.current_url:
            continue
        if driver.find_elements(By.CSS_SELECTOR, "input[type=password]"):
            raise RuntimeError("구글이 비밀번호를 묻고 있어요. 수업 도우미 크롬에서 구글에 다시 로그인해 주세요.")
        clicked = driver.execute_script(
            r"""const e=[...document.querySelectorAll('[data-identifier],[data-email]')].find(e=>(e.getAttribute('data-identifier')||e.getAttribute('data-email')||'').startsWith(arguments[0]));
                if(e){e.click(); return true} return false""", hint)
        if not clicked:
            raise RuntimeError(f"구글 계정 선택 화면에서 '{hint}'로 시작하는 계정을 찾지 못했어요.")
        time.sleep(6)


def miraen_login(driver, hint: str) -> None:
    driver.get("https://e.m-teacher.co.kr/pages/ele/Main.mrn")
    time.sleep(3)
    if not driver.execute_script("return [...document.querySelectorAll('a')].some(a=>a.offsetParent!==null && a.textContent.trim()==='로그인')"):
        return  # 이미 로그인
    driver.get("https://g.m-teacher.co.kr/pages/common/User/Login.mrn?redirectURI=https%3A%2F%2Fe.m-teacher.co.kr%2F")
    time.sleep(3)
    driver.execute_script("document.querySelector('button[data-sns-type=google]').click()")
    time.sleep(5)
    pick_google_account(driver, hint)


def miraen_guides(driver, subject: str, with_plan: bool, grade_term: str, hint: str = "") -> tuple[str, list[dict]]:
    if subject not in MIRAEN_DVD:
        raise RuntimeError(f"미래엔 {subject} 교사용 DVD 주소를 아직 몰라요.")
    grade, term = grade_term.split("-")
    miraen_login(driver, hint)
    driver.get(MIRAEN_DVD[subject])
    time.sleep(4)
    zip_url = driver.execute_script(
        r"""const r=[...document.querySelectorAll('tr')].find(t=>t.cells[0] && t.cells[0].textContent.trim()===arguments[0]+'학년');
            if(!r) return ''; const a=r.querySelectorAll('.btnDownload')[Number(arguments[1])-1]; return a? a.dataset.file : '';""",
        grade, term)
    if not zip_url:
        raise RuntimeError(f"미래엔 {subject} {grade_term} DVD 파일을 찾지 못했어요. (엠티처 로그인 확인)")
    archive = zipfile.ZipFile(HttpRangeFile(zip_url))
    items = []
    for info in archive.infolist():
        name = _zip_name(info)
        if re.search(r"지도서/pdf/[^/]+\.pdf$", name):
            items.append({"label": "교사용 지도서", "url": zip_url, "member": info, "archive": archive,
                          "file": name.rsplit("/", 1)[-1], "size": info.file_size})
    return f"{grade}학년{term}학기", items


# ──────────────────────────── 천재(T셀파 초등) ────────────────────────────
# 교과서 카드 → 수업 화면(curri_map) → "공통 자료" → "지도서" 행의 다운로드 단추.
# 파일 주소가 자바스크립트로 만들어지므로 크롬이 직접 받게 한다(받을 폴더를 CDP 로 지정).

TSHERPA_MAIN = "https://ele.tsherpa.co.kr/"


def tsherpa_guides(driver, subject: str, with_plan: bool, grade_term: str, hint: str = "") -> tuple[str, list[dict]]:
    driver.get(TSHERPA_MAIN)
    time.sleep(4)
    if "로그아웃" not in driver.find_element(By.TAG_NAME, "body").text:
        driver.execute_script("doLogin();")
        time.sleep(4)
        driver.execute_script("oauthLogin('google');")
        time.sleep(6)
        pick_google_account(driver, hint)
        driver.switch_to.window(next(h for h in driver.window_handles if _url(driver, h).startswith(TSHERPA_MAIN)))
    card = f"{subject} {grade_term}"
    found = driver.find_elements(By.XPATH, f"//li[contains(@class,'book-item')][.//*[normalize-space(text())='{card}']]//img")
    if not found:
        raise RuntimeError(f"T셀파 교과서 목록에 '{card}'가 없어요. (T셀파 '교과서 설정' 확인)")
    before = set(driver.window_handles)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'})", found[0])
    time.sleep(1)
    found[0].click()
    time.sleep(6)
    new = set(driver.window_handles) - before
    if new:
        driver.switch_to.window(new.pop())
    driver.execute_script(
        r"""const e=[...document.querySelectorAll('a,button,li')].find(x=>x.offsetParent!==null && x.textContent.replace(/\s+/g,'')==='공통자료'); if(e) e.click();""")
    time.sleep(4)
    wanted = ["지도서"] + (["연간 지도 계획"] if with_plan else [])
    items = []
    for label in wanted:
        if driver.execute_script(
                r"""return [...document.querySelectorAll('li.table-row')].some(x=>x.offsetParent!==null && x.querySelector('.file-name')?.textContent.trim()===arguments[0])""",
                label):
            items.append({"label": "교사용 지도서" if label == "지도서" else label, "url": driver.current_url,
                          "file": f"(T셀파 {label})", "browser": (driver, label)})
    grade = grade_term.split("-")[0]
    return f"{grade}학년", items  # 도덕·음악·미술처럼 1년 한 권이면 학년만


def browser_download(driver, label: str, folder: pathlib.Path) -> str:
    folder.mkdir(parents=True, exist_ok=True)
    driver.execute_cdp_cmd("Browser.setDownloadBehavior",
                           {"behavior": "allow", "downloadPath": str(folder), "eventsEnabled": True})
    before = set(p.name for p in folder.iterdir())
    driver.execute_script(
        r"""const e=[...document.querySelectorAll('li.table-row')].find(x=>x.offsetParent!==null && x.querySelector('.file-name')?.textContent.trim()===arguments[0]);
            e.querySelector('[aria-label="다운로드"]').click();""", label)
    for _ in range(300):
        time.sleep(2)
        new = set(p.name for p in folder.iterdir()) - before
        if new and not any(n.endswith((".crdownload", ".tmp")) for n in new):
            name = sorted(new)[0]
            return f"받음 {name} {(folder / name).stat().st_size / 1048576:.1f}MB"
        if not new and _ == 15:
            return "이미 있거나 다운로드가 시작되지 않았어요"
    return "시간 초과(10분)"


PUBLISHERS = {
    "아이스크림": (ISCREAM_LIST, iscream_guides),
    "미래엔": ("https://e.m-teacher.co.kr", miraen_guides),
    "천재교육": (TSHERPA_MAIN, tsherpa_guides),
}


# ──────────────────────────── 받기 ────────────────────────────

def nice_name(subject: str, term: str, item: dict) -> str:
    """math_jido_3-2-4.pdf → [수학]3-2_지도서_4단원.pdf"""
    m = re.search(r"(\d)-(\d)-(\d+)\.pdf$", item["file"])
    kind = "지도서" if item["label"] == "교사용 지도서" else safe(item["label"])
    if m:
        return f"[{subject}]{m.group(1)}-{m.group(2)}_{kind}_{m.group(3)}단원.pdf" if kind == "지도서" \
            else f"[{subject}]{m.group(1)}-{m.group(2)}_{kind}_{m.group(3)}.pdf"
    return f"[{subject}]{safe(term)}_{safe(item['file'])}"


def download(item: dict, dest: pathlib.Path) -> str:
    if "member" in item:  # ZIP 안의 파일만 꺼내기
        size = item["size"]
    else:
        with urllib.request.urlopen(urllib.request.Request(item["url"], method="HEAD"), timeout=30) as res:
            size = int(res.headers.get("Content-Length") or 0)
    if dest.is_file() and size and dest.stat().st_size == size:
        return "이미 있음"
    tmp = dest.with_suffix(".part")
    if "member" in item:
        with item["archive"].open(item["member"]) as src, open(tmp, "wb") as fh:
            while chunk := src.read(8 << 20):
                fh.write(chunk)
    else:
        with urllib.request.urlopen(item["url"], timeout=120) as res, open(tmp, "wb") as fh:
            while chunk := res.read(1 << 20):
                fh.write(chunk)
    with open(tmp, "rb") as fh:
        if fh.read(5) != b"%PDF-":
            tmp.unlink()
            raise RuntimeError("PDF가 아닌 응답이 왔어요.")
    tmp.replace(dest)
    return f"받음 {dest.stat().st_size / 1048576:.1f}MB"


def main() -> None:
    ap = argparse.ArgumentParser(description="교사용 지도서 받기")
    ap.add_argument("subjects", nargs="+", help="과목 이름 (config.json 의 subjects 키)")
    ap.add_argument("--list", action="store_true", help="받지 않고 목록만 보기")
    ap.add_argument("--with-plan", action="store_true", help="연간지도계획도 받기")
    ap.add_argument("--root", default=str(GUIDE_ROOT), help="저장 폴더 (기본 D:\\지도서)")
    ap.add_argument("--term", help="학년-학기, 예: 3-2 (기본: config 의 grade_term). 아이스크림은 사이트 설정을 따름")
    args = ap.parse_args()

    cfg = app.load_config()
    report = []
    driver = None
    for subject in args.subjects:
        publisher = cfg.get("subjects", {}).get(subject, {}).get("publisher", "")
        if publisher not in PUBLISHERS:
            print(f"[{subject}] {publisher or '출판사 미설정'}: 아직 지원하지 않는 출판사예요.")
            continue
        start_url, finder = PUBLISHERS[publisher]
        driver = driver or connect(cfg, start_url)
        try:
            term, items = finder(driver, subject, args.with_plan, args.term or cfg.get("grade_term", "3-2"),
                                 cfg.get("google_account_hint", ""))
        except RuntimeError as exc:
            print(f"[{subject}] {publisher}: {exc}")
            continue
        grade_term = "-".join(re.findall(r"\d", term)) or "학기미상"
        folder = pathlib.Path(args.root) / f"{subject} {grade_term}"
        print(f"[{subject}] {publisher} {term} — {len(items)}개 → {folder}")
        for item in items:
            # ZIP 에서 꺼낸 파일은 출판사 원래 이름을 쓴다(1학기 진도표의 파일 이름 규칙과 같음).
            name = safe(item["file"]) if "member" in item else nice_name(subject, term, item)
            if args.list:
                print(f"   {name}  ({item.get('size', 0) / 1048576:.1f}MB, {item['url']})" if "member" in item else f"   {name}  ({item['url']})")
                continue
            folder.mkdir(parents=True, exist_ok=True)
            if "browser" in item:
                existing = [p for p in folder.glob("*.pdf") if item["label"].replace("교사용 ", "") in p.name]
                result = "이미 있음 " + existing[0].name if existing else browser_download(item["browser"][0], item["browser"][1], folder)
            else:
                result = download(item, folder / name)
            print(f"   {name}: {result}")
            report.append({"subject": subject, "file": str(folder / name), "url": item["url"], "result": result})
    if report:
        log = app.DATA / "guide_downloads.json"
        old = app.read_json(log, [])
        app.write_json(log, old + [dict(r, at=time.strftime("%Y-%m-%d %H:%M")) for r in report])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
