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
    apply_props_to_file,
    get_current_props,
    match_index,
    read_text_file,
    remove_props_from_file,
    DEFAULT_BACKUP_ROOT,
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
    current_title: str
    current_props: dict
    current_domain: Optional[str]
    current_engine: Optional[str]
    current_type: object
    current_topic: List[str]
    current_tags: List[str]
    title_review: str
    suggested_title: Optional[str]
    suggested_domain: Optional[str]
    suggested_engine: Optional[str]
    suggested_type: object
    suggested_topic: List[str]
    suggested_tags: List[str]
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
    cleaned = str(value).strip()
    return TYPE_ALIASES.get(cleaned.lower(), cleaned)


def relative_to_vault(path: Path, vault_path: Path) -> str:
    return path.resolve().relative_to(vault_path.resolve()).as_posix()


def scalar_prop(props: dict, key: str) -> Optional[str]:
    value = props.get(key)
    if isinstance(value, list):
        return None
    if value is None:
        return None
    return str(value)


def list_prop(props: dict, *keys: str) -> List[str]:
    values: List[str] = []
    for key in keys:
        if key not in props:
            continue
        raw = props.get(key)
        items = raw if isinstance(raw, list) else [raw]
        for item in items:
            if item is None:
                continue
            cleaned = str(item).strip()
            if cleaned:
                values.append(cleaned)
    return values


