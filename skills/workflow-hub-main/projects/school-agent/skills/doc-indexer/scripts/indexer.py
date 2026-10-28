"""
doc-indexer: ODT/PDF 공문서 파싱 + ChromaDB 벡터 인덱싱
사용법:
  python indexer.py --once   # 폴더 내 기존 파일 전체 인덱싱
  python indexer.py          # 실시간 폴더 감시 모드
"""

import os
import sys
import time
import hashlib
import argparse
import re
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from odf.opendocument import load as load_odt
from odf.text import P as OdfP
from odf.table import Table, TableRow, TableCell
from odf import teletype
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

load_dotenv()

# ── 설정 ────────────────────────────────────────────────────────────
WATCH_FOLDER = Path(os.getenv("WATCH_FOLDER", "./docs-inbox"))
CHROMA_PATH  = os.getenv("CHROMA_PATH", "./chroma-db")
EMBED_MODEL  = os.getenv("EMBED_MODEL", "jhgan/ko-sroberta-multitask")
CHUNK_SIZE   = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP= int(os.getenv("CHUNK_OVERLAP", "50"))
COLLECTION   = "school_docs"

# 인덱싱 제외 패턴 (파일명/경로에 포함되면 무시)
EXCLUDE_PATTERNS = [p.strip() for p in os.getenv("EXCLUDE_PATTERNS", "").split(",") if p.strip()]

# 간단한 부서(업무) 키워드 사전 (파일명/경로에서 추출)
DEPT_KEYWORDS = [
    "교무", "연구", "과학", "체육", "보건", "급식", "행정", "학생", "생활", "안전",
    "돌봄", "방과후", "특수", "상담", "인사", "회계", "예산", "시설", "정보", "전산",
]

# ── ChromaDB 초기화 ─────────────────────────────────────────────────
print(f"[init] 임베딩 모델 로딩: {EMBED_MODEL}")
embed_fn = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
client   = chromadb.PersistentClient(path=CHROMA_PATH)
col      = client.get_or_create_collection(COLLECTION, embedding_function=embed_fn)
print(f"[init] ChromaDB 준비 완료 (컬렉션: {COLLECTION})")


# ── 유틸리티 ────────────────────────────────────────────────────────
def should_exclude(path: Path) -> bool:
    """파일명이나 경로에 제외 패턴이 포함되어 있는지 확인합니다."""
    path_str = str(path.resolve())
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str:
            return True
    return False


# ── 메타데이터 추출 ───────────────────────────────────────────────────
def extract_year_from_path(path: Path) -> str | None:
    # 폴더명/파일명 어디든 20xx가 있으면 연도로 사용
    m = re.search(r"(20\d{2})", str(path))
    return m.group(1) if m else None


def extract_dept_from_path(path: Path) -> str | None:
    s = str(path)
    for kw in DEPT_KEYWORDS:
        if kw in s:
            return kw
    return None


# ── ODT 파싱 (구조 보존) ──────────────────────────────────────────────
def parse_odt_elements(path: Path) -> list[dict]:
    """ODT 파일에서 문단/표를 요소 단위로 추출합니다."""
    try:
        doc = load_odt(str(path))
        elements: list[dict] = []

        def walk(node):
            # 문단
            if getattr(node, "qname", None) and node.qname[1] == "p":
                text = teletype.extractText(node).strip()
                if text:
                    elements.append({"type": "paragraph", "text": text})
                return

            # 표
            if getattr(node, "qname", None) and node.qname[1] == "table":
                rows_out: list[str] = []
                for row in getattr(node, "childNodes", []):
                    if getattr(row, "qname", None) and row.qname[1] == "table-row":
                        cells: list[str] = []
                        for cell in getattr(row, "childNodes", []):
                            if getattr(cell, "qname", None) and cell.qname[1] == "table-cell":
                                val = teletype.extractText(cell).strip()
                                cells.append(val)
                        if any(c.strip() for c in cells):
                            rows_out.append(" | ".join(c.strip() for c in cells))
                if rows_out:
                    elements.append({"type": "table", "text": "\n".join(rows_out)})
                return

            for child in getattr(node, "childNodes", []):
                walk(child)

        walk(doc.text)
        return elements

    except Exception as e:
        print(f"  [경고] ODT 파싱 실패: {path.name} — {e}")
        return []


def parse_pdf(path: Path) -> str:
    """PDF 파일에서 텍스트를 추출합니다."""
    try:
        from pdfminer.high_level import extract_text
        return extract_text(str(path))
    except ImportError:
        print("  [경고] pdfminer.six 미설치. PDF 지원 불가.")
        return ""
    except Exception as e:
        print(f"  [경고] PDF 파싱 실패: {path.name} — {e}")
        return ""


