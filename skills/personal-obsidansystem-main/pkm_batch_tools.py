"""Batch review and staged migration helpers for PARA -> PKM."""

import re
import shutil
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pkm_core import (
    DOMAIN_VALUES,
    ENGINE_VALUES,
    TYPE_VALUES,
    apply_props_to_file,
    backup_file,
    get_current_props,
    match_index,
    read_text_file,
    remove_props_from_file,
)


PARA_ROOTS = (
    "1 PROJECT(목표, 마감기한)",
    "2 AREA(책임, 장기과제, 기한 없음)",
    "3 Resources(관심사, area를 위한)",
)

DEFAULT_SOURCE = "3 Resources(관심사, area를 위한)/코딩 소프트웨어 스마트작업"
MIN_BATCH_SIZE = 5
MAX_BATCH_SIZE = 10
DEFAULT_BATCH_SIZE = 8

REVIEW_STATUS_PRIORITY = {
    "ready": 0,
    "needs_review": 1,
    "link_sensitive": 2,
    "conflict": 3,
}

DOMAIN_ALIASES = {
    "diy": "DIY",
    "Diy": "DIY",
    "학급경영": "학급",
    "[자기]": "자기",
    "자기 ": "자기",
}

ENGINE_ALIASES = {
    "pattern ": "pattern",
    "concept ": "concept",
}


@dataclass
class ReviewItem:
    source_path: Path
    source_rel: str
    current_props: dict
    current_domain: Optional[str]
    current_engine: Optional[str]
    current_type: Optional[str]
    suggested_domain: Optional[str]
    suggested_engine: Optional[str]
    suggested_type: Optional[str]
    suggested_destination: Path
    review_status: str
    reasons: List[str] = field(default_factory=list)

    @property
    def move_allowed(self) -> bool:
        return self.review_status == "ready"


@dataclass
class BatchReview:
    source_folder: str
    source_path: Path
    report_path: Path
    total_files_in_source: int
    items: List[ReviewItem]
    status_counts: Dict[str, int]
    reviewed_at: str


def list_para_source_folders(vault_path: Path) -> List[str]:
    folders = []
    for root_name in PARA_ROOTS:
        root_path = (vault_path / root_name).resolve()
        if not root_path.exists():
            continue
        if any(iter_markdown_files(root_path)):
            folders.append(root_name)
        for candidate in sorted(root_path.rglob("*")):
            if candidate.is_dir() and candidate.name != "_PKM_BACKUP":
                if any(iter_markdown_files(candidate)):
                    folders.append(candidate.relative_to(vault_path).as_posix())
    preferred = DEFAULT_SOURCE if DEFAULT_SOURCE in folders else None
    if preferred:
        folders = [preferred] + [folder for folder in folders if folder != preferred]
    return folders


def iter_markdown_files(folder: Path):
    for path in sorted(folder.rglob("*.md")):
        if "_PKM_BACKUP" in path.parts:
            continue
        yield path


def resolve_source_folder(vault_path: Path, source_folder: Optional[str]) -> Tuple[str, Path]:
    available = list_para_source_folders(vault_path)
    chosen = source_folder or (available[0] if available else DEFAULT_SOURCE)
    source_path = (vault_path / chosen).resolve()
    return chosen, source_path


