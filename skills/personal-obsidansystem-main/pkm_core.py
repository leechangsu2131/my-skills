"""Shared PKM utilities for the Obsidian property manager."""

import hashlib
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


INDEX_MAPPING = {
    "나에 대한 이해": {"domain": "자기", "engine": "concept"},
    "생각 습관 개선": {"domain": "자기", "engine": "principle"},
    "성장 마인드셋": {"domain": "자기", "engine": "concept"},
    "행동 습관 바꾸기": {"domain": "자기", "engine": "principle"},
    "멘탈훈련": {"domain": "자기", "engine": "experiment"},
    "선택과 후회 ft 의사결정": {"domain": "자기", "engine": "pattern"},
    "PESM 증후군": {"domain": "자기", "engine": "concept"},
    "5단계 연꽃 기법": {"domain": "자기", "engine": "experiment"},
    "국어 수업 IDEA": {"domain": "수업", "engine": "experiment"},
    "역사 수업 idea": {"domain": "수업", "engine": "experiment"},
    "개념기반교육과정": {"domain": "수업", "engine": "concept"},
    "문학기반 인성교육": {"domain": "수업", "engine": "concept"},
    "정반합을 위한 토론": {"domain": "수업", "engine": "experiment"},
    "가르치고 싶은 것": {"domain": "수업", "engine": "principle"},
    "수업을 위한 기초 소양": {"domain": "수업", "engine": "principle"},
    "생각하는 힘": {"domain": "수업", "engine": "concept"},
    "학급 운영": {"domain": "학급", "engine": "principle"},
    "학생과 감정싸움하지말고 규칙을 세워 적용하자": {"domain": "학급", "engine": "principle"},
    "담보를 받자 학생에게": {"domain": "학급", "engine": "experiment"},
    "얍삽한 학생 대처 방안": {"domain": "학급", "engine": "pattern"},
    "학급에서 스트레스 받는 경우": {"domain": "학급", "engine": "pattern"},
    "이지메의 구조": {"domain": "학급", "engine": "concept"},
    "장악력": {"domain": "학급", "engine": "principle"},
    "교실 문화의 변화": {"domain": "학급", "engine": "concept"},
    "다른 선생님을 그리워하는 학생들": {"domain": "학급", "engine": "pattern"},
    "행정실 교사 소통": {"domain": "학급", "engine": "principle"},
    "직관 vs 데이터": {"domain": "자기", "engine": "pattern"},
    "복리의 문제해결력": {"domain": "자기", "engine": "concept"},
    "왜라는 질문을 하고 문제를 해결하자": {"domain": "자기", "engine": "principle"},
    "결정을 번복하지 않으려면": {"domain": "자기", "engine": "principle"},
    "판단과 비논리적해결 분석과 논리적해결": {"domain": "자기", "engine": "pattern"},
    "매개 평가프로토콜": {"domain": "자기", "engine": "experiment"},
    "결정 관찰자를 위한 점검표": {"domain": "자기", "engine": "experiment"},
    "하방은 지지되고 상방이 열려있는 선택하기": {"domain": "투자", "engine": "pattern"},
    "예측수정": {"domain": "투자", "engine": "experiment"},
    "정보의 해석, 수집 반영": {"domain": "투자", "engine": "principle"},
    "사람 마음 얻는법 관계적 roic": {"domain": "관계", "engine": "principle"},
    "리더쉽": {"domain": "관계", "engine": "principle"},
    "논쟁에서 이기기 위한 프레임": {"domain": "관계", "engine": "pattern"},
    "입지를 좁히는 사람들": {"domain": "관계", "engine": "pattern"},
    "설득력을 키우자": {"domain": "관계", "engine": "principle"},
    "부부갈등 해결 결혼 나영": {"domain": "관계", "engine": "experiment"},
    "나는 왜 무시를 쉽게 받는가": {"domain": "자기", "engine": "concept"},
    "사랑": {"domain": "자기", "engine": "concept"},
    "글쓰기": {"domain": "생산성", "engine": "principle"},
    "인지적 구두쇠 이론": {"domain": "자기", "engine": "concept"},
    "기질의 4요소": {"domain": "자기", "engine": "concept"},
    "진화심리학": {"domain": "자기", "engine": "concept"},
    "동양철학": {"domain": "자기", "engine": "concept"},
    "파레토의 법칙": {"domain": "자기", "engine": "concept"},
    "동조효과와 소수의견": {"domain": "관계", "engine": "concept"},
    "여러 모형들": {"domain": "투자", "engine": "concept"},
    "원칙 - 레이달리오": {"domain": "투자", "engine": "principle"},
    "쏠림현상": {"domain": "투자", "engine": "concept"},
    "기저효과 베이즈 정리": {"domain": "투자", "engine": "concept"},
    "투자일지": {"domain": "투자", "engine": "experiment"},
    "투자와 관련된 이론 철학, 상황": {"domain": "투자", "engine": "concept"},
    "캘리기준": {"domain": "투자", "engine": "principle"},
    "자본의 힘": {"domain": "투자", "engine": "concept"},
    "경제 매크로 해석": {"domain": "투자", "engine": "concept"},
    "ai투자": {"domain": "투자", "engine": "experiment"},
    "스톡데일 패러독스": {"domain": "투자", "engine": "pattern"},
    "절세 전략 세금": {"domain": "투자", "engine": "experiment"},
    "대출": {"domain": "투자", "engine": "experiment"},
    "비트코인": {"domain": "투자", "engine": "concept"},
    "diy": {"domain": "DIY", "engine": "experiment"},
    "리콴유가 본 세계": {"domain": "자기", "engine": "concept"},
    "국가발전의 원리": {"domain": "자기", "engine": "concept"},
    "사회에 대한 생각들": {"domain": "자기", "engine": "concept"},
}