def unique_list(values: List[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        cleaned = str(value).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def compact_list_value(values: List[str]):
    cleaned = unique_list(values)
    if not cleaned:
        return None
    if len(cleaned) == 1:
        return cleaned[0]
    return cleaned


def value_contains(value, target: str) -> bool:
    if isinstance(value, list):
        return target in value
    return value == target


TYPE_ALIASES = {
    "resource": "리소스",
    "자료": "리소스",
}

TYPE_HINTS = (
    ("수업안", "수업안"),
    ("지도안", "수업안"),
    ("교수학습", "수업안"),
    ("감상문", "감상문"),
    ("거시예측", "거시예측"),
    ("시장일지", "시장일지"),
    ("자서전", "자서전"),
    ("리소스", "리소스"),
    ("resource", "리소스"),
)

TOPIC_STOPWORDS = {
    "수업",
    "학급",
    "투자",
    "자기",
    "관계",
    "생산성",
    "횡단",
    "DIY",
    "idea",
    "tip",
    "계획",
    "질문",
    "리소스",
    "감상문",
    "수업안",
    "concept",
    "pattern",
    "principle",
    "experiment",
}

_TOPIC_VOCAB_CACHE: Dict[str, List[str]] = {}
_TAG_VOCAB_CACHE: Dict[str, List[str]] = {}

TITLE_GENERIC_EXACT = {
    "생각",
    "생각들",
    "제목 없음",
    "untitled",
    "index",
    "vault",
    "agents",
    "정리",
    "메모",
    "자료",
    "리소스",
    "tip",
    "아이디어",
    "idea",
    "질문",
    "계획",
    "수업",
    "투자",
    "자기",
    "관계",
    "학급",
    "교육",
    "철학",
    "생활",
}

TITLE_GENERIC_PARTS = (
    "정리",
    "메모",
    "자료",
    "리소스",
    "아이디어",
    "idea",
    "tip",
    "질문",
    "계획",
)

TITLE_CLAIM_HINTS = (
    "해야",
    "필요",
    "중요",
    "낫다",
    "좋다",
    "막는다",
    "줄인다",
    "돕는다",
    "만든다",
    "바꾼다",
    "위한",
    "하려면",
    "하는 법",
    "원칙",
    "전략",
    "체크리스트",
)


def normalize_list_items(values: List[str], aliases: Optional[Dict[str, str]] = None) -> List[str]:
    normalized = []
    for value in values:
        cleaned = str(value).strip()
        if not cleaned:
            continue
        alias = aliases.get(cleaned.lower(), cleaned) if aliases else cleaned
        normalized.append(alias)
    return unique_list(normalized)


def normalize_match_key(value: str) -> str:
    return re.sub(r"[\s\-_#\+\[\]\(\)]+", "", str(value).strip().lower())


def normalize_title_text(value: str) -> str:
    text = str(value).replace("_", " ").strip()
    return re.sub(r"\s+", " ", text)


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    lines = text.splitlines()
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return "\n".join(lines[idx + 1 :])
    return text


def split_candidate_sentences(line: str) -> List[str]:
    parts = re.split(r"(?<=[.!?。])\s+", line)
    return [normalize_title_text(part).strip("\"'“”‘’ ") for part in parts if part.strip()]


def title_has_topic_hint(title: str, topics: List[str]) -> bool:
    title_key = normalize_match_key(title)
    for topic in topics:
        topic_key = normalize_match_key(topic)
        if len(topic_key) >= 2 and topic_key in title_key:
            return True
    return False


def title_is_generic(title: str, topics: List[str]) -> Tuple[bool, List[str]]:
    normalized = normalize_title_text(title)
    lowered = normalized.lower()
    title_key = normalize_match_key(normalized)
    tokens = [token for token in re.split(r"[\s:/\-\(\)\[\],]+", normalized) if token]
    topic_hit = title_has_topic_hint(normalized, topics)
    reasons: List[str] = []

    if lowered in TITLE_GENERIC_EXACT:
        reasons.append("제목이 너무 추상적임")
    if len(tokens) == 1 and len(title_key) <= 2 and not topic_hit:
        reasons.append("제목만으로 대상을 짐작하기 어려움")
    if any(lowered.endswith(part) for part in TITLE_GENERIC_PARTS) and not topic_hit:
        reasons.append("형식어 중심의 임시 제목 가능성")
    if not any(hint in normalized for hint in TITLE_CLAIM_HINTS) and not topic_hit:
        if len(tokens) == 1 and len(title_key) <= 6:
            reasons.append("주어+핵심 주장 구조가 아직 드러나지 않음")

    return (bool(reasons), unique_list(reasons))


def title_is_clear(title: str, topics: List[str]) -> bool:
    is_generic, _ = title_is_generic(title, topics)
    return not is_generic


def extract_title_candidates(text: str) -> List[str]:
    body = strip_frontmatter(text)
    candidates: List[str] = []
    seen = set()

    def add_candidate(raw: str):
        candidate = normalize_title_text(raw)
        if (
            not candidate
            or candidate in seen
            or len(candidate) < 6
            or len(candidate) > 45
            or candidate.startswith(("http://", "https://"))
            or candidate.startswith(("**", "`"))
            or ".md" in candidate.lower()
            or re.match(r"^\d", candidate)
        ):
            return
        seen.add(candidate)
        candidates.append(candidate)

    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("```", "---", "|", ">")):
            continue
        if re.match(r"^[-*+]\s", stripped):
            continue
        if stripped.startswith("#"):
            add_candidate(re.sub(r"^#+\s*", "", stripped))
            if len(candidates) >= 5:
                break
            continue

        for sentence in split_candidate_sentences(stripped):
            if "?" not in sentence and not any(hint in sentence for hint in TITLE_CLAIM_HINTS):
                continue
            add_candidate(sentence)
            if len(candidates) >= 5:
                break
        if len(candidates) >= 5:
            break

    return candidates


def review_title(path: Path, text: str, topics: List[str]) -> Tuple[str, str, Optional[str], List[str]]:
    current_title = normalize_title_text(path.stem)
    is_generic, reasons = title_is_generic(current_title, topics)
    if not is_generic:
        return current_title, "clear", None, []

    suggested_title = None
    current_key = normalize_match_key(current_title)
    for candidate in extract_title_candidates(text):
        if normalize_match_key(candidate) == current_key:
            continue
        if title_is_clear(candidate, topics):
            suggested_title = candidate
            break

    return current_title, "needs_review", suggested_title, reasons


def load_existing_topics(vault_path: Path) -> List[str]:
    cache_key = str(vault_path.resolve())
    if cache_key in _TOPIC_VOCAB_CACHE:
        return _TOPIC_VOCAB_CACHE[cache_key]

    topics = set()
    for path in vault_path.rglob("*.md"):
        if "_PKM_BACKUP" in path.parts or "Clippings" in path.parts or "daily" in path.parts or "knowledge" in path.parts:
            continue
        props = get_current_props(path)
        for item in list_prop(props, "topic"):
            if item and item not in TOPIC_STOPWORDS and len(item) >= 2:
                topics.add(item)

    ordered = sorted(topics, key=lambda value: (-len(value), value))
    _TOPIC_VOCAB_CACHE[cache_key] = ordered
    return ordered


def load_existing_tags(vault_path: Path) -> List[str]:
    cache_key = str(vault_path.resolve())
    if cache_key in _TAG_VOCAB_CACHE:
        return _TAG_VOCAB_CACHE[cache_key]

    tags = set()
    tags_root = (vault_path / "Tags").resolve()
    if tags_root.exists():
        for candidate in tags_root.iterdir():
            raw = candidate.name.strip()
            cleaned = re.sub(r"^[#+]+", "", raw).strip()
            if cleaned and cleaned.lower() not in {"moc", ".space"}:
                tags.add(cleaned)

    for path in vault_path.rglob("*.md"):
        if "_PKM_BACKUP" in path.parts or "Clippings" in path.parts or "daily" in path.parts or "knowledge" in path.parts:
            continue
        props = get_current_props(path)
        for item in list_prop(props, "tags", "tag"):
            cleaned = str(item).strip()
            if cleaned:
                tags.add(cleaned)

    ordered = sorted(tags, key=lambda value: (-len(value), value))
    _TAG_VOCAB_CACHE[cache_key] = ordered
    return ordered


def match_vocab_in_title(title: str, vocab: List[str]) -> List[str]:
    title_key = normalize_match_key(title)
    matches: List[str] = []
    for candidate in vocab:
        if candidate in TOPIC_STOPWORDS:
            continue
        candidate_key = normalize_match_key(candidate)
        if len(candidate_key) < 2:
            continue
        if candidate_key and candidate_key in title_key:
            matches.append(candidate)
    return unique_list(matches)


def match_vocab_in_text(text: str, vocab: List[str]) -> List[str]:
    sample = text[:800]
    matches: List[str] = []
    for candidate in vocab:
        cleaned = candidate.strip()
        if cleaned in TOPIC_STOPWORDS or len(cleaned) < 2:
            continue
        if cleaned in sample:
            matches.append(cleaned)
    return unique_list(matches)


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
        return None
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
    for token, suggested in TYPE_HINTS:
        if token.lower() in lowered_name:
            return suggested
    return None


def infer_engine(path: Path, text: str, note_type: Optional[str]) -> Optional[str]:
    lowered = path.stem.lower()

    if note_type == "리소스":
        return None
    if any(token in lowered for token in ("원칙", "체크리스트", "전략")):
        return "principle"
    if any(token in lowered for token in ("패턴", "반복", "습관")):
        return "pattern"
    return "concept"


def infer_topic(path: Path, text: str, vault_path: Path) -> List[str]:
    vocab = load_existing_topics(vault_path)
    return match_vocab_in_title(path.stem, vocab)[:4]


def infer_tags(
    path: Path,
    text: str,
    vault_path: Path,
) -> List[str]:
    vocab = load_existing_tags(vault_path)
    title_matches = match_vocab_in_title(path.stem, vocab)
    return unique_list(title_matches)[:6]


def determine_destination(
    vault_path: Path,
    domain: Optional[str],
    engine: Optional[str],
    note_type,
) -> Path:
    if domain and (engine in {"concept", "experiment"} or value_contains(note_type, "리소스")):
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
    current_type_values = normalize_list_items(list_prop(current_props, "type"), TYPE_ALIASES)
    current_type = compact_list_value(current_type_values)
    current_topic = normalize_list_items(list_prop(current_props, "topic"))
    current_tags = normalize_list_items(list_prop(current_props, "tags", "tag"))

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

    inferred_domain = infer_domain(path, text)
    inferred_type = infer_type(path, text)
    inferred_engine = infer_engine(path, text, choose(mapping_type, current_type_values[0] if current_type_values else None, inferred_type))
    inferred_topic = infer_topic(path, text, vault_path)

    suggested_domain = choose(mapping_domain, current_domain, inferred_domain)
    suggested_type = choose(mapping_type, current_type, inferred_type)
    suggested_engine = choose(mapping_engine, current_engine, inferred_engine)
    suggested_topic = unique_list(current_topic + inferred_topic) if current_topic else inferred_topic

    if value_contains(suggested_type, "리소스") and mapping_engine is None and current_engine is None:
        suggested_engine = None
    suggested_tags = unique_list(current_tags + infer_tags(path, text, vault_path))

    current_title, title_review, suggested_title, title_reasons = review_title(
        path=path,
        text=text,
        topics=suggested_topic or current_topic,
    )
    if title_review != "clear":
        title_note = "제목 보정 필요"
        if suggested_title:
            title_note += f" (제안: {suggested_title})"
        if title_reasons:
            title_note += " - " + ", ".join(title_reasons)
        reasons.append(title_note)

    if not suggested_domain:
        reasons.append("추천 domain 없음")

    if not value_contains(suggested_type, "리소스") and not suggested_engine:
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
        elif title_review != "clear" or not suggested_domain or (suggested_type != "리소스" and not suggested_engine):
            status = "needs_review"
        else:
            status = "ready"

    return ReviewItem(
        source_path=path.resolve(),
        source_rel=relative_to_vault(path, vault_path),
        current_title=current_title,
        current_props=current_props,
        current_domain=normalize_domain(scalar_prop(current_props, "domain")),
        current_engine=normalize_engine(scalar_prop(current_props, "engine")),
        current_type=current_type,
        current_topic=current_topic,
        current_tags=current_tags,
        title_review=title_review,
        suggested_title=suggested_title,
        suggested_domain=suggested_domain,
        suggested_engine=suggested_engine,
        suggested_type=suggested_type,
        suggested_topic=suggested_topic,
        suggested_tags=suggested_tags,
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
        "| 현재 경로 | 현재 제목 | 제목 검토 | 제안 제목 | 현재 YAML | 추천 YAML | 추천 목적지 | 이동 가능 | 보류 사유 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for item in review.items:
        current_yaml = ", ".join(
            part
            for part in [
                f"domain={item.current_domain}" if item.current_domain else "",
                f"engine={item.current_engine}" if item.current_engine else "",
                f"type={item.current_type}" if item.current_type else "",
                f"topic={item.current_topic}" if item.current_topic else "",
                f"tags={item.current_tags}" if item.current_tags else "",
            ]
            if part
        ) or "-"

        suggested_yaml = ", ".join(
            part
            for part in [
                f"domain={item.suggested_domain}" if item.suggested_domain else "",
                f"engine={item.suggested_engine}" if item.suggested_engine else "",
                f"type={item.suggested_type}" if item.suggested_type else "",
                f"topic={item.suggested_topic}" if item.suggested_topic else "",
                f"tags={item.suggested_tags}" if item.suggested_tags else "",
            ]
            if part
        ) or "-"

        hold_reason = "; ".join(item.reasons) if item.reasons else "-"
        move_allowed = "예" if item.move_allowed else "아니오"
        lines.append(
            "| `{path}` | {title} | `{title_review}` | {suggested_title} | {current} | {suggested} | `{destination}` | {allowed} | {reason} |".format(
                path=item.source_rel,
                title=item.current_title,
                title_review=item.title_review,
                suggested_title=f"`{item.suggested_title}`" if item.suggested_title else "-",
                current=current_yaml,
                suggested=suggested_yaml,
                destination=item.suggested_destination.as_posix(),
                allowed=move_allowed,
                reason=hold_reason,
            )
        )

    return "\n".join(lines) + "\n"


def write_report(vault_path: Path, review: BatchReview) -> Path:
    report_dir = (DEFAULT_BACKUP_ROOT / "reports" / "pkm-batches").resolve()
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
            if value_contains(item.suggested_type, "리소스") and item.current_engine and item.current_engine not in ENGINE_VALUES:
                remove_keys.append("engine")
        if item.suggested_topic:
            set_props["topic"] = compact_list_value(item.suggested_topic)
        if item.suggested_tags:
            set_props["tags"] = compact_list_value(item.suggested_tags)

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
            backup_file(current_review.source_path, vault_path)
            shutil.copy2(current_review.source_path, destination_path)
            if destination_path.exists():
                current_review.source_path.unlink()
                summary["moved"] += 1
            else:
                summary["error"] += 1
        except Exception:
            summary["error"] += 1

    return summary
