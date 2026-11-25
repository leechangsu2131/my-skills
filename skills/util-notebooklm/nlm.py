"""긴 PDF 를 'AI 가 찾고, 판단은 프런티어 모델이' 하도록 잇는 도구 (util-notebooklm).

    python nlm.py find <pdf> "찾을 내용" [--model M]     # Gemini CLI 가 관련 쪽·원문만 찾아 [p.N] 으로 답함
    python nlm.py pages <pdf> 4,7-8 [--out 파일]          # 그 쪽만 잘라 새 PDF
    python nlm.py pages <pdf> --from 답.md                # 답에 적힌 [p.N] 쪽만 잘라 냄
    python nlm.py prep <pdf…> [--out 폴더] [--images auto|all|none]   # NotebookLM 소스(md + 그림 PDF)
    python nlm.py split <받은.md> [--pattern 정규식] [--out 폴더]       # 북마클릿 md 를 제목별로 자르기
    python nlm.py nb list | nb add <주제> <주소> [--note 설명] | nb open <주제> [--q 질문]

흐름: ① 찾기(find 또는 NotebookLM) → ② 받아오기(답 md, split) → ③ 쪽 잘라내기(pages)
      → ④ 그 작은 자료만 Claude 등 프런티어 모델에 넘겨 판단.
fitz(PyMuPDF)는 PDF 를 다루는 명령에서만 불러온다 → 다른 스킬이 split_text·노트북 목록만 쓸 때는 기본 파이썬이면 된다.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

SKILL_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(next(p / "_shared" for p in SKILL_DIR.parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir, env_values  # noqa: E402

SKILL = "util-notebooklm"
DATA = data_dir(SKILL)
REGISTRY = DATA / "notebooks.json"
ANSWERS = DATA / "answers"
WORK = DATA / "gemini_work"
DEFAULT_MODEL = "gemini-3.8-flash"   # 무료 키로 되는 모델 (pro 는 무료 한도 0, 2026-11-22 확인)
FALLBACK_MODELS = ["gemini-3.7-flash", "gemini-flash-latest", "gemini-3.5-flash-lite"]  # 붐빌 때(503) 차례로
KEY_NAMES = ("UTIL_NOTEBOOKLM__GEMINI_API_KEY", "GEMINI_API_KEY", "GEMINI_API_KEY_FROM_VAULT_NOTE")

CTL = re.compile(r"[\x00-\x08\x0b-\x1f​-‍﻿]")
DOUBLED = re.compile(r"([•◼○●▒■□◆◇▶▷※])(?:\s*\1)+")
HANGUL = re.compile(r"[가-힣]")
LOW_TEXT = 40          # 한글이 이보다 적은 쪽은 '그림 쪽'
WORD_LIMIT = 450_000   # NotebookLM 소스당 50만 단어
GRAY_DPI, GRAY_QUALITY = 90, 50
PAGE_REF = re.compile(r"\[p\.?\s*(\d+)(?:\s*[-~∼]\s*(\d+))?\]|PDF\s*(?:파일\s*)?(\d+)\s*쪽")

FIND_PROMPT = """@{file} 이 PDF 에서 아래 내용과 관련된 부분을 찾아 주세요.

찾을 내용: {query}