DOMAIN_VALUES = ["수업", "학급", "투자", "자기", "관계", "DIY", "생산성", "횡단"]
ENGINE_VALUES = ["concept", "pattern", "principle", "experiment"]
TYPE_VALUES = [
    "수업안",
    "감상문",
    "거시예측",
    "시장일지",
    "자서전",
    "리소스",
    "idea",
    "계획",
    "질문",
    "tip",
    "수업tip",
    "지침",
    "교육연극",
    "moc",
    "MOC",
]

PROP_DESCRIPTIONS = {
    "domain": "삶의 영역\n수업/학급/투자/자기/관계/DIY/생산성/횡단",
    "engine": "사고 단계\nconcept(개념) / pattern(패턴)\nprinciple(원칙) / experiment(실험)",
    "topic": "짧은 주제어 (자유 입력)\n예: 학급갈등, 안전마진, 교육연극",
    "path": "보조 위치 메타데이터\n현재 Vault 폴더 기준 저장 위치\n예: 2 AREA(...) / 교육 학급운영 / 수업 / 공통",
    "tags": "선택 메타데이터\n기존 태그 체계가 있을 때만 보조적으로 사용",
    "type": "노트의 형식(v13 기준)\n수업안 / 감상문 / 거시예측 / 시장일지 / 자서전 / 리소스",
    "status": "진행 상태\n완료 / 초안 / 진행중 / 확인됨 / 반증됨 / 철회",
    "관련종목": "관련 종목 (리스트)\n예: tsmc, 삼성전자\n[a, b] 형식으로 저장됨",
    "확률": "예측 확률 (0.0 ~ 1.0)",
    "중요도": "중요도 숫자 (예: 12)",
    "확인시기": "확인 예정 시기 (예: 2025-06)",
    "상태": "거시예측 상태\n진행중 / 확인됨 / 반증됨 / 철회",
    "날짜": "시장일지 날짜 (예: 2025-10)",
}

READ_ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")
INDEX_SNAPSHOT_EXCLUDED_PARTS = {
    "_PKM_BACKUP",
    "knowledge",
    "daily",
    "Clippings",
    "reports",
    ".obsidian",
    ".trash",
    ".space",
    ".makemd",
    "Tags",
    "MOC",
    "_MOC",
}
RELATION_INCLUDED_TOP_LEVEL = {
    "Inbox",
    "10_NOTE",
    "20_THINKING",
    "30_SYSTEM",
}
RELATION_INCLUDED_PREFIXES = (
    "1 PROJECT(",
    "2 AREA(",
    "3 Resources(",
)
RELATION_EXCLUDED_PREFIXES = (
    "4 ARCHIVE(",
)
LINK_UPDATE_EXCLUDED_PARTS = {
    "_PKM_BACKUP",
    "reports",
    ".obsidian",
    ".trash",
    ".space",
    ".makemd",
    ".smart-env",
}
DOMAIN_VALUE_ALIASES = {
    "diy": "DIY",
    "Diy": "DIY",
    "학급경영": "학급",
    "[자기]": "자기",
    "자기 ": "자기",
}


def read_text_file(path: Path) -> str:
    last_error = None  # type: Optional[Exception]
    for encoding in READ_ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return path.read_text(encoding="utf-8")


DEFAULT_BACKUP_ROOT = Path.home() / "Documents" / "backupvault"


def backup_file(path: Path, vault_path: Optional[Path] = None) -> Path:
    """변경 전 .bak 백업 생성 (절대 삭제 없음 원칙)"""
    root = DEFAULT_BACKUP_ROOT.resolve()
    if vault_path:
        try:
            rel = path.parent.relative_to(vault_path.resolve())
            bak_dir = root / rel
        except ValueError:
            bak_dir = root / path.parent.name
    else:
        bak_dir = root / path.parent.name

    bak_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_path = bak_dir / f"{path.stem}_{ts}{path.suffix}.bak"
    shutil.copy2(path, bak_path)
    return bak_path


def list_backup_files(vault_path: Path) -> list[Path]:
    backup_files = []
    # Legacy interior backups
    for bak_dir in vault_path.rglob("_PKM_BACKUP"):
        backup_files.extend(sorted(bak_dir.glob("*.bak")))
        
    # External backups
    if DEFAULT_BACKUP_ROOT.exists():
        backup_files.extend(sorted(DEFAULT_BACKUP_ROOT.rglob("*.bak")))
        
    return sorted(backup_files)


def remove_empty_backup_dirs(vault_path: Path) -> int:
    removed = 0
    backup_dirs = sorted(vault_path.rglob("_PKM_BACKUP"), key=lambda p: len(p.parts), reverse=True)
    for bak_dir in backup_dirs:
        try:
            if bak_dir.exists() and not any(bak_dir.iterdir()):
                bak_dir.rmdir()
                removed += 1
        except OSError:
            continue
    return removed


def move_backups_outside_vault(vault_path: Path, archive_root: Path) -> dict:
    backup_files = list_backup_files(vault_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = archive_root / f"pkm_backups_{ts}"
    export_dir.mkdir(parents=True, exist_ok=True)

    moved = 0
    errors = []
    for backup_file in backup_files:
        rel = backup_file.relative_to(vault_path)
        target = export_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(backup_file), str(target))
            moved += 1
        except Exception as exc:
            errors.append(f"{backup_file.name}: {exc}")

    removed_dirs = remove_empty_backup_dirs(vault_path)
    return {
        "export_dir": export_dir,
        "moved": moved,
        "removed_dirs": removed_dirs,
        "error_count": len(errors),
        "errors": errors,
    }