# ── 구조 보존 청킹 ────────────────────────────────────────────────────
def _chunk_by_elements(elements: list[dict]) -> list[tuple[str, dict]]:
    """
    요소(문단/표)를 경계로 유지하면서 CHUNK_SIZE 목표로 묶습니다.
    반환: (chunk_text, chunk_meta) 리스트
    """
    chunks: list[tuple[str, dict]] = []
    buf: list[dict] = []
    buf_len = 0

    def flush():
        nonlocal buf, buf_len
        if not buf:
            return
        text = "\n\n".join(e["text"] for e in buf if e.get("text"))
        if text.strip():
            chunk_type = "mixed"
            types = {e.get("type") for e in buf}
            if len(types) == 1:
                chunk_type = next(iter(types))
            chunks.append((text.strip(), {"chunk_type": chunk_type}))
        buf = []
        buf_len = 0

    for e in elements:
        t = (e.get("text") or "").strip()
        if not t:
            continue

        # 요소가 너무 길면(특히 표) 단독 청크로 처리하되, 정말 큰 경우에만 슬라이스
        if len(t) >= CHUNK_SIZE:
            flush()
            if len(t) <= CHUNK_SIZE * 2:
                chunks.append((t, {"chunk_type": e.get("type", "unknown")}))
            else:
                start = 0
                while start < len(t):
                    end = start + CHUNK_SIZE
                    part = t[start:end].strip()
                    if part:
                        chunks.append((part, {"chunk_type": e.get("type", "unknown")}))
                    start += CHUNK_SIZE - CHUNK_OVERLAP
            continue

        # 버퍼에 추가했을 때 넘치면 먼저 flush
        if buf and (buf_len + len(t) + 2) > CHUNK_SIZE:
            flush()

        buf.append(e)
        buf_len += len(t) + 2

    flush()

    # 오버랩: 이전 청크의 마지막 N자를 다음 청크 앞에 붙여 맥락 유지(구조 경계는 유지)
    if CHUNK_OVERLAP > 0 and len(chunks) >= 2:
        out: list[tuple[str, dict]] = [chunks[0]]
        for prev, cur in zip(chunks, chunks[1:]):
            prev_text, _ = prev
            cur_text, cur_meta = cur
            overlap = prev_text[-CHUNK_OVERLAP:].strip()
            if overlap and not cur_text.startswith(overlap):
                cur_text = overlap + "\n" + cur_text
            out.append((cur_text, cur_meta))
        return out

    return chunks


def chunk_for_file(path: Path, suffix: str) -> list[tuple[str, dict]]:
    """파일 형식별로 구조를 최대한 보존하여 청킹합니다."""
    if suffix == ".odt":
        elements = parse_odt_elements(path)
        return _chunk_by_elements(elements)
    # PDF: 구조 정보가 약해 문단 단위로 최대한 분리
    text = parse_pdf(path)
    if not text.strip():
        return []
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    elements = [{"type": "paragraph", "text": p} for p in paras]
    return _chunk_by_elements(elements)


# ── 파일 ID 생성 ─────────────────────────────────────────────────────
def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


# ── 인덱싱 ───────────────────────────────────────────────────────────
def index_file(path: Path) -> bool:
    """파일을 파싱하여 ChromaDB에 저장. 이미 인덱싱된 파일은 건너뜁니다."""
    suffix = path.suffix.lower()
    if suffix not in (".odt", ".pdf"):
        return False
    
    if should_exclude(path):
        print(f"  [제외] 패턴 매칭되어 인덱싱 건너뜀: {path.name}")
        return False

    fhash = file_hash(path)

    # 중복 체크: 같은 해시 이미 저장된 경우 스킵
    existing = col.get(where={"file_hash": fhash}, limit=1)
    if existing["ids"]:
        print(f"  [스킵] 이미 인덱싱됨: {path.name}")
        return False

    print(f"  [파싱] {path.name} ...")
    chunk_pairs = chunk_for_file(path, suffix)
    if not chunk_pairs:
        print(f"  [경고] 텍스트 비어있음: {path.name}")
        return False

    chunks = [t for (t, _m) in chunk_pairs]
    now    = datetime.now().isoformat()
    year   = extract_year_from_path(path)
    dept   = extract_dept_from_path(path)

    ids       = [f"{fhash}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "file_name": path.name,
            "file_path": str(path.resolve()),
            "file_hash": fhash,
            "file_type": suffix,
            "chunk_idx": i,
            "chunk_type": chunk_pairs[i][1].get("chunk_type", "unknown"),
            "year": year,
            "dept": dept,
            "indexed_at": now,
        }
        for i in range(len(chunks))
    ]

    col.add(ids=ids, documents=chunks, metadatas=metadatas)
    print(f"  ✅ {path.name} — {len(chunks)}개 청크 저장 완료")
    return True


