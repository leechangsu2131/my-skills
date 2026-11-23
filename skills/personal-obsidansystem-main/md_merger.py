#!/usr/bin/env python3
"""
NotebookLM-friendly markdown bundler.

Goals:
1. Exclude generated/system files such as backups, reports, and relation wiki outputs.
2. Reduce the total file count to the target count or lower.
3. Keep every output file under NotebookLM-friendly limits.

The script uses lightweight title/content/size heuristics and prefers merging
within the same folder so that nearby notes stay together.
"""

from __future__ import annotations

import argparse
import fnmatch
import logging
import math
import re
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(next(p / "_shared" for p in Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir  # 결과물(노트 내용 포함)은 저장소 밖 <내 문서>\my-skills-data 에 둔다

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    np = None
    TfidfVectorizer = None
    cosine_similarity = None
    HAS_SKLEARN = False

try:
    from rapidfuzz.fuzz import ratio as rapidfuzz_ratio
    HAS_RAPIDFUZZ = True
except ImportError:
    rapidfuzz_ratio = None
    HAS_RAPIDFUZZ = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None
    HAS_SENTENCE_TRANSFORMERS = False


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


READ_ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")
DEFAULT_TARGET = 299
DEFAULT_MAX_CHARS = 500_000
DEFAULT_MAX_BYTES = 200_000_000

DEFAULT_EXCLUDED_DIRS = {
    "_PKM_BACKUP",
    "knowledge",
    "reports",
    "daily",
    "Clippings",
    ".obsidian",
    ".trash",
    ".space",
    ".makemd",
    ".agent",
    ".llm-wiki",
    ".smart-env",
}

DEFAULT_EXCLUDED_GLOBS = [
    "*.bak",
    "*.excalidraw.md",
    "_merge_report.md",
    "batch_*.md",
    "pkm_index.md",
]

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "over",
    "about", "idea", "ideas", "note", "notes", "memo", "정리", "생각",
    "메모", "노트", "것", "수", "및", "그리고", "에서", "위한", "대한",
}


@dataclass(frozen=True)
class MDFile:
    index: int
    path: Path
    base_dir: Path
    relative_path: Path
    title: str
    raw_content: str
    clean_text: str
    size_bytes: int
    char_count: int
    folder_key: str
    top_level_key: str
    keywords: tuple[str, ...]


@dataclass
class Bundle:
    items: list[MDFile] = field(default_factory=list)
    total_chars: int = 0
    total_bytes: int = 0

    @property
    def folder_key(self) -> str:
        if not self.items:
            return ""
        return self.items[0].folder_key

    @property
    def top_level_key(self) -> str:
        if not self.items:
            return ""
        return self.items[0].top_level_key

    def add(self, md_file: MDFile) -> None:
        self.items.append(md_file)
        self.total_chars += md_file.char_count
        self.total_bytes += md_file.size_bytes

    def representative(self) -> MDFile:
        return max(self.items, key=lambda item: (item.size_bytes, item.char_count, len(item.title)))

    def can_add(self, md_file: MDFile, max_chars: int, max_bytes: int, overhead: int = 4096) -> bool:
        return (
            self.total_chars + md_file.char_count + overhead <= max_chars
            and self.total_bytes + md_file.size_bytes + overhead <= max_bytes
        )


@dataclass
class SimilarityContext:
    engine: str
    matrix: list[list[float]]


def read_text(path: Path) -> str:
    last_error: Exception | None = None
    for encoding in READ_ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
        except OSError as exc:
            last_error = exc
            break
    if last_error:
        logger.warning("파일 읽기 실패: %s (%s)", path, last_error)
    return ""


def extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = re.sub(r"^#+\s*", "", stripped).strip()
            if title:
                return title
    return fallback


def clean_content(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[\[\]{}()#*_~>|-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def remove_h1(content: str) -> str:
    lines = content.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.strip().startswith("# "):
            return "".join(lines[:index] + lines[index + 1 :])
    return content


def slugify(text: str) -> str:
    value = text.lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_-]+", "-", value)
    return value.strip(" -") or "section"


def sanitize_filename(text: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", text).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(". ")
    if len(cleaned) > 180:
        cleaned = cleaned[:180].rstrip(" ._")
    return cleaned or "merged"


def quote_yaml_string(value: str) -> str:
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def split_frontmatter(content: str) -> tuple[list[str], str]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", content, re.DOTALL)
    if not match:
        return [], content
    raw = match.group(1)
    body = content[match.end():]
    return raw.splitlines(), body


def inject_frontmatter_props(content: str, new_props: dict[str, str]) -> str:
    if not new_props:
        return content

    lines, body = split_frontmatter(content)
    replaced_keys = set(new_props.keys())
    preserved: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r"^([\w가-힣]+)\s*:\s*(.*)$", line)
        if match and match.group(1) in replaced_keys:
            i += 1
            while i < len(lines) and re.match(r"^\s+-\s", lines[i]):
                i += 1
            continue
        preserved.append(line)
        i += 1

    for key, value in new_props.items():
        preserved.append(f"{key}: {quote_yaml_string(value)}")

    frontmatter = "---\n" + "\n".join(preserved) + "\n---\n"
    return frontmatter + body


def extract_keywords(title: str, clean_text: str, limit: int = 8) -> tuple[str, ...]:
    tokens = re.findall(r"[0-9A-Za-z가-힣]{2,}", f"{title} {clean_text[:2000]}")
    counter = Counter(token.lower() for token in tokens if token.lower() not in STOPWORDS)
    return tuple(token for token, _ in counter.most_common(limit))


def jaccard_similarity(tokens_a: tuple[str, ...], tokens_b: tuple[str, ...]) -> float:
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def title_similarity(a: str, b: str) -> float:
    if HAS_RAPIDFUZZ:
        return rapidfuzz_ratio(a.lower(), b.lower()) / 100.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def content_similarity(a: MDFile, b: MDFile) -> float:
    if a.clean_text and b.clean_text:
        snippet_a = a.clean_text[:1000]
        snippet_b = b.clean_text[:1000]
        ratio = SequenceMatcher(None, snippet_a, snippet_b).ratio()
    else:
        ratio = 0.0
    keyword_score = jaccard_similarity(a.keywords, b.keywords)
    return max(ratio, keyword_score)


def size_similarity(size_a: int, size_b: int) -> float:
    if size_a <= 0 and size_b <= 0:
        return 1.0
    max_size = max(size_a, size_b, 1)
    return max(0.0, 1.0 - abs(size_a - size_b) / max_size)


def file_similarity(a: MDFile, b: MDFile, weights: dict[str, float]) -> float:
    base = (
        weights["title"] * title_similarity(a.title, b.title)
        + weights["content"] * content_similarity(a, b)
        + weights["size"] * size_similarity(a.size_bytes, b.size_bytes)
    )
    if a.folder_key == b.folder_key:
        base += 0.08
    elif a.top_level_key == b.top_level_key:
        base += 0.03
    return base


def average_similarity(bundle: Bundle, md_file: MDFile, sim_context: SimilarityContext) -> float:
    if not bundle.items:
        return 0.0
    sample = bundle.items[: min(4, len(bundle.items))]
    scores = [sim_context.matrix[item.index][md_file.index] for item in sample]
    return sum(scores) / len(scores)


def build_zero_matrix(n: int) -> list[list[float]]:
    return [[0.0 for _ in range(n)] for _ in range(n)]


def compute_base_title_matrix(md_files: list[MDFile]) -> list[list[float]]:
    n = len(md_files)
    matrix = build_zero_matrix(n)
    for i in range(n):
        matrix[i][i] = 1.0
        for j in range(i + 1, n):
            score = title_similarity(md_files[i].title, md_files[j].title)
            matrix[i][j] = score
            matrix[j][i] = score
    return matrix


def compute_size_matrix(md_files: list[MDFile]) -> list[list[float]]:
    n = len(md_files)
    matrix = build_zero_matrix(n)
    for i in range(n):
        matrix[i][i] = 1.0
        for j in range(i + 1, n):
            score = size_similarity(md_files[i].size_bytes, md_files[j].size_bytes)
            matrix[i][j] = score
            matrix[j][i] = score
    return matrix


def compute_heuristic_content_matrix(md_files: list[MDFile]) -> list[list[float]]:
    n = len(md_files)
    matrix = build_zero_matrix(n)
    for i in range(n):
        matrix[i][i] = 1.0
        for j in range(i + 1, n):
            score = content_similarity(md_files[i], md_files[j])
            matrix[i][j] = score
            matrix[j][i] = score
    return matrix


def compute_tfidf_content_matrix(md_files: list[MDFile]) -> list[list[float]]:
    if not HAS_SKLEARN:
        raise RuntimeError("TF-IDF 모드를 쓰려면 numpy와 scikit-learn이 필요합니다.")
    texts = [
        f"{md_file.title}\n\n{md_file.clean_text[:4000] if md_file.clean_text else md_file.raw_content[:4000]}"
        for md_file in md_files
    ]
    vectorizer = TfidfVectorizer(max_features=12000, ngram_range=(1, 2), min_df=1)
    tfidf = vectorizer.fit_transform(texts)
    sim = cosine_similarity(tfidf)
    return sim.tolist()


def compute_embedding_content_matrix(md_files: list[MDFile], model_name: str) -> list[list[float]]:
    if not HAS_SENTENCE_TRANSFORMERS:
        raise RuntimeError("embedding 모드를 쓰려면 sentence-transformers가 필요합니다.")
    model = SentenceTransformer(model_name)
    texts = [
        f"{md_file.title}\n\n{md_file.clean_text[:3000] if md_file.clean_text else md_file.raw_content[:3000]}"
        for md_file in md_files
    ]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    sim = embeddings @ embeddings.T
    if hasattr(sim, "tolist"):
        return sim.tolist()
    return [list(row) for row in sim]


def build_similarity_context(
    md_files: list[MDFile],
    weights: dict[str, float],
    engine: str,
    embedding_model: str,
) -> SimilarityContext:
    if not md_files:
        return SimilarityContext(engine=engine, matrix=[])

    title_matrix = compute_base_title_matrix(md_files)
    size_matrix = compute_size_matrix(md_files)

    resolved_engine = engine
    if engine == "hybrid":
        resolved_engine = "tfidf" if HAS_SKLEARN else "heuristic"

    if resolved_engine == "tfidf":
        content_matrix = compute_tfidf_content_matrix(md_files)
    elif resolved_engine == "embedding":
        content_matrix = compute_embedding_content_matrix(md_files, embedding_model)
    elif resolved_engine == "hybrid-embedding":
        tfidf_matrix = compute_tfidf_content_matrix(md_files) if HAS_SKLEARN else compute_heuristic_content_matrix(md_files)
        embedding_matrix = compute_embedding_content_matrix(md_files, embedding_model)
        n = len(md_files)
        content_matrix = build_zero_matrix(n)
        for i in range(n):
            for j in range(n):
                content_matrix[i][j] = 0.5 * tfidf_matrix[i][j] + 0.5 * embedding_matrix[i][j]
    else:
        resolved_engine = "heuristic"
        content_matrix = compute_heuristic_content_matrix(md_files)

    n = len(md_files)
    matrix = build_zero_matrix(n)
    for i in range(n):
        matrix[i][i] = 1.0
        for j in range(i + 1, n):
            base = (
                weights["title"] * title_matrix[i][j]
                + weights["content"] * content_matrix[i][j]
                + weights["size"] * size_matrix[i][j]
            )
            if md_files[i].folder_key == md_files[j].folder_key:
                base += 0.08
            elif md_files[i].top_level_key == md_files[j].top_level_key:
                base += 0.03
            score = max(0.0, min(1.0, base))
            matrix[i][j] = score
            matrix[j][i] = score

    return SimilarityContext(engine=resolved_engine, matrix=matrix)


def should_exclude_path(
    relative_path: Path,
    excluded_dirs: set[str],
    excluded_globs: list[str],
) -> bool:
    for part in relative_path.parts:
        if part in excluded_dirs:
            return True
    rel_posix = relative_path.as_posix()
    name = relative_path.name
    for pattern in excluded_globs:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_posix, pattern):
            return True
    return False


def load_md_files(directory: Path, excluded_dirs: set[str], excluded_globs: list[str]) -> list[MDFile]:
    paths = sorted(
        path for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() == ".md"
    )

    md_files: list[MDFile] = []
    skipped = 0
    for index, path in enumerate(paths):
        relative_path = path.relative_to(directory)
        if should_exclude_path(relative_path, excluded_dirs, excluded_globs):
            skipped += 1
            continue

        raw = read_text(path)
        clean = clean_content(raw)
        folder_key = relative_path.parent.as_posix() if str(relative_path.parent) != "." else ""
        top_level_key = relative_path.parts[0] if relative_path.parts else ""
        title = extract_title(raw, path.stem)
        md_files.append(
            MDFile(
                index=len(md_files),
                path=path,
                base_dir=directory,
                relative_path=relative_path,
                title=title,
                raw_content=raw,
                clean_text=clean,
                size_bytes=path.stat().st_size,
                char_count=len(raw),
                folder_key=folder_key,
                top_level_key=top_level_key,
                keywords=extract_keywords(title, clean),
            )
        )

    logger.info("마크다운 파일 %s개 로드, 제외 %s개", len(md_files), skipped)
    return md_files


def allocate_targets_by_folder(folder_groups: dict[str, list[MDFile]], target: int) -> dict[str, int]:
    total_files = sum(len(files) for files in folder_groups.values())
    if total_files <= target:
        return {folder: len(files) for folder, files in folder_groups.items()}

    avg_files_per_output = max(2, math.ceil(total_files / target))
    desired = {
        folder: max(1, math.ceil(len(files) / avg_files_per_output))
        for folder, files in folder_groups.items()
    }

    current_total = sum(desired.values())
    if current_total <= target:
        return desired

    while current_total > target:
        candidates = [
            (len(folder_groups[folder]) / desired_count, len(folder_groups[folder]), folder)
            for folder, desired_count in desired.items()
            if desired_count > 1
        ]
        if not candidates:
            break
        _, _, chosen = max(candidates)
        desired[chosen] -= 1
        current_total -= 1

    return desired


def cluster_folder_files(
    files: list[MDFile],
    desired_outputs: int,
    sim_context: SimilarityContext,
    max_chars: int,
    max_bytes: int,
) -> list[Bundle]:
    if not files:
        return []
    if desired_outputs >= len(files):
        bundles = []
        for md_file in files:
            bundle = Bundle()
            bundle.add(md_file)
            bundles.append(bundle)
        return bundles

    seeds = sorted(files, key=lambda item: (-item.size_bytes, item.title.lower()))[:desired_outputs]
    seed_paths = {seed.path for seed in seeds}
    bundles = []
    for seed in seeds:
        bundle = Bundle()
        bundle.add(seed)
        bundles.append(bundle)

    remaining = [item for item in files if item.path not in seed_paths]
    remaining.sort(key=lambda item: (-item.size_bytes, item.title.lower()))

    for md_file in remaining:
        best_index = None
        best_score = -1.0
        for index, bundle in enumerate(bundles):
            if not bundle.can_add(md_file, max_chars=max_chars, max_bytes=max_bytes):
                continue
            score = average_similarity(bundle, md_file, sim_context)
            if score > best_score:
                best_index = index
                best_score = score

        if best_index is None:
            fallback_index = min(range(len(bundles)), key=lambda idx: bundles[idx].total_chars)
            bundles[fallback_index].add(md_file)
        else:
            bundles[best_index].add(md_file)

    for bundle in bundles:
        bundle.items.sort(key=lambda item: item.title.lower())
    return bundles


def group_and_cluster_files(
    md_files: list[MDFile],
    target: int,
    sim_context: SimilarityContext,
    max_chars: int,
    max_bytes: int,
) -> list[Bundle]:
    folder_groups: dict[str, list[MDFile]] = defaultdict(list)
    for md_file in md_files:
        folder_groups[md_file.folder_key].append(md_file)

    desired_by_folder = allocate_targets_by_folder(folder_groups, target)
    bundles: list[Bundle] = []
    for folder_key in sorted(folder_groups):
        files = folder_groups[folder_key]
        desired_outputs = desired_by_folder.get(folder_key, len(files))
        bundles.extend(
            cluster_folder_files(
                files=files,
                desired_outputs=desired_outputs,
                sim_context=sim_context,
                max_chars=max_chars,
                max_bytes=max_bytes,
            )
        )
    return bundles


def split_large_markdown(content: str, max_chars: int) -> list[str]:
    if len(content) <= max_chars:
        return [content]

    chunks: list[str] = []
    current_lines: list[str] = []
    current_len = 0
    for line in content.splitlines(keepends=True):
        line_len = len(line)
        if current_lines and current_len + line_len > max_chars:
            chunks.append("".join(current_lines))
            current_lines = []
            current_len = 0

        if line_len > max_chars:
            start = 0
            while start < len(line):
                end = min(start + max_chars, len(line))
                part = line[start:end]
                if current_lines:
                    chunks.append("".join(current_lines))
                    current_lines = []
                    current_len = 0
                chunks.append(part)
                start = end
            continue

        current_lines.append(line)
        current_len += line_len

    if current_lines:
        chunks.append("".join(current_lines))
    return chunks


def build_bundle_markdown(bundle: Bundle, mode: str) -> str:
    if len(bundle.items) == 1:
        return bundle.items[0].raw_content

    representative = bundle.representative()
    content_parts: list[str] = []

    if mode == "toc":
        content_parts.append(f"# {representative.title} (외 {len(bundle.items) - 1}개 병합)\n\n")
        content_parts.append("> NotebookLM 업로드용으로 유사한 메모를 한 파일로 묶었습니다.\n\n")
        content_parts.append("## 목차\n")
        for md_file in bundle.items:
            content_parts.append(f"- [{md_file.title}](#{slugify(md_file.title)})\n")
        for md_file in bundle.items:
            content_parts.append(f"\n\n========== [ FILE_SEPARATOR : {md_file.relative_path.as_posix()} ] ==========\n\n")
            content_parts.append(f"## {md_file.title}\n")
            content_parts.append(f"> 원본 파일: `{md_file.relative_path.as_posix()}`\n\n")
            content_parts.append(remove_h1(md_file.raw_content).strip())
        content_parts.append("\n")
    else:
        first = bundle.items[0]
        content_parts.append(first.raw_content.strip())
        for md_file in bundle.items[1:]:
            content_parts.append(f"\n\n========== [ FILE_SEPARATOR : {md_file.relative_path.as_posix()} ] ==========\n\n")
            content_parts.append(f"## {md_file.title}\n")
            content_parts.append(f"> 원본 파일: `{md_file.relative_path.as_posix()}`\n\n")
            content_parts.append(remove_h1(md_file.raw_content).strip())
        content_parts.append("\n")

    return "".join(content_parts)


def split_bundle_if_needed(bundle: Bundle, max_chars: int, max_bytes: int, mode: str) -> list[str]:
    content = build_bundle_markdown(bundle, mode)
    byte_size = len(content.encode("utf-8"))
    if len(content) <= max_chars and byte_size <= max_bytes:
        return [content]

    if len(bundle.items) == 1:
        item = bundle.items[0]
        parts = split_large_markdown(item.raw_content, max_chars)
        return parts

    parts: list[str] = []
    current = Bundle()
    for md_file in bundle.items:
        candidate = Bundle(items=current.items.copy(), total_chars=current.total_chars, total_bytes=current.total_bytes)
        candidate.add(md_file)
        candidate_content = build_bundle_markdown(candidate, mode)
        candidate_bytes = len(candidate_content.encode("utf-8"))
        if current.items and (len(candidate_content) > max_chars or candidate_bytes > max_bytes):
            parts.extend(split_bundle_if_needed(current, max_chars, max_bytes, mode))
            current = Bundle()
            current.add(md_file)
        else:
            current = candidate
    if current.items:
        parts.extend(split_bundle_if_needed(current, max_chars, max_bytes, mode) if len(build_bundle_markdown(current, mode)) > max_chars else [build_bundle_markdown(current, mode)])
    return parts


def bundle_output_base_name(bundle: Bundle) -> str:
    representative = bundle.representative()
    if len(bundle.items) == 1:
        return sanitize_filename(representative.path.stem)
    folder_name = Path(bundle.folder_key).name if bundle.folder_key else representative.path.stem
    return sanitize_filename(folder_name or representative.path.stem)


def bundle_path_value(bundle: Bundle) -> str:
    if bundle.folder_key:
        return bundle.folder_key.replace("/", " / ")
    return "Vault 루트"


def build_output_content(bundle: Bundle, content: str, inject_path_frontmatter: bool) -> str:
    if not inject_path_frontmatter:
        return content
    return inject_frontmatter_props(content, {"path": bundle_path_value(bundle)})


def build_flat_bundle_filename(bundle: Bundle, part_index: int, total_parts: int) -> str:
    if len(bundle.items) == 1:
        relative_stem = bundle.items[0].relative_path.with_suffix("").as_posix()
        base = sanitize_filename(relative_stem.replace("/", "__"))
    else:
        folder_basis = bundle.folder_key or bundle.representative().relative_path.with_suffix("").as_posix()
        base = sanitize_filename(folder_basis.replace("/", "__"))
    if total_parts > 1:
        base = f"{base}__part_{part_index:02d}"
    return f"{base}.md"


def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def write_bundle_outputs(
    bundles: list[Bundle],
    output_dir: Path,
    max_chars: int,
    max_bytes: int,
    mode: str,
    flatten_output: bool,
    inject_path_frontmatter: bool,
) -> list[tuple[Bundle, list[Path]]]:
    bundle_outputs: list[tuple[Bundle, list[Path]]] = []

    for bundle in bundles:
        written_paths: list[Path] = []
        if len(bundle.items) == 1:
            md_file = bundle.items[0]
            parts = split_bundle_if_needed(bundle, max_chars=max_chars, max_bytes=max_bytes, mode=mode)
        else:
            parts = split_bundle_if_needed(bundle, max_chars=max_chars, max_bytes=max_bytes, mode=mode)

        for part_index, content in enumerate(parts, start=1):
            final_content = build_output_content(bundle, content, inject_path_frontmatter=inject_path_frontmatter)
            if len(final_content) > max_chars or len(final_content.encode("utf-8")) > max_bytes:
                raise RuntimeError(
                    f"출력 제한을 넘는 번들이 있습니다: {bundle.representative().relative_path.as_posix()}"
                )

            if flatten_output:
                destination = ensure_unique_path(
                    output_dir / build_flat_bundle_filename(bundle, part_index=part_index, total_parts=len(parts))
                )
            else:
                folder_path = output_dir / bundle.folder_key if bundle.folder_key else output_dir
                folder_path.mkdir(parents=True, exist_ok=True)
                base_name = bundle_output_base_name(bundle)
                suffix = f"__bundle_{part_index:02d}" if len(parts) > 1 else ""
                destination = ensure_unique_path(folder_path / f"{base_name}{suffix}.md")

            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(final_content, encoding="utf-8")
            written_paths.append(destination)

        bundle_outputs.append((bundle, written_paths))

    return bundle_outputs


def generate_report(
    md_files: list[MDFile],
    output_dir: Path,
    bundle_outputs: list[tuple[Bundle, list[Path]]],
    excluded_dirs: set[str],
    excluded_globs: list[str],
    max_chars: int,
    max_bytes: int,
    flatten_output: bool,
    inject_path_frontmatter: bool,
) -> None:
    report_path = output_dir / "_merge_report.md"
    total_chars = sum(item.char_count for item in md_files)
    written_paths = [path for _, paths in bundle_outputs for path in paths]
    lines = [
        "# NotebookLM 업로드용 병합 리포트\n\n",
        f"- 작업 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"- 입력 파일 수: {len(md_files)}\n",
        f"- 출력 파일 수: {len(written_paths)}\n",
        f"- 총 문자 수: {total_chars}\n",
        f"- 최대 문자 제한: {max_chars}\n",
        f"- 최대 바이트 제한: {max_bytes}\n",
        f"- 출력 평탄화: {'예' if flatten_output else '아니오'}\n",
        f"- path frontmatter 삽입: {'예' if inject_path_frontmatter else '아니오'}\n",
        f"- 제외 디렉터리: {', '.join(sorted(excluded_dirs))}\n",
        f"- 제외 패턴: {', '.join(excluded_globs)}\n\n",
        "## 출력 파일 목록\n\n",
        "| 출력 파일 | 포함 원본 수 | 포함 원본 |\n",
        "| :--- | ---: | :--- |\n",
    ]

    for bundle, outputs in bundle_outputs:
        originals = ", ".join(f"`{item.relative_path.as_posix()}`" for item in bundle.items)
        for written in outputs:
            try:
                rel = written.relative_to(output_dir).as_posix()
            except ValueError:
                rel = written.name
            lines.append(f"| `{rel}` | {len(bundle.items)} | {originals} |\n")

    report_path.write_text("".join(lines), encoding="utf-8")
    logger.info("리포트 생성: %s", report_path)


def prepare_output_dir(output_dir: Path, replace_output: bool) -> None:
    if output_dir.exists():
        if any(output_dir.iterdir()):
            if not replace_output:
                raise RuntimeError(
                    f"출력 폴더가 이미 존재하고 비어 있지 않습니다: {output_dir}\n"
                    "안전하게 새 폴더를 지정하거나 --replace-output을 사용하세요."
                )
            shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NotebookLM 업로드용 마크다운 병합기",
        epilog=(
            "예시:\n"
            "  python md_merger.py \"<볼트 경로>\"\n"
            "  python md_merger.py \"<볼트 경로>\" --replace-output --flatten-output\n"
            "  python md_merger.py \"<볼트 경로>\" --similarity-engine tfidf --dry-run"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("input", nargs="?", help="입력 디렉터리")
    parser.add_argument("output", nargs="?", help="출력 디렉터리 (생략 시 <내 문서>\\my-skills-data\\personal-obsidansystem-main\\notebooklm_bundle_TIMESTAMP)")
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET, help=f"목표 파일 개수 (기본: {DEFAULT_TARGET})")
    parser.add_argument("--mode", choices=["toc", "append"], default="toc", help="병합 모드")
    parser.add_argument(
        "--similarity-engine",
        choices=["heuristic", "tfidf", "hybrid", "embedding", "hybrid-embedding"],
        default="hybrid",
        help="유사도 엔진 (기본: hybrid)",
    )
    parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        help="embedding 엔진에서 사용할 모델명",
    )
    parser.add_argument("--w-title", type=float, default=0.45, help="제목 유사도 가중치")
    parser.add_argument("--w-content", type=float, default=0.45, help="내용 유사도 가중치")
    parser.add_argument("--w-size", type=float, default=0.10, help="용량 유사도 가중치")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS, help=f"출력 파일 최대 문자 수 (기본: {DEFAULT_MAX_CHARS})")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help=f"출력 파일 최대 바이트 수 (기본: {DEFAULT_MAX_BYTES})")
    parser.add_argument("--exclude-dir", action="append", default=[], help="추가 제외 디렉터리명")
    parser.add_argument("--exclude-glob", action="append", default=[], help="추가 제외 파일 패턴")
    parser.add_argument("--flatten-output", action="store_true", help="출력 파일을 하위 폴더 없이 한 폴더에 평평하게 저장")
    parser.add_argument("--inject-path-frontmatter", action="store_true", help="출력 파일 맨 위에 path YAML 속성 추가")
    parser.add_argument("--replace-output", action="store_true", help="출력 폴더가 이미 있으면 삭제 후 재생성")
    parser.add_argument("--dry-run", action="store_true", help="실제 파일을 쓰지 않고 예상 결과만 계산")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.input:
        print("입력 폴더가 필요합니다.\n", file=sys.stderr)
        print("예시:", file=sys.stderr)
        print('  python md_merger.py "<볼트 경로>"', file=sys.stderr)
        return 2

    input_dir = Path(args.input).expanduser().resolve()
    if args.output:
        output_dir = Path(args.output).expanduser().resolve()
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = (data_dir() / f"notebooklm_bundle_{timestamp}").resolve()

    if not input_dir.is_dir():
        logger.error("입력 디렉터리가 존재하지 않습니다: %s", input_dir)
        return 1

    excluded_dirs = set(DEFAULT_EXCLUDED_DIRS) | set(args.exclude_dir)
    excluded_globs = list(DEFAULT_EXCLUDED_GLOBS) + list(args.exclude_glob)
    inject_path_frontmatter = args.inject_path_frontmatter or args.flatten_output

    weights = {
        "title": args.w_title,
        "content": args.w_content,
        "size": args.w_size,
    }

    if args.similarity_engine in {"tfidf", "hybrid", "hybrid-embedding"} and not HAS_SKLEARN:
        if args.similarity_engine == "tfidf":
            logger.error("tfidf 모드를 쓰려면 numpy와 scikit-learn이 필요합니다.")
            return 1
        logger.warning("numpy/scikit-learn이 없어 %s 모드 일부를 사용할 수 없습니다. 휴리스틱으로 보완합니다.", args.similarity_engine)

    if args.similarity_engine in {"embedding", "hybrid-embedding"} and not HAS_SENTENCE_TRANSFORMERS:
        logger.error("embedding 계열 모드를 쓰려면 sentence-transformers가 필요합니다.")
        return 1

    logger.info(
        "유사도 엔진 요청: %s (sklearn=%s, rapidfuzz=%s, sentence-transformers=%s)",
        args.similarity_engine,
        "yes" if HAS_SKLEARN else "no",
        "yes" if HAS_RAPIDFUZZ else "no",
        "yes" if HAS_SENTENCE_TRANSFORMERS else "no",
    )
    logger.info(
        "출력 옵션: flatten=%s, inject_path_frontmatter=%s",
        "yes" if args.flatten_output else "no",
        "yes" if inject_path_frontmatter else "no",
    )

    md_files = load_md_files(input_dir, excluded_dirs=excluded_dirs, excluded_globs=excluded_globs)
    if not md_files:
        logger.warning("처리할 마크다운 파일이 없습니다.")
        return 0

    oversized = [md_file for md_file in md_files if md_file.char_count > args.max_chars]
    if oversized:
        logger.warning("단일 파일 기준을 넘는 파일 %s개는 자동 분할됩니다.", len(oversized))
        for md_file in oversized[:10]:
            logger.warning(" - %s (%s chars)", md_file.relative_path.as_posix(), md_file.char_count)

    sim_context = build_similarity_context(
        md_files=md_files,
        weights=weights,
        engine=args.similarity_engine,
        embedding_model=args.embedding_model,
    )
    logger.info("실제 유사도 엔진: %s", sim_context.engine)

    bundles = group_and_cluster_files(
        md_files=md_files,
        target=args.target,
        sim_context=sim_context,
        max_chars=args.max_chars,
        max_bytes=args.max_bytes,
    )

    estimated_outputs = 0
    for bundle in bundles:
        estimated_outputs += len(split_bundle_if_needed(bundle, args.max_chars, args.max_bytes, args.mode))

    logger.info("예상 출력 파일 수: %s", estimated_outputs)
    if estimated_outputs > args.target:
        logger.warning(
            "예상 출력 파일 수가 목표(%s)를 초과합니다. 일부 폴더는 파일 수가 너무 적어 더 줄이기 어렵거나, 큰 단일 파일 분할이 필요합니다.",
            args.target,
        )

    if args.dry_run:
        logger.info("dry-run이므로 파일을 쓰지 않습니다.")
        return 0

    try:
        prepare_output_dir(output_dir, replace_output=args.replace_output)
    except RuntimeError as exc:
        logger.error(str(exc))
        return 1

    bundle_outputs = write_bundle_outputs(
        bundles=bundles,
        output_dir=output_dir,
        max_chars=args.max_chars,
        max_bytes=args.max_bytes,
        mode=args.mode,
        flatten_output=args.flatten_output,
        inject_path_frontmatter=inject_path_frontmatter,
    )
    generate_report(
        md_files=md_files,
        output_dir=output_dir,
        bundle_outputs=bundle_outputs,
        excluded_dirs=excluded_dirs,
        excluded_globs=excluded_globs,
        max_chars=args.max_chars,
        max_bytes=args.max_bytes,
        flatten_output=args.flatten_output,
        inject_path_frontmatter=inject_path_frontmatter,
    )

    written_paths = [path for _, paths in bundle_outputs for path in paths]

    logger.info("완료: %s개 입력 -> %s개 출력", len(md_files), len(written_paths))
    logger.info("결과 위치: %s", output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