def parse_yaml_value(raw: str):
    v = raw.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1]
        if not inner.strip():
            return []
        items = [item.strip().strip("'\"") for item in inner.split(",")]
        return items if len(items) > 1 else (items[0] if items else "")
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    return v


def format_yaml_value(val) -> str:
    if isinstance(val, list):
        if not val:
            return "[]"
        return "[" + ", ".join(str(item) for item in val) + "]"
    s = str(val)
    if any(c in s for c in [":", "#", '"', "'", "[", "]", "{"]):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def escape_markdown_cell(val) -> str:
    return str(val).replace("\n", " ").replace("|", "\\|")


def normalize_prop_list(value) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def normalize_domain_value(value: str) -> str:
    cleaned = str(value).strip()
    return DOMAIN_VALUE_ALIASES.get(cleaned, cleaned)


def sanitize_filename(text: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", str(text).strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(". ")
    return cleaned or "note"


def slugify_note_path(rel_path: str) -> str:
    stem = sanitize_filename(Path(rel_path).stem)
    digest = hashlib.sha1(rel_path.encode("utf-8")).hexdigest()[:8]
    return f"{stem}__{digest}.md"


def read_frontmatter(text: str):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.DOTALL)
    if not m:
        return {}, [], text

    raw = m.group(1)
    body = text[m.end():]
    lines = raw.splitlines()
    props = {}
    blocks = []

    i = 0
    while i < len(lines):
        line = lines[i]
        simple = re.match(r"^([\w가-힣]+)\s*:\s*(.*)$", line)
        if simple:
            key, value = simple.group(1), simple.group(2).strip()

            if value == "" and i + 1 < len(lines) and re.match(r"^\s+-\s", lines[i + 1]):
                block_lines = [line]
                list_items = []
                i += 1
                while i < len(lines) and re.match(r"^\s+-\s?(.*)", lines[i]):
                    item_m = re.match(r"^\s+-\s?(.*)", lines[i])
                    list_items.append(item_m.group(1).strip().strip("'\""))
                    block_lines.append(lines[i])
                    i += 1
                props[key] = list_items if len(list_items) != 1 else list_items[0]
                blocks.append({"key": key, "lines": block_lines, "is_list_block": True})
                continue

            parsed = parse_yaml_value(value)
            if isinstance(parsed, str) and "," in parsed and not re.match(r"^\d", parsed):
                items = [item.strip() for item in parsed.split(",") if item.strip()]
                if len(items) > 1:
                    parsed = items
            props[key] = parsed
            blocks.append({"key": key, "lines": [line], "is_list_block": False})
        else:
            blocks.append({"key": None, "lines": [line], "is_list_block": False})
        i += 1

    return props, blocks, body


def write_frontmatter(props: dict, blocks: list, body: str) -> str:
    written_keys = set()
    new_lines = []

    for block in blocks:
        key = block["key"]
        if key is None:
            new_lines.extend(block["lines"])
        else:
            if key in props:
                new_lines.append(f"{key}: {format_yaml_value(props[key])}")
                written_keys.add(key)

    for key, value in props.items():
        if key not in written_keys:
            new_lines.append(f"{key}: {format_yaml_value(value)}")

    if not new_lines and not body:
        return body
    return "---\n" + "\n".join(new_lines) + "\n---\n" + body


def update_props_in_file(
    path: Path,
    set_props=None,
    remove_keys=None,
    overwrite: bool = False,
    make_backup: bool = True,
    vault_path: Optional[Path] = None,
) -> str:
    try:
        text = read_text_file(path)
        props, blocks, body = read_frontmatter(text)
        changed = False

        for key in remove_keys or []:
            if key in props:
                del props[key]
                changed = True

        for key, value in (set_props or {}).items():
            if value == "":
                continue
            if overwrite or key not in props or props[key] == "":
                if props.get(key) != value:
                    props[key] = value
                    changed = True

        if not changed:
            return "skipped"

        if make_backup:
            backup_file(path, vault_path)
        path.write_text(write_frontmatter(props, blocks, body), encoding="utf-8")
        return "ok"
    except Exception as exc:
        return f"error:{exc}"


def apply_props_to_file(
    path: Path,
    new_props: dict,
    overwrite: bool = False,
    make_backup: bool = True,
    vault_path: Optional[Path] = None,
) -> str:
    return update_props_in_file(
        path,
        set_props=new_props,
        overwrite=overwrite,
        make_backup=make_backup,
        vault_path=vault_path,
    )


def remove_props_from_file(path: Path, keys: list, make_backup: bool = True, vault_path: Optional[Path] = None) -> str:
    return update_props_in_file(path, remove_keys=keys, make_backup=make_backup, vault_path=vault_path)


def build_note_folder_path_value(vault_path: Path, note_path: Path) -> str:
    vault_root = vault_path.resolve()
    note_file = note_path.resolve()
    parent = note_file.parent
    try:
        rel_parent = parent.relative_to(vault_root)
    except ValueError as exc:
        raise ValueError(f"{note_file} is not inside vault {vault_root}") from exc

    if str(rel_parent) in ("", "."):
        return "Vault 루트"
    return rel_parent.as_posix().replace("/", " / ")