def index_folder(folder: Path):
    """폴더 안의 모든 ODT/PDF 파일을 인덱싱합니다."""
    files = list(folder.rglob("*.odt")) + list(folder.rglob("*.pdf"))
    if not files:
        print(f"[!] 처리할 파일 없음: {folder}")
        return
    print(f"[scan] {len(files)}개 파일 발견 → 인덱싱 시작")
    for f in files:
        index_file(f)
    total = col.count()
    print(f"\n[완료] 전체 저장된 청크 수: {total}")


def purge_excluded_data():
    """DB에 이미 저장된 데이터 중 제외 패턴에 맞는 것들을 삭제합니다."""
    if not EXCLUDE_PATTERNS:
        print("[!] 설정된 제외 패턴(EXCLUDE_PATTERNS)이 없습니다.")
        return

    print(f"[purge] 현재 제외 패턴: {EXCLUDE_PATTERNS}")
    
    # DB의 모든 메타데이터를 확인하여 패턴 매칭되는 파일명/경로 찾기
    all_data = col.get(include=["metadatas"])
    metas = all_data.get("metadatas") or []
    ids = all_data.get("ids") or []
    
    deleted_ids = []
    deleted_files = set()
    
    for i, meta in zip(ids, metas):
        file_name = meta.get("file_name", "")
        file_path = meta.get("file_path", "")
        
        # 파일명이나 경로에 패턴이 있는지 확인
        is_match = False
        for p in EXCLUDE_PATTERNS:
            if p in file_name or p in file_path:
                is_match = True
                break
        
        if is_match:
            deleted_ids.append(i)
            deleted_files.add(file_name)
    
    if deleted_ids:
        # ChromaDB는 한 번에 너무 많은 ID를 삭제하면 에러가 날 수 있으므로 배치 처리
        batch_size = 500
        for i in range(0, len(deleted_ids), batch_size):
            batch = deleted_ids[i : i + batch_size]
            col.delete(ids=batch)
            
        print(f"  🔥 삭제 완료: {len(deleted_files)}개 파일 ({len(deleted_ids)}개 청크)")
        for f in sorted(list(deleted_files)):
            print(f"    - {f}")
    else:
        print("  ✅ 삭제할 데이터가 없습니다.")


# ── 실시간 감시 ──────────────────────────────────────────────────────
class DocHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            path = Path(event.src_path)
            if path.suffix.lower() in (".odt", ".pdf"):
                print(f"\n[감지] 새 파일: {path.name}")
                time.sleep(0.5)  # 파일 쓰기 완료 대기
                index_file(path)

    def on_moved(self, event):
        """파일이 복사·이동될 때도 처리"""
        if not event.is_directory:
            path = Path(event.dest_path)
            if path.suffix.lower() in (".odt", ".pdf"):
                print(f"\n[이동 감지] {path.name}")
                time.sleep(0.5)
                index_file(path)


# ── 메인 ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="공문서 인덱서")
    parser.add_argument("--once", action="store_true", help="기존 파일만 1회 인덱싱 후 종료")
    parser.add_argument("--purge-excluded", action="store_true", help="제외 패턴에 맞는 기존 데이터를 DB에서 삭제")
    args = parser.parse_args()

    if args.purge_excluded:
        purge_excluded_data()
        if not args.once: # --once가 없으면 삭제만 하고 종료
            return

    WATCH_FOLDER.mkdir(parents=True, exist_ok=True)
    print(f"[설정] 감시 폴더: {WATCH_FOLDER.resolve()}")
    print(f"[설정] ChromaDB:  {CHROMA_PATH}")

    # 기존 파일 인덱싱
    index_folder(WATCH_FOLDER)

    if args.once:
        print("[완료] --once 모드 종료")
        return

    # 실시간 감시
    observer = Observer()
    observer.schedule(DocHandler(), str(WATCH_FOLDER), recursive=True)
    observer.start()
    print(f"\n[감시 중] {WATCH_FOLDER.resolve()} — 종료하려면 Ctrl+C")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    print("[종료] 인덱서 종료됨")


if __name__ == "__main__":
    main()
