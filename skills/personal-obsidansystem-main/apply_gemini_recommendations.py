"""Apply Gemini recommendation tables to an Obsidian vault.

Expected columns:
bundle_file, source_path, 현재 제목, 제안 제목, domain, engine, topic, type,
연결 후보, 처리 제안, 확신도, 이유
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from pkm_core import (
    backup_file,
    build_note_folder_path_value,
    format_yaml_value,
    merge_aliases,
    read_frontmatter,
    read_text_file,
    sanitize_filename,
    sync_path_prop_for_file,
    update_links_for_note_change,
    write_frontmatter,
    DEFAULT_BACKUP_ROOT,
)


HEADER_SOURCE = "source_path"
HEADER_CURRENT_TITLE = "현재 제목"
HEADER_PROPOSED_TITLE = "제안 제목"
HEADER_DOMAIN = "domain"
HEADER_ENGINE = "engine"
HEADER_TOPIC = "topic"
HEADER_TYPE = "type"
HEADER_ACTION = "처리 제안"
HEADER_CONFIDENCE = "확신도"
HEADER_REASON = "이유"
HEADER_BUNDLE = "bundle_file"

DEST_ACTIONS = {"10_NOTE 승격", "20_THINKING 승격", "30_SYSTEM 승격", "Inbox 보류"}
ABSORB_ACTION = "기존 노트에 흡수"
MANUAL_ACTIONS: set[str] = set()  # 흡수 기능이 자동화됨
VALID_ACTIONS = {
    "유지",
    "제목 수정 후 유지",
    "10_NOTE 승격",
    "20_THINKING 승격",
    "30_SYSTEM 승격",
    "Inbox 보류",
    ABSORB_ACTION,
    "기존 노트에 흡수",
}
CONFIDENCE_ORDER = {"하": 0, "중": 1, "상": 2, "낮음": 0, "중간": 1, "높음": 2}
FIELD_ORDER = [
    HEADER_BUNDLE,
    HEADER_SOURCE,
    HEADER_CURRENT_TITLE,
    HEADER_PROPOSED_TITLE,
    HEADER_DOMAIN,
    HEADER_ENGINE,
    HEADER_TOPIC,
    HEADER_TYPE,
    "연결 후보",
    HEADER_ACTION,
    HEADER_CONFIDENCE,
    HEADER_REASON,
]
HEADER_ALIASES = {
    "current_title": HEADER_CURRENT_TITLE,
    "proposed_title": HEADER_PROPOSED_TITLE,
    "links": "연결 후보",
    "action": HEADER_ACTION,
    "confidence": HEADER_CONFIDENCE,
    "reason": HEADER_REASON,
    "note_type": HEADER_TYPE,
}


@dataclass
class Recommendation:
    bundle_file: str
    source_path: str
    current_title: str
    proposed_title: str
    domain: str
    engine: str
    topic: str
    note_type: str
    links: str
    action: str
    confidence: str
    reason: str
    fingerprint: str


@dataclass
class ApplyResult:
    source_path: str
    status: str
    detail: str
    destination: str = ""
    fingerprint: str = ""


def normalize_cell(value: str) -> str:
    return str(value or "").strip().strip("\ufeff")


def normalize_path_for_match(value: str) -> str:
    text = normalize_cell(value).replace("\\", "/").lower()
    text = re.sub(r"\([^)]*\)", "", text)
    text = text.replace("...", "")
    text = re.sub(r"[^0-9a-z가-힣/._-]+", "", text)
    text = text.replace("//", "/")
    return text.strip("/")


def detect_delimiter(header_line: str) -> str:
    if "\t" in header_line:
        return "\t"
    if "|" in header_line and "," not in header_line:
        return "|"
    return ","


def looks_like_header(line: str) -> bool:
    normalized = line.strip()
    return "bundle_file" in normalized and "source_path" in normalized


def parse_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if looks_like_header(line):
            if current:
                blocks.append(current)
            current = [line]
            continue
        if current:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def parse_row_dicts(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for block in parse_blocks(text):
        header_line = block[0]
        delimiter = detect_delimiter(header_line)
        if delimiter == "|":
            reader = csv.reader(
                [line.strip().strip("|") for line in block],
                delimiter="|",
            )
        else:
            reader = csv.reader(block, delimiter=delimiter)
        parsed = list(reader)
        if not parsed:
            continue
        headers = [HEADER_ALIASES.get(normalize_cell(cell), normalize_cell(cell)) for cell in parsed[0]]
        for raw_row in parsed[1:]:
            cells = list(raw_row) + [""] * max(0, len(headers) - len(raw_row))
            row = {headers[i]: normalize_cell(cells[i]) for i in range(len(headers))}
            if row.get(HEADER_SOURCE, "") in {"", HEADER_SOURCE}:
                continue
            rows.append(row)
    return rows


def build_fingerprint(row: dict[str, str]) -> str:
    parts = [
        row.get(HEADER_SOURCE, ""),
        row.get(HEADER_PROPOSED_TITLE, ""),
        row.get(HEADER_DOMAIN, ""),
        row.get(HEADER_ENGINE, ""),
        row.get(HEADER_TOPIC, ""),
        row.get(HEADER_TYPE, ""),
        row.get(HEADER_ACTION, ""),
        row.get(HEADER_CONFIDENCE, ""),
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


def resolve_source_note_path(vault_path: Path, source_path: str) -> Path | None:
    exact = (vault_path / source_path).resolve()
    if exact.exists():
        return exact

    normalized_source = normalize_path_for_match(source_path)
    filename = Path(source_path).name
    if not filename:
        return None

    candidates = list(vault_path.rglob(filename))
    if not candidates:
        source_stem = normalize_path_for_match(Path(source_path).stem)
        candidates = []
        for note_path in vault_path.rglob("*.md"):
            note_rel = note_path.relative_to(vault_path).as_posix()
            normalized_rel = normalize_path_for_match(note_rel)
            normalized_stem = normalize_path_for_match(note_path.stem)
            if normalized_source in normalized_rel or normalized_stem == source_stem:
                candidates.append(note_path)
        if not candidates:
            return None

    exact_matches: list[Path] = []
    prefix_matches: list[Path] = []
    contains_matches: list[Path] = []

    for candidate in candidates:
        rel = candidate.relative_to(vault_path).as_posix()
        normalized_rel = normalize_path_for_match(rel)
        if normalized_rel == normalized_source:
            exact_matches.append(candidate)
        elif normalized_rel.endswith(normalized_source) or normalized_source.endswith(normalized_rel):
            prefix_matches.append(candidate)
        elif normalized_source in normalized_rel:
            contains_matches.append(candidate)

    for group in (exact_matches, prefix_matches, contains_matches):
        if len(group) == 1:
            return group[0].resolve()

    return None


def dedupe_recommendations(rows: Iterable[dict[str, str]]) -> list[Recommendation]:
    deduped: dict[str, Recommendation] = {}
    for row in rows:
        source_path = normalize_cell(row.get(HEADER_SOURCE, ""))
        if not source_path:
            continue
        rec = Recommendation(
            bundle_file=normalize_cell(row.get(HEADER_BUNDLE, "")),
            source_path=source_path,
            current_title=normalize_cell(row.get(HEADER_CURRENT_TITLE, "")),
            proposed_title=normalize_cell(row.get(HEADER_PROPOSED_TITLE, "")),
            domain=normalize_cell(row.get(HEADER_DOMAIN, "")),
            engine=normalize_cell(row.get(HEADER_ENGINE, "")),
            topic=normalize_cell(row.get(HEADER_TOPIC, "")),
            note_type=normalize_cell(row.get(HEADER_TYPE, "")),
            links=normalize_cell(row.get("연결 후보", "")),
            action=normalize_cell(row.get(HEADER_ACTION, "")),
            confidence=normalize_cell(row.get(HEADER_CONFIDENCE, "")),
            reason=normalize_cell(row.get(HEADER_REASON, "")),
            fingerprint=build_fingerprint(row),
        )
        deduped[source_path] = rec
    return list(deduped.values())


def canonicalize_recommendations(
    vault_path: Path,
    recommendations: Iterable[Recommendation],
) -> list[Recommendation]:
    deduped: dict[str, Recommendation] = {}
    for rec in recommendations:
        resolved = resolve_source_note_path(vault_path, rec.source_path)
        if resolved:
            canonical = resolved.relative_to(vault_path).as_posix()
            rec.source_path = canonical
            key = canonical.lower()
        else:
            key = normalize_path_for_match(rec.source_path)
        deduped[key] = rec
    return list(deduped.values())


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {"entries": {}}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {"entries": {}}


def save_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def confidence_allows(confidence: str, minimum: str) -> bool:
    return CONFIDENCE_ORDER.get(confidence, -1) >= CONFIDENCE_ORDER.get(minimum, -1)


def infer_engine(rec: Recommendation) -> str:
    if rec.action == "20_THINKING 승격":
        return "pattern"
    if rec.action == "30_SYSTEM 승격":
        return "principle"
    if rec.action == "10_NOTE 승격" and not rec.engine:
        return "concept"
    return rec.engine


def normalize_topic(raw: str):
    text = normalize_cell(raw)
    if not text:
        return None
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return None
        parts = [part.strip().strip("'\"") for part in inner.split(",") if part.strip()]
        if len(parts) == 1:
            return parts[0]
        return parts
    if "," in text:
        parts = [part.strip().strip("'\"") for part in text.split(",") if part.strip()]
        if len(parts) == 1:
            return parts[0]
        if parts:
            return parts
    return text


def infer_destination_dir(vault_path: Path, note_path: Path, rec: Recommendation) -> Path:
    action = rec.action
    if action == "Inbox 보류":
        return (vault_path / "Inbox").resolve()
    if action == "10_NOTE 승격":
        return (vault_path / "10_NOTE" / rec.domain).resolve()
    if action == "20_THINKING 승격":
        return (vault_path / "20_THINKING" / rec.domain).resolve()
    if action == "30_SYSTEM 승격":
        return (vault_path / "30_SYSTEM" / rec.domain).resolve()
    return note_path.parent.resolve()


def maybe_update_heading(body: str, current_title: str, new_title: str, old_stem: str) -> str:
    lines = body.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading in {current_title, old_stem}:
                prefix = line[: line.index("#")]
                level = stripped[: len(stripped) - len(stripped.lstrip("#"))]
                lines[index] = f"{prefix}{level} {new_title}"
            break
        break
    return "\n".join(lines) + ("\n" if body.endswith("\n") else "")


def inject_links_to_body(body: str, raw_links: str) -> str:
    if not raw_links.strip():
        return body
        
    candidates = []
    # NotebookLM may output comma or newline separated links
    for part in raw_links.replace("\n", ",").split(","):
        clean = part.strip()
        if not clean:
            continue
        # Remove paths if any (e.g. 10_NOTE/foo.md)
        clean = Path(clean).name
        # Remove .md
        if clean.lower().endswith('.md'):
            clean = clean[:-3]
        # Remove brackets if any
        clean = clean.lstrip('[').rstrip(']')
        if clean:
            candidates.append(clean)
            
    if not candidates:
        return body
        
    if "## 🔗 연결 노트" in body:
        return body

    links_text = "\n\n---\n## 🔗 연결 노트\n" + "\n".join(f"- [[{c}]]" for c in set(candidates))
    return body.rstrip() + links_text + "\n"



def write_note(path: Path, props: dict, blocks: list, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(write_frontmatter(props, blocks, body), encoding="utf-8")


def absorb_into_target(
    vault_path: Path,
    source_path: Path,
    raw_target: str,
    source_title: str,
    dry_run: bool,
) -> ApplyResult:
    """원본 노트 내용을 대상 노트 하단에 흡수하고 원본을 삭제한다."""
    # 대상 노트 탐색: 연결 후보 열 값(파일명 또는 경로)
    target_name = Path(raw_target.strip()).name
    if target_name.lower().endswith(".md"):
        target_stem = target_name[:-3]
    else:
        target_stem = target_name

    # Vault 전체에서 파일명으로 탐색
    candidates = list(vault_path.rglob(f"{target_stem}.md"))
    if not candidates:
        return ApplyResult(
            source_path.name, "missing",
            f"흡수 대상 노트를 찾을 수 없음: {target_name}"
        )
    target_path = candidates[0].resolve()

    if dry_run:
        return ApplyResult(
            str(source_path.relative_to(vault_path)),
            "planned",
            f"흡수 → {target_path.relative_to(vault_path).as_posix()}",
            destination=target_path.relative_to(vault_path).as_posix(),
        )

    # 원본 내용 읽기
    src_text = read_text_file(source_path)
    _, _, src_body = read_frontmatter(src_text)
    src_body = src_body.strip()

    # 대상 파일에 흡수 섹션 추가
    backup_file(target_path, vault_path)
    backup_file(source_path, vault_path)

    target_text = read_text_file(target_path)
    absorb_block = (
        f"\n\n---\n## 📎 흡수: {source_title or source_path.stem}\n\n"
        + src_body
        + "\n"
    )
    target_path.write_text(target_text.rstrip() + absorb_block, encoding="utf-8")

    # 원본 삭제 후 링크를 대상 노트로 리다이렉트
    source_path.unlink()
    link_result = update_links_for_note_change(vault_path, source_path, target_path)

    detail = (
        f"흡수 → {target_path.relative_to(vault_path).as_posix()}; "
        f"links updated: {link_result['updated_files']} files "
        f"(wikilinks {link_result['wikilinks_updated']}, markdown {link_result['markdown_links_updated']})"
    )
    return ApplyResult(
        str(source_path.relative_to(vault_path)),
        "absorbed",
        detail,
        destination=target_path.relative_to(vault_path).as_posix(),
    )



def apply_recommendation(vault_path: Path, rec: Recommendation, dry_run: bool) -> ApplyResult:
    """Link-safe override that also preserves old titles as aliases."""
    note_path = resolve_source_note_path(vault_path, rec.source_path)
    if not note_path or not note_path.exists():
        return ApplyResult(rec.source_path, "missing", "source file not found", fingerprint=rec.fingerprint)

    if rec.action == ABSORB_ACTION:
        if not rec.links.strip():
            return ApplyResult(rec.source_path, "manual", "흡수 대상 노트(연결 후보)가 비어있음 — 수동 처리 필요", fingerprint=rec.fingerprint)
        return absorb_into_target(
            vault_path=vault_path,
            source_path=note_path,
            raw_target=rec.links,
            source_title=rec.current_title or note_path.stem,
            dry_run=dry_run,
        )

    if rec.action in MANUAL_ACTIONS:
        return ApplyResult(rec.source_path, "manual", "manual merge required", fingerprint=rec.fingerprint)

    if rec.action and rec.action not in VALID_ACTIONS:
        return ApplyResult(rec.source_path, "invalid", f"unsupported action: {rec.action}", fingerprint=rec.fingerprint)

    if not rec.domain and rec.action in DEST_ACTIONS - {"Inbox 보류"}:
        return ApplyResult(rec.source_path, "invalid", "domain is required for destination move", fingerprint=rec.fingerprint)

    original_note_path = note_path.resolve()
    text = read_text_file(note_path)
    props, blocks, body = read_frontmatter(text)
    new_title = rec.current_title or note_path.stem
    safe_name = sanitize_filename(new_title) + note_path.suffix
    engine = infer_engine(rec)
    topic_value = normalize_topic(rec.topic)

    if rec.domain:
        props["domain"] = rec.domain
    if engine:
        props["engine"] = engine
    if topic_value is not None:
        props["topic"] = topic_value
    if rec.note_type:
        props["type"] = rec.note_type

    alias_candidates = []
    if new_title and new_title != note_path.stem:
        alias_candidates.append(note_path.stem)
    if rec.current_title and rec.current_title != new_title:
        alias_candidates.append(rec.current_title)
    merge_aliases(props, alias_candidates)

    destination_dir = infer_destination_dir(vault_path.resolve(), note_path, rec)
    destination_path = (destination_dir / safe_name).resolve()

    if destination_path != note_path.resolve() and destination_path.exists():
        return ApplyResult(
            rec.source_path,
            "conflict",
            f"destination already exists: {destination_path.relative_to(vault_path).as_posix()}",
            destination=destination_path.relative_to(vault_path).as_posix(),
            fingerprint=rec.fingerprint,
        )

    # 제목 자동 변경 방지 (사용자 요청: 제목은 직접 수정하겠음)
    # if rec.proposed_title:
    #     body = maybe_update_heading(body, rec.current_title, rec.proposed_title, note_path.stem)

    if rec.links:
        body = inject_links_to_body(body, rec.links)

    if dry_run:
        return ApplyResult(
            rec.source_path,
            "planned",
            rec.action or "유지",
            destination=destination_path.relative_to(vault_path).as_posix(),
            fingerprint=rec.fingerprint,
        )

    backup_file(note_path, vault_path)
    
    cwd = str(vault_path)
    vault_name = vault_path.name  # Obsidian CLI의 vault 이름 = 볼트 폴더 이름
    detail = rec.action or "유지"
    
    # 1. 이동 (이름 변경 포함)
    if destination_path.resolve() != original_note_path:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        rel_src = original_note_path.relative_to(vault_path).as_posix()
        rel_dst = destination_path.relative_to(vault_path).as_posix()
        try:
            subprocess.run(
                f'obsidian vault={vault_name} move path="{rel_src}" to="{rel_dst}"',
                shell=True, check=True, cwd=cwd
            )
            detail += "; moved via cli"
        except subprocess.CalledProcessError as e:
            detail += f"; move failed: {e}"
            # 이동에 실패하더라도 파일은 기존 경로에 있으므로 destination_path를 원상복구
            destination_path = original_note_path
            rel_dst = rel_src

    rel_dst = destination_path.relative_to(vault_path).as_posix()

    # 2. 프로퍼티 업데이트 (CLI 사용)
    if rec.domain:
        subprocess.run(f'obsidian vault={vault_name} property:set path="{rel_dst}" name=domain value="{rec.domain}"', shell=True, cwd=cwd)
    if engine:
        subprocess.run(f'obsidian vault={vault_name} property:set path="{rel_dst}" name=engine value="{engine}"', shell=True, cwd=cwd)
    if topic_value is not None:
        topic_str = str(topic_value).replace("'", '"')
        subprocess.run(f'obsidian vault={vault_name} property:set path="{rel_dst}" name=topic value=\'{topic_str}\'', shell=True, cwd=cwd)
    if rec.note_type:
        subprocess.run(f'obsidian vault={vault_name} property:set path="{rel_dst}" name=type value="{rec.note_type}"', shell=True, cwd=cwd)

    # 3. 본문에 링크 추가
    if rec.links:
        # 연결 후보 추가는 CLI의 append를 이용
        links_text = "\\n\\n#### 🔗 연결 노트\\n" + "\\n".join(f"* [[{c.strip()}]]" for c in rec.links.replace("\\n", ",").split(",") if c.strip())
        # append CLI 명령 실행
        subprocess.run(f'obsidian vault={vault_name} append path="{rel_dst}" content="{links_text}"', shell=True, cwd=cwd)

    return ApplyResult(
        rec.source_path,
        "applied",
        detail,
        destination=destination_path.relative_to(vault_path).as_posix(),
        fingerprint=rec.fingerprint,
    )


def write_report(report_path: Path, results: list[ApplyResult], dry_run: bool) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Gemini Recommendation Apply Report ({'dry-run' if dry_run else 'apply'})",
        "",
        f"- generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "| source_path | status | destination | detail |",
        "|---|---|---|---|",
    ]
    for result in results:
        lines.append(
            f"| `{result.source_path}` | {result.status} | `{result.destination}` | {result.detail} |"
        )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply Gemini CSV/TSV recommendation tables to an Obsidian vault.",
    )
    parser.add_argument("vault", help="Obsidian vault path")
    parser.add_argument("recommendations", help="CSV/TSV text file exported or pasted from Gemini")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without touching files")
    parser.add_argument(
        "--min-confidence",
        choices=["상", "중", "하"],
        default="중",
        help="Minimum confidence to apply automatically. Default: 중",
    )
    parser.add_argument(
        "--include-manual",
        action="store_true",
        help="Include rows like '기존 노트에 흡수' in the report only; they are still not auto-merged.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    vault_path = Path(args.vault).resolve()
    recommendations_path = Path(args.recommendations).resolve()
    if not vault_path.exists():
        parser.error(f"vault does not exist: {vault_path}")
    if not recommendations_path.exists():
        parser.error(f"recommendation file does not exist: {recommendations_path}")

    text = read_text_file(recommendations_path)
    rows = parse_row_dicts(text)
    recommendations = canonicalize_recommendations(
        vault_path,
        dedupe_recommendations(rows),
    )

    state_path = DEFAULT_BACKUP_ROOT / "reports" / "gemini-applied" / "state.json"
    report_dir = DEFAULT_BACKUP_ROOT / "reports" / "gemini-applied"
    state = load_state(state_path)
    state_entries = state.setdefault("entries", {})
    processed_fingerprints = {
        entry.get("fingerprint")
        for entry in state_entries.values()
        if entry.get("fingerprint")
    }

    results: list[ApplyResult] = []
    for rec in recommendations:
        if not confidence_allows(rec.confidence, args.min_confidence):
            results.append(
                ApplyResult(
                    rec.source_path,
                    "skipped",
                    f"confidence below threshold ({rec.confidence})",
                    fingerprint=rec.fingerprint,
                )
            )
            continue

        prior = state_entries.get(rec.source_path)
        if rec.fingerprint in processed_fingerprints:
            results.append(
                ApplyResult(
                    rec.source_path,
                    "skipped",
                    "same recommendation already processed",
                    destination=(prior.get("destination", "") if prior else ""),
                    fingerprint=rec.fingerprint,
                )
            )
            continue

        result = apply_recommendation(vault_path, rec, dry_run=args.dry_run)
        results.append(result)

        if result.status in {"applied", "planned", "manual"}:
            state_entries[rec.source_path] = {
                "fingerprint": rec.fingerprint,
                "status": result.status,
                "destination": result.destination,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "action": rec.action,
                "title": rec.proposed_title or rec.current_title,
            }
            processed_fingerprints.add(rec.fingerprint)

    if not args.dry_run:
        save_state(state_path, state)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = f"gemini_apply_{timestamp}{'_dry_run' if args.dry_run else ''}.md"
    report_path = report_dir / report_name
    write_report(report_path, results, dry_run=args.dry_run)

    summary: dict[str, int] = {}
    for result in results:
        summary[result.status] = summary.get(result.status, 0) + 1

    print(f"Parsed rows: {len(rows)}")
    print(f"Deduped recommendations: {len(recommendations)}")
    for status in sorted(summary):
        print(f"{status}: {summary[status]}")
    print(f"Report: {report_path}")
    if not args.dry_run:
        print(f"State: {state_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