def parse_note_folder_path_value(path_value: str) -> Path:
    raw = str(path_value or "").strip().strip("\"'")
    if not raw:
        raise ValueError("path property is empty")
    if raw.startswith("Vault ") and "/" not in raw:
        return Path()

    if raw in {"Vault 猷⑦듃", "Vault root", "Vault Root", "root", "/"}:
        return Path()

    normalized = raw.replace("\\", "/")
    if normalized.startswith("Vault ") and "/" in normalized:
        normalized = normalized.split("/", 1)[1]
    for prefix in ("Vault 猷⑦듃 / ", "Vault root / ", "Vault Root / "):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break

    normalized = re.sub(r"\s*/\s*", "/", normalized).strip().strip("/")
    if not normalized:
        return Path()

    parts = [part.strip() for part in normalized.split("/") if part.strip()]
    if parts and parts[-1].lower().endswith(".md"):
        parts = parts[:-1]
    if any(part in {".", ".."} for part in parts):
        raise ValueError("path contains relative traversal")
    return Path(*parts)


def resolve_note_target_dir_from_path_value(vault_path: Path, path_value: str) -> Path:
    vault_root = vault_path.resolve()
    rel_dir = parse_note_folder_path_value(path_value)
    target_dir = (vault_root / rel_dir).resolve()
    if target_dir != vault_root and vault_root not in target_dir.parents:
        raise ValueError("path escapes vault root")
    return target_dir


def sync_path_prop_for_file(
    note_path: Path,
    vault_path: Path,
    make_backup: bool = True,
) -> tuple[str, str]:
    path_value = build_note_folder_path_value(vault_path, note_path)
    result = apply_props_to_file(
        note_path,
        {"path": path_value},
        overwrite=True,
        make_backup=make_backup,
        vault_path=vault_path,
    )
    return result, path_value


def normalize_alias_list(value) -> list[str]:
    aliases = normalize_prop_list(value)
    return [alias for alias in aliases if alias]


def merge_aliases(props: dict, aliases: list[str]) -> bool:
    cleaned = []
    seen = set()
    for alias in aliases:
        text = str(alias).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)

    if not cleaned:
        return False

    existing = normalize_alias_list(props.get("aliases"))
    merged = list(existing)
    existing_keys = {item.casefold() for item in existing}
    changed = False

    for alias in cleaned:
        if alias.casefold() not in existing_keys:
            merged.append(alias)
            existing_keys.add(alias.casefold())
            changed = True

    if changed or "aliases" not in props:
        props["aliases"] = merged
    return changed


def iter_link_update_notes(vault_path: Path) -> list[Path]:
    notes = []
    for note_path in vault_path.rglob("*.md"):
        rel_parts = note_path.relative_to(vault_path).parts
        if any(part in LINK_UPDATE_EXCLUDED_PARTS for part in rel_parts):
            continue
        notes.append(note_path)
    return sorted(notes)


def note_title_is_unique(
    vault_path: Path,
    title: str,
    ignore_paths: Optional[set[Path]] = None,
) -> bool:
    ignore = {path.resolve() for path in (ignore_paths or set())}
    matches = 0
    for note_path in iter_link_update_notes(vault_path):
        if note_path.resolve() in ignore:
            continue
        if note_path.stem.casefold() == title.casefold():
            matches += 1
            if matches > 1:
                return False
    return matches <= 1


def split_wikilink_parts(inner: str) -> tuple[str, str, str]:
    alias = ""
    target = inner
    if "|" in target:
        target, alias = target.split("|", 1)
    heading = ""
    if "#" in target:
        target, heading = target.split("#", 1)
    return target, heading, alias


def wikilink_points_to_note(
    source_note: Path,
    raw_target: str,
    old_note_path: Path,
    vault_path: Path,
) -> bool:
    target = raw_target.strip().replace("\\", "/")
    if not target:
        return False

    old_rel = old_note_path.relative_to(vault_path).as_posix()
    old_rel_no_ext = old_rel[:-3] if old_rel.lower().endswith(".md") else old_rel
    normalized = target.lower().strip("/")
    if normalized in {old_rel.lower(), old_rel_no_ext.lower()}:
        return True

    if "/" not in target and Path(target).stem.casefold() == old_note_path.stem.casefold():
        return True

    if target.startswith("/"):
        candidate = (vault_path / target.lstrip("/")).resolve()
    else:
        candidate = (source_note.parent / target).resolve()

    if candidate.suffix == "":
        candidate = candidate.with_suffix(".md")
    return candidate.resolve() == old_note_path.resolve()


def build_replacement_wikilink_base(
    source_note: Path,
    original_base: str,
    old_note_path: Path,
    new_note_path: Path,
    vault_path: Path,
) -> str:
    base = original_base.strip().replace("\\", "/")
    if not base:
        return base

    had_extension = base.lower().endswith(".md")
    uses_path = "/" in base or base.startswith(".")
    old_rel = old_note_path.relative_to(vault_path).as_posix()
    old_rel_no_ext = old_rel[:-3] if old_rel.lower().endswith(".md") else old_rel
    new_rel = new_note_path.relative_to(vault_path).as_posix()
    new_rel_no_ext = new_rel[:-3] if new_rel.lower().endswith(".md") else new_rel

    if uses_path:
        if base.startswith("/"):
            replacement = "/" + new_rel_no_ext
        else:
            replacement = new_rel_no_ext
    else:
        if old_note_path.stem == new_note_path.stem:
            replacement = base
        elif note_title_is_unique(vault_path, new_note_path.stem, {old_note_path.resolve()}):
            replacement = new_note_path.stem
        else:
            replacement = new_rel_no_ext

    if had_extension and not replacement.lower().endswith(".md"):
        replacement += ".md"
    if not had_extension and replacement.lower().endswith(".md"):
        replacement = replacement[:-3]
    return replacement