def normalize_domain(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = str(value).strip()
    return DOMAIN_ALIASES.get(cleaned, cleaned)


def normalize_engine(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = str(value).strip()
    return ENGINE_ALIASES.get(cleaned, cleaned)


def normalize_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return str(value).strip()


def relative_to_vault(path: Path, vault_path: Path) -> str:
    return path.resolve().relative_to(vault_path.resolve()).as_posix()


def scalar_prop(props: dict, key: str) -> Optional[str]:
    value = props.get(key)
    if isinstance(value, list):
        return None
    if value is None:
        return None
    return str(value)


def mostly_links(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    sample = lines[:30]
    linkish = 0
    for line in sample:
        if line.startswith("http") or "http://" in line or "https://" in line:
            linkish += 1
        elif re.match(r"^- \[.\]", line):
            linkish += 1
    return linkish >= max(3, len(sample) // 3)


def infer_domain(path: Path, text: str) -> Optional[str]:
    raw = path.as_posix()
    name = path.stem

    if "/교육 학급운영/수업/" in raw:
        return "수업"
    if "/교육 학급운영/" in raw:
        return "수업" if "수업" in name else "학급"
    if "/투자/" in raw or "투자" in name:
        return "투자"
    if "/인간 관계와 커뮤니케이션/" in raw:
        return "관계"
    if "/자기 성찰 및 성장/" in raw:
        return "자기"
    if "/건강/" in raw:
        return "자기"
    if "/문제해결 및 사고/" in raw:
        return "횡단"
    if "/코딩 소프트웨어 스마트작업/" in raw:
        return "생산성"
    if "/철학 통찰/" in raw:
        return "횡단"
    if "/사회 문제/" in raw or "/이과적 지식(과학 사유)/" in raw:
        return "횡단"
    if "/diy/" in raw or "/DIY/" in raw:
        return "DIY"
    if "/생활 tip/" in raw:
        return "생산성"
    if "/육아/" in raw or "/음악/" in raw:
        return "자기"
    if "/모임운영/" in raw:
        return "관계"

    if "교육연극" in text:
        return "수업"
    if any(token in text for token in ("편향", "의사결정", "역설")):
        return "횡단"
    return None


def infer_type(path: Path, text: str) -> Optional[str]:
    lowered_name = path.stem.lower()
    if mostly_links(text):
        return "리소스"
    if "요약" in path.stem or "summary" in lowered_name:
        return "감상문"
    if "수업안" in path.stem or "지도안" in path.stem:
        return "수업안"
    if "시장일지" in path.stem:
        return "시장일지"
    if "거시" in path.stem and "예측" in path.stem:
        return "거시예측"
    return None


def infer_engine(path: Path, text: str, note_type: Optional[str]) -> Optional[str]:
    lowered = path.stem.lower()

    if note_type == "리소스":
        return None
    if note_type == "수업안":
        return "experiment"
    if note_type == "시장일지":
        return "experiment"
    if note_type == "거시예측":
        return "concept"
    if any(token in lowered for token in ("원칙", "체크리스트", "전략")):
        return "principle"
    if any(token in lowered for token in ("패턴", "반복", "습관")):
        return "pattern"
    return "concept"


def determine_destination(
    vault_path: Path,
    domain: Optional[str],
    engine: Optional[str],
    note_type: Optional[str],
) -> Path:
    if domain and (engine in {"concept", "experiment"} or note_type == "리소스"):
        return (vault_path / "10_NOTE" / domain).resolve()
    if domain and engine == "pattern":
        return (vault_path / "20_THINKING" / domain).resolve()
    if domain and engine == "principle":
        return (vault_path / "30_SYSTEM" / domain).resolve()
    return (vault_path / "Inbox").resolve()


def choose(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if value:
            return value
    return None


def extract_wikilink_targets(text: str) -> List[str]:
    matches = re.findall(r"\[\[([^\]]+)\]\]", text)
    targets = []
    for match in matches:
        target = match.split("|", 1)[0].split("#", 1)[0].strip()
        if target:
            targets.append(target.replace("\\", "/"))
    return targets


def extract_markdown_targets(text: str) -> List[str]:
    return re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)


def resolve_markdown_target(source_path: Path, raw_target: str, vault_path: Path) -> Optional[Path]:
    target = raw_target.strip().strip("<>").split("#", 1)[0].strip()
    if not target or target.startswith(("http://", "https://", "mailto:", "#")):
        return None

    if target.startswith("/"):
        candidate = (vault_path / target.lstrip("/")).resolve()
    else:
        candidate = (source_path.parent / target).resolve()

    if candidate.exists():
        return candidate
    if candidate.suffix == "":
        md_candidate = candidate.with_suffix(".md")
        if md_candidate.exists():
            return md_candidate
    return None


def find_link_sensitive_references(
    vault_path: Path,
    target_path: Path,
    all_vault_notes: List[Path],
) -> List[str]:
    hits = []
    target_rel = relative_to_vault(target_path, vault_path)
    target_rel_no_ext = target_rel[:-3] if target_rel.endswith(".md") else target_rel
    target_resolved = target_path.resolve()

    for note_path in all_vault_notes:
        if note_path.resolve() == target_resolved:
            continue
        try:
            text = read_text_file(note_path)
        except Exception:
            continue

        matched = False
        for target in extract_wikilink_targets(text):
            if "/" in target and target == target_rel_no_ext:
                hits.append(relative_to_vault(note_path, vault_path))
                matched = True
                break
        if matched:
            continue

        for raw_target in extract_markdown_targets(text):
            resolved = resolve_markdown_target(note_path, raw_target, vault_path)
            if resolved and resolved.resolve() == target_resolved:
                hits.append(relative_to_vault(note_path, vault_path))
                break

    return hits


def review_single_note(path: Path, vault_path: Path, all_vault_notes: List[Path]) -> ReviewItem:
    text = read_text_file(path)
    current_props = get_current_props(path)
    reasons = []

    current_domain = normalize_domain(scalar_prop(current_props, "domain"))
    current_engine = normalize_engine(scalar_prop(current_props, "engine"))
    current_type = normalize_type(scalar_prop(current_props, "type"))

    mapping = match_index(path.stem)
    mapping_domain = normalize_domain(mapping.get("domain"))
    mapping_engine = normalize_engine(mapping.get("engine"))
    mapping_type = normalize_type(mapping.get("type"))

    if current_domain and current_domain not in DOMAIN_VALUES:
        reasons.append(f"현재 domain 보정 필요: {current_domain}")
        current_domain = None
    if current_engine and current_engine not in ENGINE_VALUES:
        reasons.append(f"현재 engine 보정 필요: {current_engine}")
        current_engine = None
    if current_type and current_type not in TYPE_VALUES:
        reasons.append(f"현재 type 보정 필요: {current_type}")
        current_type = None

    inferred_domain = infer_domain(path, text)
    inferred_type = infer_type(path, text)
    inferred_engine = infer_engine(path, text, choose(mapping_type, current_type, inferred_type))

    suggested_domain = choose(mapping_domain, current_domain, inferred_domain)
    suggested_type = choose(mapping_type, current_type, inferred_type)
    suggested_engine = choose(mapping_engine, current_engine, inferred_engine)

    if suggested_type == "리소스" and mapping_engine is None and current_engine is None:
        suggested_engine = None

    if not suggested_domain:
        reasons.append("추천 domain 없음")

    if suggested_type != "리소스" and not suggested_engine:
        reasons.append("추천 engine 없음")

    destination_dir = determine_destination(
        vault_path=vault_path,
        domain=suggested_domain,
        engine=suggested_engine,
        note_type=suggested_type,
    )

    destination_path = (destination_dir / path.name).resolve()
    if destination_path.exists() and destination_path.resolve() != path.resolve():
        reasons.append(f"대상 파일 충돌: {relative_to_vault(destination_path, vault_path)}")
        status = "conflict"
    else:
        link_hits = find_link_sensitive_references(vault_path, path, all_vault_notes)
        if link_hits:
            reasons.append("경로 지정 링크 참조 존재: " + ", ".join(link_hits[:3]))
            status = "link_sensitive"
        elif not suggested_domain or (suggested_type != "리소스" and not suggested_engine):
            status = "needs_review"
        else:
            status = "ready"

    return ReviewItem(
        source_path=path.resolve(),
        source_rel=relative_to_vault(path, vault_path),
        current_props=current_props,
        current_domain=normalize_domain(scalar_prop(current_props, "domain")),
        current_engine=normalize_engine(scalar_prop(current_props, "engine")),
        current_type=normalize_type(scalar_prop(current_props, "type")),
        suggested_domain=suggested_domain,
        suggested_engine=suggested_engine,
        suggested_type=suggested_type,
        suggested_destination=destination_dir,
        review_status=status,
        reasons=reasons,
    )


def build_report(review: BatchReview) -> str:
    lines = [
        "# PARA -> PKM 배치 검토 보고서",
        "",
        f"- 검토 시각: `{review.reviewed_at}`",
        f"- source: `{review.source_folder}`",
        f"- source 내 전체 md 수: `{review.total_files_in_source}`",
        f"- 보고서 대상 배치 수: `{len(review.items)}`",
        f"- 상태 요약: `ready {review.status_counts.get('ready', 0)}` / "
        f"`needs_review {review.status_counts.get('needs_review', 0)}` / "
        f"`link_sensitive {review.status_counts.get('link_sensitive', 0)}` / "
        f"`conflict {review.status_counts.get('conflict', 0)}`",
        "",
        "| 현재 경로 | 현재 YAML | 추천 YAML | 추천 목적지 | 이동 가능 | 보류 사유 |",
        "|---|---|---|---|---|---|",
    ]

    for item in review.items:
        current_yaml = ", ".join(
            part
            for part in [
                f"domain={item.current_domain}" if item.current_domain else "",
                f"engine={item.current_engine}" if item.current_engine else "",
                f"type={item.current_type}" if item.current_type else "",
            ]
            if part
        ) or "-"

        suggested_yaml = ", ".join(
            part
            for part in [
                f"domain={item.suggested_domain}" if item.suggested_domain else "",
                f"engine={item.suggested_engine}" if item.suggested_engine else "",
                f"type={item.suggested_type}" if item.suggested_type else "",
            ]
            if part
        ) or "-"

        hold_reason = "; ".join(item.reasons) if item.reasons else "-"
        move_allowed = "예" if item.move_allowed else "아니오"
        lines.append(
            "| `{path}` | {current} | {suggested} | `{destination}` | {allowed} | {reason} |".format(
                path=item.source_rel,
                current=current_yaml,
                suggested=suggested_yaml,
                destination=item.suggested_destination.as_posix(),
                allowed=move_allowed,
                reason=hold_reason,
            )
        )

    return "\n".join(lines) + "\n"


def write_report(vault_path: Path, review: BatchReview) -> Path:
    report_dir = (vault_path / "reports" / "pkm-batches").resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = review.source_folder.replace("/", "__").replace(" ", "_")
    report_path = report_dir / f"batch_{slug}_{timestamp}.md"
    report_path.write_text(build_report(review), encoding="utf-8")
    return report_path


def review_para_batch(
    vault_path: Path,
    source_folder: Optional[str] = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> BatchReview:
    chosen_source, source_path = resolve_source_folder(vault_path, source_folder)
    if not source_path.exists():
        raise FileNotFoundError(f"source folder not found: {chosen_source}")

    batch_size = max(MIN_BATCH_SIZE, min(MAX_BATCH_SIZE, int(batch_size)))
    source_files = list(iter_markdown_files(source_path))
    all_vault_notes = [
        path
        for path in vault_path.rglob("*.md")
        if "_PKM_BACKUP" not in path.parts and "knowledge" not in path.parts
        and "daily" not in path.parts and "Clippings" not in path.parts and "MOC" not in path.parts
    ]

    reviewed = [review_single_note(path, vault_path, all_vault_notes) for path in source_files]
    reviewed.sort(
        key=lambda item: (
            REVIEW_STATUS_PRIORITY.get(item.review_status, 99),
            item.source_rel.lower(),
        )
    )
    batch_items = reviewed[:batch_size]
    status_counts = Counter(item.review_status for item in batch_items)

    review = BatchReview(
        source_folder=chosen_source,
        source_path=source_path,
        report_path=Path(),
        total_files_in_source=len(source_files),
        items=batch_items,
        status_counts=dict(status_counts),
        reviewed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    review.report_path = write_report(vault_path, review)
    return review


def apply_stage1_yaml(items: List[ReviewItem]) -> Dict[str, int]:
    summary = {"ok": 0, "skipped": 0, "error": 0}
    for item in items:
        set_props = {}
        remove_keys = []

        if item.suggested_domain:
            set_props["domain"] = item.suggested_domain
        if item.suggested_engine:
            set_props["engine"] = item.suggested_engine
        if item.suggested_type:
            set_props["type"] = item.suggested_type
            if item.suggested_type == "리소스" and item.current_engine and item.current_engine not in ENGINE_VALUES:
                remove_keys.append("engine")

        if remove_keys:
            remove_result = remove_props_from_file(item.source_path, remove_keys)
            if remove_result.startswith("error"):
                summary["error"] += 1
                continue

        if set_props:
            result = apply_props_to_file(item.source_path, set_props, overwrite=True)
        else:
            result = "skipped"

        if result == "ok":
            summary["ok"] += 1
        elif result == "skipped":
            summary["skipped"] += 1
        else:
            summary["error"] += 1

    return summary


def move_stage2_items(vault_path: Path, items: List[ReviewItem]) -> Dict[str, int]:
    summary = {"moved": 0, "skipped": 0, "conflict": 0, "error": 0}

    all_vault_notes = [
        path
        for path in vault_path.rglob("*.md")
        if "_PKM_BACKUP" not in path.parts
    ]

    for item in items:
        if not item.source_path.exists():
            summary["skipped"] += 1
            continue

        current_review = review_single_note(item.source_path, vault_path, all_vault_notes)
        if current_review.review_status != "ready":
            if current_review.review_status == "conflict":
                summary["conflict"] += 1
            else:
                summary["skipped"] += 1
            continue

        destination_dir = current_review.suggested_destination
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination_path = (destination_dir / current_review.source_path.name).resolve()
        if destination_path.exists():
            summary["conflict"] += 1
            continue

        try:
            backup_file(current_review.source_path)
            shutil.copy2(current_review.source_path, destination_path)
            if destination_path.exists():
                current_review.source_path.unlink()
                summary["moved"] += 1
            else:
                summary["error"] += 1
        except Exception:
            summary["error"] += 1

    return summary
