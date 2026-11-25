"""skills/*/SKILL.md 의 앞머리(frontmatter)를 읽어 루트 CATALOG.md 를 다시 만든다.

카탈로그는 손으로 고치지 않는다. 스킬 정보는 각 스킬의 SKILL.md 에만 적고, 이 스크립트로 모은다.

    python tools/build_catalog.py           # CATALOG.md 갱신
    python tools/build_catalog.py --check   # 형식 점검만 (SKILL.md·ISSUES.md 누락, 앞머리 항목 누락)

점검은 두 가지로 나뉜다.
  - 문제: 형식 위반. 있으면 종료값 1.
  - 경고: git 이 추적 중인 tmp*·generated_rows*·*.pdf 같은 결과물. 알려 주기만 하고 종료값은 바꾸지 않는다.

SKILL.md 앞머리 형식 (docs/templates/SKILL.md 참고):
    ---
    name: 스킬폴더명
    description: AI가 언제 이 스킬을 쓸지 판단하는 설명
    metadata:
      category: 학교 행정 | 학생 기록·평가 | 수업·교사 도구 | 홈페이지 | 개인·생활 | 공통 유틸
      status: 운영 | 개발 | 보관 | 확인 필요
      version: v1.0.0        # 없으면 생략
      summary: 사람이 읽는 한두 문장 설명 (카탈로그에 표시)
    ---
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
CATALOG = ROOT / "CATALOG.md"

CATEGORY_ORDER = ["학교 행정", "학생 기록·평가", "수업·교사 도구", "홈페이지", "개인·생활", "공통 유틸"]
CATEGORY_ICON = {"학교 행정": "🏫", "학생 기록·평가": "📝", "수업·교사 도구": "📚", "홈페이지": "🌐",
                 "개인·생활": "👤", "공통 유틸": "🛠️"}
STATUS_ICON = {"운영": "✅ 운영", "개발": "🔧 개발", "보관": "📦 보관", "확인 필요": "❔ 확인 필요"}
REQUIRED_META = ("category", "status", "summary")
SKIP_DIRS = {"_shared"}

# 저장소에 올라가 있으면 안 되는 결과물·임시 파일 (이름이 이걸로 시작하거나 끝나는 파일·폴더)
ARTIFACT_PREFIXES = ("tmp", "generated_rows")
ARTIFACT_SUFFIXES = (".pdf",)


def read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def open_issue_count(issues: Path) -> int:
    """ISSUES.md 의 '진행 중' 절에 있는 ### 항목 수."""
    if not issues.is_file():
        return 0
    text = issues.read_text(encoding="utf-8-sig")
    m = re.search(r"^## [^\n]*진행 중[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return len(re.findall(r"^### ", m.group(1), re.M)) if m else 0


def collect() -> tuple[list[dict], list[str]]:
    rows, problems = [], []
    for d in sorted(p for p in SKILLS.iterdir() if p.is_dir() and p.name not in SKIP_DIRS):
        if not any(d.iterdir()):
            continue  # 빈 폴더
        skill_md, issues = d / "SKILL.md", d / "ISSUES.md"
        if not skill_md.is_file():
            problems.append(f"{d.name}: SKILL.md 없음")
            continue
        fm = read_frontmatter(skill_md)
        meta = fm.get("metadata") or {}
        for key in ("name", "description"):
            if not fm.get(key):
                problems.append(f"{d.name}: 앞머리 '{key}' 없음")
        for key in REQUIRED_META:
            if not meta.get(key):
                problems.append(f"{d.name}: metadata.{key} 없음")
        if meta.get("category") and meta["category"] not in CATEGORY_ORDER:
            problems.append(f"{d.name}: 알 수 없는 category '{meta['category']}'")
        if not issues.is_file():
            problems.append(f"{d.name}: ISSUES.md 없음")
        rows.append({
            "dir": d.name,
            "category": meta.get("category", "공통 유틸"),
            "status": meta.get("status", "확인 필요"),
            "version": str(meta.get("version", "")),
            "summary": str(meta.get("summary") or fm.get("description", "")).strip(),
            "has_readme": (d / "README.md").is_file(),
            "open_issues": open_issue_count(issues),
        })
    return rows, problems


def tracked_paths() -> list[str]:
    """git 이 추적 중인 파일 경로(저장소 기준, / 로 구분). git 을 못 쓰면 빈 목록."""
    try:
        result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    return [p for p in result.stdout.decode("utf-8", "replace").split("\0") if p]


def find_artifacts(paths: list[str]) -> list[str]:
    """추적 중인 경로에서 결과물·임시 파일처럼 보이는 것을 묶어 경고 글로 돌려준다.

    폴더 이름이 걸리면 그 폴더 하나로 묶어 파일 수를 센다(파일마다 한 줄씩 늘어놓지 않음).
    """
    groups: dict[str, int] = {}
    for path in paths:
        parts = path.split("/")
        for i, part in enumerate(parts):
            low = part.lower()
            is_last = i == len(parts) - 1
            if low.startswith(ARTIFACT_PREFIXES) or (is_last and low.endswith(ARTIFACT_SUFFIXES)):
                key = "/".join(parts[: i + 1]) + ("" if is_last else "/")
                groups[key] = groups.get(key, 0) + 1
                break
    return [
        f"{key} — 결과물·임시 파일로 보이는데 git 이 추적 중" + (f" (파일 {n}개)" if key.endswith("/") else "")
        for key, n in sorted(groups.items())
    ]


def print_warnings(warnings: list[str]) -> None:
    if not warnings:
        return
    print("\n⚠ 경고 (점검은 통과하지만 확인이 필요해요):\n  " + "\n  ".join(warnings))
    print("  → 필요 없는 결과물이면 교사 확인 뒤 `git rm --cached` 로 추적을 끊고 .gitignore 에 넣으세요. 학생 기록·저작물이 섞였는지도 보세요.")


def cell(text: str) -> str:
    return re.sub(r"\s+", " ", text).replace("|", "\\|")


def render(rows: list[dict]) -> str:
    out = [
        "# 스킬 카탈로그",
        "",
        "> 이 파일은 `python tools/build_catalog.py`로 자동 생성된다. 직접 고치지 말고 각 스킬의 `SKILL.md` 앞머리(`metadata`)를 고친 뒤 다시 실행한다.",
        f"> 생성일: {date.today().isoformat()} · 스킬 {len(rows)}개",
        "",
        "## 빠른 찾기",
        "",
    ]
    counts = {c: sum(r["category"] == c for r in rows) for c in CATEGORY_ORDER}
    out += [f"- [{CATEGORY_ICON[c]} {c}](#{c.replace(' ', '-').replace('·', '')}) — {counts[c]}개" for c in CATEGORY_ORDER if counts[c]]
    for cat in CATEGORY_ORDER:
        items = [r for r in rows if r["category"] == cat]
        if not items:
            continue
        out += ["", f"## {cat}", "", "| 스킬 | 상태 | 버전 | 할 수 있는 일 | 문서 |", "|---|---|---|---|---|"]
        for r in items:
            base = f"skills/{r['dir']}"
            docs = [f"[SKILL]({base}/SKILL.md)",
                    f"[이슈]({base}/ISSUES.md)" + (f" 🔵{r['open_issues']}" if r["open_issues"] else "")]
            if r["has_readme"]:
                docs.append(f"[README]({base}/README.md)")
            out.append(f"| `{r['dir']}` | {STATUS_ICON.get(r['status'], r['status'])} | {cell(r['version']) or '-'} "
                       f"| {cell(r['summary'])} | {' · '.join(docs)} |")
    out += ["", "## 범례", "",
            "| 상태 | 의미 |", "|---|---|",
            "| ✅ 운영 | 실제로 사용 중 |", "| 🔧 개발 | 만드는 중이거나 미완성 |",
            "| 📦 보관 | 더 이상 쓰지 않지만 참고용으로 둠 |", "| ❔ 확인 필요 | 상태를 아직 정하지 않음 |",
            "", "🔵 숫자 = `ISSUES.md`의 '진행 중' 항목 수", ""]
    return "\n".join(out)


def main() -> int:
    # 출력이 다른 프로그램으로 넘어가면 윈도우는 cp949 로 써서 '⚠' 에서 멈춘다(T24 검토 🔴) → utf-8 로
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    rows, problems = collect()
    warnings = find_artifacts(tracked_paths())
    if "--check" in sys.argv:
        print("\n".join(problems) or "문제 없음")
        print_warnings(warnings)
        return 1 if problems else 0
    CATALOG.write_text(render(rows), encoding="utf-8")
    print(f"CATALOG.md 갱신: 스킬 {len(rows)}개")
    if problems:
        print("점검 필요:\n  " + "\n  ".join(problems))
    print_warnings(warnings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