def replace_wikilinks_for_note_change(
    text: str,
    source_note: Path,
    old_note_path: Path,
    new_note_path: Path,
    vault_path: Path,
) -> tuple[str, int]:
    replacements = 0

    def repl(match):
        nonlocal replacements
        inner = match.group(1)
        base, heading, alias = split_wikilink_parts(inner)
        if not wikilink_points_to_note(source_note, base, old_note_path, vault_path):
            return match.group(0)

        new_base = build_replacement_wikilink_base(
            source_note,
            base,
            old_note_path,
            new_note_path,
            vault_path,
        )
        pieces = [new_base]
        if heading:
            pieces[0] += f"#{heading}"
        if alias:
            pieces[0] += f"|{alias}"
        replacements += 1
        return f"[[{pieces[0]}]]"

    updated = re.sub(r"\[\[([^\]]+)\]\]", repl, text)
    return updated, replacements


def replace_markdown_links_for_note_change(
    text: str,
    source_note: Path,
    old_note_path: Path,
    new_note_path: Path,
    vault_path: Path,
) -> tuple[str, int]:
    replacements = 0

    def repl(match):
        nonlocal replacements
        label = match.group(1)
        raw_target = match.group(2)
        target = raw_target.strip()
        wrapped = target.startswith("<") and target.endswith(">")
        stripped = target.strip("<>")

        fragment = ""
        if "#" in stripped:
            base_part, fragment = stripped.split("#", 1)
            fragment = "#" + fragment
        else:
            base_part = stripped

        if not base_part or base_part.startswith(("http://", "https://", "mailto:", "#")):
            return match.group(0)

        if base_part.startswith("/"):
            candidate = (vault_path / base_part.lstrip("/")).resolve()
            absolute_style = True
        else:
            candidate = (source_note.parent / base_part).resolve()
            absolute_style = False

        if candidate.suffix == "":
            candidate = candidate.with_suffix(".md")
        if candidate.resolve() != old_note_path.resolve():
            return match.group(0)

        had_extension = base_part.lower().endswith(".md")
        if absolute_style:
            new_base = "/" + new_note_path.relative_to(vault_path).as_posix()
        else:
            new_base = os.path.relpath(new_note_path, start=source_note.parent).replace("\\", "/")
        if not had_extension and new_base.lower().endswith(".md"):
            new_base = new_base[:-3]
        if wrapped:
            new_base = f"<{new_base}>"

        replacements += 1
        return f"[{label}]({new_base}{fragment})"

    updated = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", repl, text)
    return updated, replacements


def update_links_for_note_change(
    vault_path: Path,
    old_note_path: Path,
    new_note_path: Path,
) -> dict:
    updated_files = 0
    wikilinks_updated = 0
    markdown_links_updated = 0
    changed_files: list[str] = []

    for note_path in iter_link_update_notes(vault_path):
        if not note_path.exists():
            continue
        original_text = read_text_file(note_path)
        updated_text, wiki_count = replace_wikilinks_for_note_change(
            original_text,
            note_path,
            old_note_path,
            new_note_path,
            vault_path,
        )
        updated_text, md_count = replace_markdown_links_for_note_change(
            updated_text,
            note_path,
            old_note_path,
            new_note_path,
            vault_path,
        )
        if updated_text == original_text:
            continue

        if note_path.resolve() != new_note_path.resolve():
            backup_file(note_path, vault_path)
        note_path.write_text(updated_text, encoding="utf-8")
        updated_files += 1
        wikilinks_updated += wiki_count
        markdown_links_updated += md_count
        changed_files.append(note_path.relative_to(vault_path).as_posix())

    return {
        "updated_files": updated_files,
        "wikilinks_updated": wikilinks_updated,
        "markdown_links_updated": markdown_links_updated,
        "changed_files": changed_files,
    }


def move_note_to_path_prop(
    note_path: Path,
    vault_path: Path,
) -> tuple[str, Optional[Path], str]:
    note_file = note_path.resolve()
    vault_root = vault_path.resolve()

    try:
        props = get_current_props(note_file)
        path_value = props.get("path", "")
        if not path_value:
            return "skipped", note_file, "path 속성이 없습니다."

        target_dir = resolve_note_target_dir_from_path_value(vault_root, str(path_value))
        destination = (target_dir / note_file.name).resolve()
        if destination == note_file:
            sync_result, normalized = sync_path_prop_for_file(
                note_file,
                vault_root,
                make_backup=False,
            )
            if sync_result.startswith("error"):
                return "error", note_file, sync_result
            return "skipped", note_file, f"이미 path 위치에 있습니다. ({normalized})"

        if destination.exists():
            return "conflict", destination, f"대상 파일이 이미 있습니다: {destination}"

        old_note_path = note_file
        backup_file(note_file, vault_root)
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(note_file), str(destination))
        sync_result, normalized = sync_path_prop_for_file(
            destination,
            vault_root,
            make_backup=False,
        )
        if sync_result.startswith("error"):
            return "error", destination, sync_result
        link_result = update_links_for_note_change(vault_root, old_note_path, destination)
        detail = (
            f"{normalized}; links updated: {link_result['updated_files']} files "
            f"(wikilinks {link_result['wikilinks_updated']}, markdown {link_result['markdown_links_updated']})"
        )
        return "moved", destination, detail
    except Exception as exc:
        return "error", None, str(exc)