규칙
- 판단·요약·추천은 하지 말고, 관련된 원문 문장을 그대로 인용만 합니다.
- 각 인용 앞에 PDF 파일 쪽 번호를 [p.N] 형식으로 붙입니다(인쇄된 쪽 번호가 아니라 PDF 파일의 몇 번째 쪽인지). 여러 쪽이면 [p.N-M].
- 관련 부분이 없으면 "없음"이라고만 답합니다.
- 마지막 줄에 "쪽: N, N-M" 처럼 관련 쪽을 모두 모아 적습니다."""

ASK_PROMPT = """소스에서 아래 내용과 관련된 부분만 찾아 주세요.
찾을 내용: {query}
판단·요약은 하지 말고 원문을 그대로 인용하고, 인용마다 출처(소스 이름과 쪽, 〔p.N〕 표시가 있으면 그 번호)를 붙여 주세요."""


# ──────────────────────────── 글자 뽑기·소스 만들기 (다른 스킬도 가져다 씀) ────────────────────────────

def fitz():
    import fitz as _fitz  # PyMuPDF
    return _fitz


def page_text(page) -> str:
    lines = []
    for line in CTL.sub(" ", page.get_text()).splitlines():
        line = DOUBLED.sub(r"\1", " ".join(line.split()))
        if line:
            lines.append("\\" + line if line.startswith("#") else line)  # 원문이 md 제목으로 읽히지 않게
    return "\n".join(lines)


def is_low_text(text: str) -> bool:
    return len(HANGUL.findall(text)) < LOW_TEXT and len(re.findall(r"[A-Za-z]{2,}", text)) < LOW_TEXT


def gray_page(out, page, label: str) -> None:
    f = fitz()
    pix = page.get_pixmap(dpi=GRAY_DPI, colorspace=f.csGRAY)
    new = out.new_page(width=page.rect.width, height=page.rect.height)
    new.insert_image(new.rect, stream=pix.tobytes("jpeg", jpg_quality=GRAY_QUALITY))
    try:  # 그림 쪽이 어디인지 글자로도 남김
        new.insert_text((12, 14), label, fontname="korea", fontsize=9)
    except Exception:
        pass


def write_source(md_path: pathlib.Path, img_path: pathlib.Path, header: list[str],
                 sections: list[dict], images: str = "auto") -> dict:
    """구간 목록을 NotebookLM 소스(md + 그림 PDF)로 쓴다.
    sections: [{"heading": "## …", "pdf": 경로, "pages": [(0부터 쪽, 표시 쪽 번호)], "note": ""}]
    images: auto(글자 적은 쪽만) | all(모든 쪽) | none"""
    f = fitz()
    md_path.parent.mkdir(parents=True, exist_ok=True)
    out = list(header)
    gray = f.open()
    low_pages, docs = 0, {}
    try:
        for s in sections:
            out += ["", s["heading"], ""]
            if s.get("note"):
                out.append(s["note"])
                continue
            doc = docs.setdefault(s["pdf"], f.open(s["pdf"]))
            short = s["heading"].lstrip("# ").split(" (")[0]
            for idx, label in s["pages"]:
                page = doc[idx]
                text = page_text(page)
                low = is_low_text(text)
                if images == "all" or (images == "auto" and low):
                    gray_page(gray, page, f"{short} p.{label}")
                if low:
                    low_pages += 1
                    hint = f" — 그림은 {img_path.name} 참고" if images != "none" else ""
                    out.append(f"〔p.{label}〕 (글자가 거의 없는 쪽{hint})")
                    if text:
                        out.append(text)
                else:
                    out += [f"〔p.{label}〕", text]
                out.append("")
        if gray.page_count:
            gray.save(img_path, garbage=3, deflate=True)
        elif img_path.exists():
            img_path.unlink()
        gray_pages = gray.page_count
    finally:
        gray.close()
        for d in docs.values():
            d.close()
    body = "\n".join(out).rstrip() + "\n"
    md_path.write_text(body, encoding="utf-8")
    words = len(body.split())
    return {"words": words, "low_pages": low_pages, "gray_pages": gray_pages,
            "too_big": words > WORD_LIMIT, "missing": sum(1 for s in sections if s.get("note"))}


def whole_section(heading: str, pdf: str, start_label: int | None = None) -> dict:
    with fitz().open(pdf) as doc:
        n = doc.page_count
    return {"heading": heading, "pdf": pdf, "note": "",
            "pages": [(i, (start_label + i) if start_label else i + 1) for i in range(n)]}


# ──────────────────────────── 받은 md 자르기 (기본 파이썬) ────────────────────────────

HEADING = re.compile(r"^\s*(#{1,6}\s|\*\*)")


def split_text(text: str, pattern: str | re.Pattern | None = None) -> list[tuple[re.Match | None, str, str]]:
    """제목 줄(# … / **…**)에서 자른다. pattern 이 있으면 그 표시가 든 제목에서만.
    반환: [(표시 match 또는 None, 제목 줄, 본문)] — 첫 제목 앞 글은 버린다."""
    rx = re.compile(pattern) if isinstance(pattern, str) else pattern
    parts, cur, buf = [], None, []
    for line in text.splitlines():
        m = None
        if HEADING.match(line):
            m = rx.search(line) if rx else re.match(r".*", line)
        if m:
            if cur:
                parts.append((cur[0], cur[1], "\n".join(buf).strip()))
            cur, buf = (m if rx else None, line), [line]
        elif cur:
            buf.append(line)
    if cur:
        parts.append((cur[0], cur[1], "\n".join(buf).strip()))
    return parts


def page_refs(text: str) -> list[int]:
    """답 글에서 [p.N] / [p.N-M] / 'PDF 파일 N쪽' 을 모아 쪽 번호 목록(1부터)."""
    pages: set[int] = set()
    for m in PAGE_REF.finditer(text):
        a = int(m.group(1) or m.group(3))
        b = int(m.group(2) or a)
        pages.update(range(a, max(a, b) + 1))
    return sorted(p for p in pages if p >= 1)


def parse_pages(spec: str) -> list[int]:
    pages: set[int] = set()
    for part in re.split(r"[,\s]+", spec.strip()):
        if not part:
            continue
        a, _, b = part.partition("-")
        pages.update(range(int(a), int(b or a) + 1))
    return sorted(pages)


# ──────────────────────────── 노트북 목록 (기본 파이썬) ────────────────────────────

def load_registry() -> dict:
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def notebook_url(topic: str) -> str:
    return str(load_registry().get(topic, {}).get("url", ""))


def save_registry(reg: dict) -> None:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")


def copy_to_clipboard(text: str) -> None:
    subprocess.run(["clip"], input=text.encode("utf-16-le"), check=False)


# ──────────────────────────── Gemini CLI 찾기 ────────────────────────────

def gemini_command() -> list[str]:
    """윈도우의 gemini.cmd 는 cmd.exe 를 거치며 여러 줄 인자를 첫 줄에서 자르고 & % 따옴표도 깨뜨린다
    → node 로 Gemini CLI 본체(gemini.js)를 직접 실행한다."""
    shim = shutil.which("gemini.cmd") or shutil.which("gemini")
    node = shutil.which("node")
    if shim and node:
        js = pathlib.Path(shim).parent / "node_modules" / "@google" / "gemini-cli" / "bundle" / "gemini.js"
        if js.is_file():
            return [node, str(js)]
    if shim and not shim.lower().endswith((".cmd", ".bat")):
        return [shim]
    raise RuntimeError("gemini CLI 를 찾지 못했어요 (npm i -g @google/gemini-cli).")


def gemini_find(pdf: pathlib.Path, query: str, model: str = DEFAULT_MODEL, timeout: int = 300,
                model_timeout: int | None = None) -> tuple[str, str]:
    """PDF 에서 관련 원문과 [p.N] 만 찾게 한다(판단·요약 없음).

    반환값은 (답변, 실제로 답한 모델)이다.
    """
    return gemini_ask(pdf, FIND_PROMPT.replace("{query}", query), model, timeout,
                      model_timeout=model_timeout)


def gemini_ask(pdf: pathlib.Path, prompt: str, model: str = DEFAULT_MODEL, timeout: int = 300,
               work: pathlib.Path | None = None, model_timeout: int | None = None) -> tuple[str, str]:
    """PDF 를 작업 폴더로 복사해 Gemini CLI 에 묻는다. prompt 안의 {file} 은 PDF 이름(@ 첨부)으로 바뀐다.
    - 키가 중앙 .env 에 있으면 작업 폴더에만 API 키 방식을 설정(전역 Gemini 설정은 건드리지 않음). 없으면 그 PC 의 구글 로그인 사용.
    - 이 PC 의 Gemini 확장은 끈다(-e none). work 를 다르게 주면 여러 개를 동시에 돌릴 수 있다."""
    cmd = gemini_command()
    work = work or WORK
    work.mkdir(parents=True, exist_ok=True)
    local = work / ("doc" + (pdf.suffix or ".pdf"))   # 한글·공백 경로 문제를 피하려고 고정 이름 (PDF 또는 md/txt)
    shutil.copyfile(pdf, local)
    env = dict(os.environ)
    values = env_values()
    key = next((values[k] for k in KEY_NAMES if values.get(k)), "")
    settings = work / ".gemini" / "settings.json"
    settings.parent.mkdir(exist_ok=True)
    if key:
        env["GEMINI_API_KEY"] = key
        settings.write_text(json.dumps({"security": {"auth": {"selectedType": "gemini-api-key"}}}), encoding="utf-8")
    elif settings.exists():
        settings.unlink()
    prompt = prompt.replace("{file}", local.name)
    # 기본값은 기존 동작(60~120초)을 유지한다. 짧은 출력은 호출 쪽에서 30~45초로 줄일 수 있다.
    chain = [model] + [m for m in FALLBACK_MODELS if m != model]
    per_try = max(1, int(model_timeout)) if model_timeout is not None else max(60, min(timeout, 120))
    errors = []
    for m in chain:
        try:
            res = subprocess.run([*cmd, "-e", "none", "-m", m, "-p", prompt], cwd=work, env=env,
                                 stdin=subprocess.DEVNULL, capture_output=True, timeout=per_try,
                                 encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            errors.append(f"{m}: {per_try}초 넘음(붐빔)")
            continue
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip(), m
        err = (res.stderr or "").strip().splitlines()
        hint = next((l for l in err if "quota" in l.lower() or "Error" in l), err[-1] if err else "")
        errors.append(f"{m}: 코드 {res.returncode} {hint[:150]}")
    raise RuntimeError("Gemini 실패 — " + " / ".join(errors))


# ──────────────────────────── 명령 ────────────────────────────

def cmd_find(a) -> None:
    pdf = pathlib.Path(a.pdf)
    t0 = time.time()
    answer, used_model = gemini_find(pdf, a.query, a.model)
    ANSWERS.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out) if a.out else ANSWERS / f"{time.strftime('%Y%m%d_%H%M%S')}_{pdf.stem[:40]}.md"
    out.write_text(f"<!-- 원본: {pdf} | 찾을 내용: {a.query} | {a.model} -->\n{answer}\n", encoding="utf-8")
    print(answer)
    print(f"\n[{time.time() - t0:.0f}초] 저장: {out} · 사용 모델: {used_model}\n관련 쪽: {page_refs(answer) or '없음'}"
          f"  → 잘라내기: python nlm.py pages \"{pdf}\" --from \"{out}\"")


def cmd_pages(a) -> None:
    f = fitz()
    pdf = pathlib.Path(a.pdf)
    pages = page_refs(pathlib.Path(a.from_md).read_text(encoding="utf-8-sig")) if a.from_md else parse_pages(a.spec or "")
    with f.open(pdf) as doc:
        pages = [p for p in pages if 1 <= p <= doc.page_count]
        if not pages:
            raise SystemExit("잘라낼 쪽이 없어요.")
        part = f.open()
        for p in pages:
            part.insert_pdf(doc, from_page=p - 1, to_page=p - 1)
        out = pathlib.Path(a.out) if a.out else DATA / "pages" / f"{pdf.stem[:50]}_p{compact(pages)}.pdf"
        out.parent.mkdir(parents=True, exist_ok=True)
        part.save(out, garbage=3, deflate=True)
        part.close()
    print(f"{len(pages)}쪽 → {out}")


def compact(pages: list[int]) -> str:
    runs, start = [], pages[0]
    for prev, cur in zip(pages, pages[1:] + [None]):
        if cur != prev + 1:
            runs.append(f"{start}-{prev}" if prev != start else str(start))
            start = cur
    return ",".join(runs)[:60]


def cmd_prep(a) -> None:
    out_dir = pathlib.Path(a.out) if a.out else DATA / "sources"
    for p in a.pdfs:
        pdf = pathlib.Path(p)
        title = a.title or pdf.stem
        md = out_dir / f"{pdf.stem}.md"
        header = [f"# {title}", "", f"원본: {pdf.name} · 만든 날: {time.strftime('%Y-%m-%d')}",
                  "〔p.N〕은 PDF 파일 쪽 번호입니다."]
        r = write_source(md, out_dir / f"{pdf.stem}_그림.pdf", header, [whole_section(f"## {title}", str(pdf))], a.images)
        print(f"{md.name}: {r['words']:,}단어, 그림 쪽 {r['low_pages']}" + (" ⚠ 50만 단어 한도 가까움" if r["too_big"] else ""))


def cmd_split(a) -> None:
    src = pathlib.Path(a.md)
    out_dir = pathlib.Path(a.out) if a.out else DATA / "notes" / src.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = split_text(src.read_text(encoding="utf-8-sig"), a.pattern)
    for i, (_, head, body) in enumerate(parts, 1):
        name = re.sub(r'[\\/:*?"<>|\s#*]+', "_", head).strip("_")[:60] or "part"
        (out_dir / f"{i:02d}_{name}.md").write_text(body + "\n", encoding="utf-8")
    print(f"{len(parts)}개 → {out_dir}")


def cmd_nb(a) -> None:
    reg = load_registry()
    if a.action == "list":
        for k, v in reg.items():
            print(f"{k}: {v.get('url')}  {v.get('note', '')}")
        print(f"({len(reg)}개, {REGISTRY})")
    elif a.action == "add":
        if not (a.topic and a.url and a.url.startswith("https://notebooklm.google.com/")):
            raise SystemExit("주제와 https://notebooklm.google.com/… 주소를 주세요.")
        reg[a.topic] = {"url": a.url, "note": a.note or "", "updated": time.strftime("%Y-%m-%d")}
        save_registry(reg)
        print(f"등록: {a.topic}")
    elif a.action == "open":
        url = reg.get(a.topic or "", {}).get("url")
        if not url:
            raise SystemExit(f"'{a.topic}' 노트북이 목록에 없어요 (nb add).")
        if a.q:
            copy_to_clipboard(ASK_PROMPT.format(query=a.q))
            print("찾기 질문을 복사했어요 → 노트북 대화창에 Ctrl+V")
        os.startfile(url)  # noqa: S606  (목록에 등록된 notebooklm 주소만)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("find"); p.add_argument("pdf"); p.add_argument("query")
    p.add_argument("--model", default=DEFAULT_MODEL); p.add_argument("--out"); p.set_defaults(fn=cmd_find)
    p = sub.add_parser("pages"); p.add_argument("pdf"); p.add_argument("spec", nargs="?")
    p.add_argument("--from", dest="from_md"); p.add_argument("--out"); p.set_defaults(fn=cmd_pages)
    p = sub.add_parser("prep"); p.add_argument("pdfs", nargs="+"); p.add_argument("--out"); p.add_argument("--title")
    p.add_argument("--images", choices=["auto", "all", "none"], default="auto"); p.set_defaults(fn=cmd_prep)
    p = sub.add_parser("split"); p.add_argument("md"); p.add_argument("--pattern"); p.add_argument("--out"); p.set_defaults(fn=cmd_split)
    p = sub.add_parser("nb"); p.add_argument("action", choices=["list", "add", "open"]); p.add_argument("topic", nargs="?")
    p.add_argument("url", nargs="?"); p.add_argument("--note"); p.add_argument("--q"); p.set_defaults(fn=cmd_nb)
    a = ap.parse_args()
    try:
        a.fn(a)
    except RuntimeError as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