def restore_backup(path: Path, vault_path: Optional[Path] = None) -> str:
    baks = []
    
    # Check external first
    if vault_path:
        try:
            rel = path.parent.relative_to(vault_path.resolve())
            ext_bak_dir = DEFAULT_BACKUP_ROOT / rel
        except ValueError:
            ext_bak_dir = DEFAULT_BACKUP_ROOT / path.parent.name
    else:
        ext_bak_dir = DEFAULT_BACKUP_ROOT / path.parent.name
        
    if ext_bak_dir.exists():
        baks.extend(ext_bak_dir.glob(f"{path.stem}_*{path.suffix}.bak"))
        
    # Check legacy
    legacy_bak_dir = path.parent / "_PKM_BACKUP"
    if legacy_bak_dir.exists():
        baks.extend(legacy_bak_dir.glob(f"{path.stem}_*{path.suffix}.bak"))
        
    if not baks:
        return "no_backup"
        
    baks.sort(key=lambda p: p.name)
    latest = baks[-1]
    shutil.copy2(latest, path)
    return f"restored:{latest.name}"


def get_current_props(path: Path) -> dict:
    try:
        text = read_text_file(path)
        props, _, _ = read_frontmatter(text)
        return props
    except Exception:
        return {}


def match_index(stem: str) -> dict:
    stem_lower = stem.lower()
    for key, value in INDEX_MAPPING.items():
        if key.lower() == stem_lower:
            return value

    normalized_stem = re.sub(r"[\s\-_]+", "", stem_lower)
    for key, value in INDEX_MAPPING.items():
        normalized_key = re.sub(r"[\s\-_]+", "", key.lower())
        if normalized_key == normalized_stem:
            return value

    # 부분 일치는 너무 짧은 제목에서 오매칭이 심하므로
    # 충분히 긴 경우에만 좁게 허용한다.
    for key, value in INDEX_MAPPING.items():
        key_lower = key.lower()
        normalized_key = re.sub(r"[\s\-_]+", "", key_lower)
        if len(normalized_stem) < 6 or len(normalized_key) < 6:
            continue
        if normalized_key in normalized_stem or normalized_stem in normalized_key:
            return value
    return {}


def search_in_content(files: list, query: str) -> list:
    query_lower = query.lower()
    result = []
    for file_path in files:
        try:
            text = read_text_file(file_path).lower()
            if query_lower in text:
                result.append(file_path)
        except Exception:
            pass
    return result


def parse_obsidian_paths(text: str, vault_path: Path) -> tuple[list, list]:
    found = []
    not_found = []
    for raw_line in text.strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = line.replace("\\", "/")
        if not line.endswith(".md"):
            line += ".md"
        candidate = vault_path / line
        if candidate.exists():
            found.append(candidate)
        else:
            stem = Path(line).stem
            matches = [file_path for file_path in vault_path.rglob("*.md") if file_path.stem == stem]
            if len(matches) == 1:
                found.append(matches[0])
            elif len(matches) > 1:
                best = min(matches, key=lambda file_path: len(str(file_path)))
                found.append(best)
            else:
                not_found.append(raw_line)
    return found, not_found


def generate_index_snapshot(vault_path: Path) -> str:
    """
    vault 전체 md 파일의 frontmatter를 읽어
    AI가 읽을 수 있는 정적 인덱스 마크다운을 생성한다.
    """
    rows = []
    files = [
        file_path
        for file_path in vault_path.rglob("*.md")
        if not any(part in INDEX_SNAPSHOT_EXCLUDED_PARTS for part in file_path.parts)
    ]

    for file_path in sorted(files):
        props = get_current_props(file_path)
        if not props:
            continue

        domain = normalize_domain_value(props.get("domain", "")) if props.get("domain", "") else ""
        engine = props.get("engine", "")
        topic = props.get("topic", "")
        if not any([domain, engine, topic]):
            continue

        rel = file_path.relative_to(vault_path).as_posix()
        rows.append(
            "| {title} | {domain} | {engine} | {topic} | {path} |".format(
                title=escape_markdown_cell(file_path.stem),
                domain=escape_markdown_cell(domain),
                engine=escape_markdown_cell(engine),
                topic=escape_markdown_cell(format_yaml_value(topic) if topic else ""),
                path=escape_markdown_cell(rel),
            )
        )

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = [
        f"# PKM Index (스냅샷 {ts})",
        "",
        "> AI 연결 제안용 정적 인덱스. Dataview 결과를 값붙여넣기한 마크다운 버전.",
        "",
        f"- source vault: `{vault_path.as_posix()}`",
        f"- indexed notes: `{len(rows)}`",
        "",
        "| 제목 | domain | engine | topic | 경로 |",
        "|------|--------|--------|-------|------|",
    ]
    return "\n".join(header + rows) + "\n"


def iter_relation_source_notes(vault_path: Path) -> list[Path]:
    note_paths = []
    for file_path in vault_path.rglob("*.md"):
        if any(part in INDEX_SNAPSHOT_EXCLUDED_PARTS for part in file_path.parts):
            continue
        rel_parts = file_path.relative_to(vault_path).parts
        if not rel_parts:
            continue
        top = rel_parts[0]
        if any(top.startswith(prefix) for prefix in RELATION_EXCLUDED_PREFIXES):
            continue
        if top in RELATION_INCLUDED_TOP_LEVEL or any(top.startswith(prefix) for prefix in RELATION_INCLUDED_PREFIXES):
            note_paths.append(file_path)
            continue
        props = get_current_props(file_path)
        if props.get("domain") or props.get("engine") or props.get("topic"):
            note_paths.append(file_path)
    return sorted(note_paths)


def extract_wikilink_targets(text: str) -> list[str]:
    matches = re.findall(r"\[\[([^\]]+)\]\]", text)
    targets = []
    for match in matches:
        target = match.split("|", 1)[0].split("#", 1)[0].strip()
        if target:
            targets.append(target.replace("\\", "/"))
    return targets


def extract_markdown_targets(text: str) -> list[str]:
    return re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)


def build_note_lookup(note_paths: list[Path], vault_path: Path) -> dict:
    rel_with_ext = {}
    rel_no_ext = {}
    stem_map = {}

    for note_path in note_paths:
        rel = note_path.relative_to(vault_path).as_posix()
        rel_key = rel.lower()
        rel_with_ext[rel_key] = note_path
        if rel_key.endswith(".md"):
            rel_no_ext[rel_key[:-3]] = note_path

        stem_key = note_path.stem.lower()
        stem_map.setdefault(stem_key, []).append(note_path)

    unique_stems = {
        stem: paths[0]
        for stem, paths in stem_map.items()
        if len(paths) == 1
    }

    return {
        "rel_with_ext": rel_with_ext,
        "rel_no_ext": rel_no_ext,
        "unique_stems": unique_stems,
        "note_set": {path.resolve() for path in note_paths},
    }


def resolve_wikilink_target(
    source_path: Path,
    raw_target: str,
    vault_path: Path,
    lookup: dict,
) -> Optional[Path]:
    target = raw_target.strip().replace("\\", "/")
    if not target:
        return None

    normalized = target.lower()
    if normalized in lookup["rel_with_ext"]:
        return lookup["rel_with_ext"][normalized]
    if normalized in lookup["rel_no_ext"]:
        return lookup["rel_no_ext"][normalized]

    relative_candidate = (source_path.parent / target).resolve()
    if relative_candidate.suffix == "":
        relative_candidate = relative_candidate.with_suffix(".md")
    if relative_candidate.resolve() in lookup["note_set"]:
        return relative_candidate

    absolute_candidate = (vault_path / target).resolve()
    if absolute_candidate.suffix == "":
        absolute_candidate = absolute_candidate.with_suffix(".md")
    if absolute_candidate.resolve() in lookup["note_set"]:
        return absolute_candidate

    stem_key = Path(target).stem.lower()
    return lookup["unique_stems"].get(stem_key)


def resolve_markdown_target(
    source_path: Path,
    raw_target: str,
    vault_path: Path,
    lookup: dict,
) -> Optional[Path]:
    target = raw_target.strip().strip("<>").split("#", 1)[0].strip()
    if not target or target.startswith(("http://", "https://", "mailto:", "#")):
        return None

    if target.startswith("/"):
        candidate = (vault_path / target.lstrip("/")).resolve()
    else:
        candidate = (source_path.parent / target).resolve()

    if candidate.suffix == "":
        candidate = candidate.with_suffix(".md")

    if candidate.resolve() in lookup["note_set"]:
        return candidate
    return None


def score_note_relation(source_meta: dict, target_meta: dict) -> tuple[int, list[str]]:
    reasons = []
    score = 0

    shared_topics = sorted(set(source_meta["topics"]) & set(target_meta["topics"]))
    shared_tags = sorted(set(source_meta["tags"]) & set(target_meta["tags"]))
    if shared_topics:
        score += 3 * len(shared_topics)
        reasons.append(f"shared topic: {', '.join(shared_topics[:3])}")
    if shared_tags:
        score += 2 * len(shared_tags)
        reasons.append(f"shared tag: {', '.join(shared_tags[:3])}")
    if source_meta["domain"] and source_meta["domain"] == target_meta["domain"]:
        score += 1
        reasons.append(f"same domain: {source_meta['domain']}")
    if source_meta["engine"] and source_meta["engine"] == target_meta["engine"]:
        score += 1
        reasons.append(f"same engine: {source_meta['engine']}")

    return score, reasons


def format_related_note_line(target_meta: dict, reason: Optional[str] = None, prefix: str = "") -> str:
    suffix = f" — {reason}" if reason else ""
    return (
        f"- {prefix}[{target_meta['title']}](./{target_meta['page_name']})"
        f" `{target_meta['rel_path']}`{suffix}"
    )


def render_note_relation_page(meta: dict) -> str:
    props_block = [
        f"- source: `{meta['rel_path']}`",
        f"- domain: `{meta['domain']}`" if meta["domain"] else "- domain: ``",
        f"- engine: `{meta['engine']}`" if meta["engine"] else "- engine: ``",
        f"- topic: `{format_yaml_value(meta['topics'])}`" if meta["topics"] else "- topic: `[]`",
        f"- type: `{format_yaml_value(meta['type_value'])}`" if meta["type_value"] else "- type: ``",
        f"- tags: `{format_yaml_value(meta['tags'])}`" if meta["tags"] else "- tags: `[]`",
    ]

    sections = [
        f"# {meta['title']}",
        "",
        *props_block,
        "",
        "## Direct Links",
    ]
    sections.extend(meta["direct_links"] or ["- 없음"])
    sections.extend(["", "## Backlinks"])
    sections.extend(meta["backlinks"] or ["- 없음"])
    sections.extend(["", "## Related Notes"])
    sections.extend(meta["related_notes"] or ["- 없음"])
    if meta["unresolved_links"]:
        sections.extend(["", "## Unresolved Links"])
        sections.extend(f"- `{item}`" for item in meta["unresolved_links"])
    return "\n".join(sections) + "\n"


def generate_relations_wiki(vault_path: Path) -> dict:
    note_paths = iter_relation_source_notes(vault_path)
    lookup = build_note_lookup(note_paths, vault_path)

    wiki_dir = Path("G:/내 드라이브/knowledge/pkm_wiki").resolve()
    notes_dir = wiki_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    note_meta = {}
    backlinks = {}
    total_explicit_links = 0

    for note_path in note_paths:
        rel_path = note_path.relative_to(vault_path).as_posix()
        page_name = slugify_note_path(rel_path)
        props = get_current_props(note_path)
        raw_text = read_text_file(note_path)

        domain_value = [normalize_domain_value(item) for item in normalize_prop_list(props.get("domain"))]
        engine_value = normalize_prop_list(props.get("engine"))
        topics = normalize_prop_list(props.get("topic"))
        tags = normalize_prop_list(props.get("tags"))
        direct_targets = []
        unresolved = []

        for target in extract_wikilink_targets(raw_text):
            resolved = resolve_wikilink_target(note_path, target, vault_path, lookup)
            if resolved:
                direct_targets.append(resolved)
            else:
                unresolved.append(target)

        for target in extract_markdown_targets(raw_text):
            resolved = resolve_markdown_target(note_path, target, vault_path, lookup)
            if resolved:
                direct_targets.append(resolved)

        unique_targets = []
        seen_targets = set()
        for target in direct_targets:
            rel_target = target.relative_to(vault_path).as_posix()
            if rel_target not in seen_targets:
                seen_targets.add(rel_target)
                unique_targets.append(rel_target)
                backlinks.setdefault(rel_target, set()).add(rel_path)

        total_explicit_links += len(unique_targets)

        note_meta[rel_path] = {
            "title": note_path.stem,
            "rel_path": rel_path,
            "page_name": page_name,
            "domain": domain_value[0] if domain_value else "",
            "engine": engine_value[0] if engine_value else "",
            "topics": topics,
            "tags": tags,
            "type_value": props.get("type", ""),
            "targets": unique_targets,
            "unresolved_links": sorted(set(unresolved)),
        }

    for meta in note_meta.values():
        meta["direct_links"] = [
            format_related_note_line(note_meta[target_rel])
            for target_rel in meta["targets"]
            if target_rel in note_meta
        ]
        meta["backlinks"] = [
            format_related_note_line(note_meta[source_rel])
            for source_rel in sorted(backlinks.get(meta["rel_path"], set()))
            if source_rel in note_meta
        ]

        related_candidates = []
        for other_rel, other_meta in note_meta.items():
            if other_rel == meta["rel_path"]:
                continue
            score, reasons = score_note_relation(meta, other_meta)
            if score <= 0:
                continue
            related_candidates.append((score, other_meta["title"].lower(), other_rel, reasons))

        related_candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        meta["related_notes"] = [
            format_related_note_line(
                note_meta[other_rel],
                reason="; ".join(reasons),
            )
            for _, _, other_rel, reasons in related_candidates[:8]
        ]

        page_path = notes_dir / meta["page_name"]
        page_path.write_text(render_note_relation_page(meta), encoding="utf-8")

    domain_counts = {}
    for meta in note_meta.values():
        domain = meta["domain"] or "(미분류)"
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    ranked = sorted(
        note_meta.values(),
        key=lambda item: (
            -(len(item["targets"]) + len(backlinks.get(item["rel_path"], set()))),
            item["title"].lower(),
        ),
    )

    index_lines = [
        f"# PKM Relations Wiki ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
        "",
        "> AI가 읽을 수 있는 정적 파일 관계 위키. 직접 링크, 백링크, 공통 topic/tag/domain을 함께 기록한다.",
        "",
        f"- source vault: `{vault_path.as_posix()}`",
        f"- notes: `{len(note_meta)}`",
        f"- explicit links: `{total_explicit_links}`",
        "",
        "## Domain Counts",
    ]
    for domain, count in sorted(domain_counts.items(), key=lambda item: (-item[1], item[0])):
        index_lines.append(f"- `{domain}`: {count}")

    index_lines.extend(["", "## High-Connection Notes"])
    for meta in ranked[:20]:
        link_count = len(meta["targets"])
        backlink_count = len(backlinks.get(meta["rel_path"], set()))
        index_lines.append(
            f"- [{meta['title']}](notes/{meta['page_name']}) `{meta['rel_path']}`"
            f" — out {link_count}, in {backlink_count}"
        )

    index_lines.extend(["", "## All Notes"])
    for meta in sorted(note_meta.values(), key=lambda item: item["rel_path"].lower()):
        topic_text = format_yaml_value(meta["topics"]) if meta["topics"] else "[]"
        index_lines.append(
            f"- [{meta['title']}](notes/{meta['page_name']})"
            f" `{meta['rel_path']}` — {meta['domain'] or '-'} / {meta['engine'] or '-'} / {topic_text}"
        )

    index_path = wiki_dir / "INDEX.md"
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    return {
        "wiki_dir": wiki_dir,
        "index_path": index_path,
        "note_count": len(note_meta),
        "explicit_links": total_explicit_links,
        "page_count": len(note_meta) + 1,
    }
