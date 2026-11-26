"""doc-indexer(indexer.py · search.py · ask.py) 시험.

네트워크·실제 ChromaDB·임베딩 모델·OpenRouter·비밀값 없이 가짜로 시험한다. 가짜 문서 이름만 사용.
- chromadb / sentence-transformers / rank-bm25 / openai 는 메모리 속 가짜 모듈로 대신한다
  (이 작업 환경에 없고 설치도 막혀 있음. 교사 PC 에서도 같은 결과가 나오게 항상 가짜를 쓴다).
- odfpy · watchdog 는 실제 패키지를 쓴다(없으면 indexer 시험은 건너뜀). ODT 는 시험 안에서 직접 만든다.
- 순위 섞기(RRF)·문서 조각 만들기·메타데이터 같은 '우리 코드'를 시험한다. 실제 검색 품질은 시험하지 않는다.

소스는 고치지 않는다. 현재 동작과 다르게 기대하는 것은 xfail 로 표시하고 이유를 적었다.
"""
import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

DOC_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = DOC_DIR / "scripts"


# ── 가짜 chromadb 등 ───────────────────────────────────────────

class FakeCollection:
    def __init__(self):
        self.rows = {}               # id -> (문서, 메타)
        self.delete_calls = []       # 삭제 때 넘긴 id 묶음 크기
        self.get_calls = 0
        self.query_calls = []
        self.dense_ids = None        # None 이면 넣은 순서대로
        self.dense_dists = None

    def count(self):
        return len(self.rows)

    def add(self, ids, documents, metadatas):
        for i, d, m in zip(ids, documents, metadatas):
            self.rows[i] = (d, m)

    @staticmethod
    def _match(meta, where):
        if not where:
            return True
        if "$and" in where:
            return all(FakeCollection._match(meta, w) for w in where["$and"])
        return all(meta.get(k) == v for k, v in where.items())

    def get(self, ids=None, where=None, limit=None, offset=0, include=None):
        self.get_calls += 1
        picked = [
            (i, d, m) for i, (d, m) in self.rows.items()
            if (ids is None or i in ids) and self._match(m, where)
        ]
        end = None if limit is None else offset + limit
        picked = picked[offset:end]
        return {
            "ids": [p[0] for p in picked],
            "documents": [p[1] for p in picked],
            "metadatas": [p[2] for p in picked],
        }

    def query(self, query_texts, n_results, where=None, include=None):
        self.query_calls.append({"n_results": n_results, "where": where})
        order = self.dense_ids if self.dense_ids is not None else list(self.rows)
        order = [i for i in order if i in self.rows and self._match(self.rows[i][1], where)][:n_results]
        dists = self.dense_dists or [0.1 * (k + 1) for k in range(len(order))]
        return {
            "ids": [order],
            "documents": [[self.rows[i][0] for i in order]],
            "metadatas": [[self.rows[i][1] for i in order]],
            "distances": [dists[: len(order)]],
        }

    def delete(self, ids):
        self.delete_calls.append(len(ids))
        for i in ids:
            self.rows.pop(i, None)


class FakeClient:
    def __init__(self):
        self.collections = {}

    def get_or_create_collection(self, name, embedding_function=None):
        return self.collections.setdefault(name, FakeCollection())

    def get_collection(self, name, embedding_function=None):
        if name not in self.collections:
            raise ValueError(f"Collection {name} does not exist")
        return self.collections[name]


class FakeBM25:
    """낱말이 그대로 겹치는 개수를 점수로 쓰는 아주 단순한 가짜."""

    def __init__(self, corpus):
        self.corpus = corpus

    def get_scores(self, query_tokens):
        return [sum(1 for t in query_tokens if t in doc) for doc in self.corpus]


@pytest.fixture
def chroma(monkeypatch):
    registry = {}
    loaded_models = []

    def persistent_client(path):
        return registry.setdefault(path, FakeClient())

    class FakeEmbedFn:
        def __init__(self, model_name):
            loaded_models.append(model_name)

    chromadb = types.ModuleType("chromadb")
    chromadb.PersistentClient = persistent_client
    utils = types.ModuleType("chromadb.utils")
    emb = types.ModuleType("chromadb.utils.embedding_functions")
    emb.SentenceTransformerEmbeddingFunction = FakeEmbedFn
    chromadb.utils = utils
    utils.embedding_functions = emb
    bm25 = types.ModuleType("rank_bm25")
    bm25.BM25Okapi = FakeBM25
    skill_env = types.ModuleType("skill_env")
    skill_env.load_env = lambda *a, **k: None   # 중앙 .env 를 읽지 않음
    skill_env.data_dir = lambda *a, **k: Path(".")
    for name, mod in {
        "chromadb": chromadb, "chromadb.utils": utils,
        "chromadb.utils.embedding_functions": emb,
        "rank_bm25": bm25, "skill_env": skill_env,
    }.items():
        monkeypatch.setitem(sys.modules, name, mod)
    return SimpleNamespace(registry=registry, models=loaded_models)


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("WATCH_FOLDER", str(tmp_path / "inbox"))
    monkeypatch.setenv("CHUNK_SIZE", "100")
    monkeypatch.setenv("CHUNK_OVERLAP", "10")
    monkeypatch.delenv("EXCLUDE_PATTERNS", raising=False)
    monkeypatch.delenv("EMBED_MODEL", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    return tmp_path


@pytest.fixture
def idx(chroma, env):
    pytest.importorskip("odf")
    pytest.importorskip("watchdog")
    return load_script("t_doc_indexer", "indexer.py")


@pytest.fixture
def srch(chroma, env):
    return load_script("t_doc_search", "search.py")


@pytest.fixture
def ask(chroma, env, monkeypatch):
    mod_openai = types.ModuleType("openai")
    mod_openai.OpenAI = object
    monkeypatch.setitem(sys.modules, "openai", mod_openai)
    return load_script("t_doc_ask", "ask.py")


def fill(chroma_ns, env_path, items):
    """items: [(id, 문서, 메타)] 를 가짜 컬렉션에 넣고 돌려준다."""
    client = chroma_ns.registry.setdefault(str(env_path / "chroma"), FakeClient())
    col = client.get_or_create_collection("school_docs")
    col.add([i[0] for i in items], [i[1] for i in items], [i[2] for i in items])
    return col


DOCS = [
    ("d1", "과학의 달 예산 기안 계획", {"file_name": "a.odt", "year": "2026", "dept": "과학", "indexed_at": "2026-11-25T10:00:00"}),
    ("d2", "체육대회 운영 계획", {"file_name": "b.odt", "year": "2025", "dept": "체육", "indexed_at": "2025-05-01T10:00:00"}),
    ("d3", "과학 실험 안전 교육", {"file_name": "c.odt", "year": "2026", "dept": "안전", "indexed_at": "2026-03-02T10:00:00"}),
]


# ══ indexer.py ═════════════════════════════════════════════════

def test_indexer_uses_env_settings_and_embed_model(idx, chroma):
    assert idx.CHUNK_SIZE == 100 and idx.CHUNK_OVERLAP == 10
    assert chroma.models == ["jhgan/ko-sroberta-multitask"]   # EMBED_MODEL 기본값


def test_extract_year_from_path(idx):
    assert idx.extract_year_from_path(Path("공문/2025학년도/계획.odt")) == "2025"
    assert idx.extract_year_from_path(Path("계획서.odt")) is None
    assert idx.extract_year_from_path(Path("19990101_x.pdf")) is None


def test_extract_year_ignores_digits_inside_longer_numbers(idx):
    # 문서번호 같은 긴 숫자 속의 20xx 는 연도가 아니다(ISSUE-004 ① 해결)
    assert idx.extract_year_from_path(Path("공문/교무-12023456.pdf")) is None
    assert idx.extract_year_from_path(Path("공문/교무-2023456.pdf")) is None          # 7자리
    assert idx.extract_year_from_path(Path("공문/교무-120234.pdf")) is None            # 앞이 '20' 이 아님


@pytest.mark.parametrize("name, expected", [
    ("20250304_공문.pdf", "2025"),            # 날짜 붙임(YYYYMMDD)
    ("202503_보고.odt", "2025"),              # 연월(YYYYMM)
    ("20250304153012_scan.pdf", "2025"),      # 날짜+시각 14자리
    ("2025-03-04 계획.odt", "2025"),           # 구분 기호가 있는 날짜
    ("2025.3.4 계획.odt", "2025"),
    ("계획2025학년도.odt", "2025"),            # 글자에 붙은 4자리
    ("문서12023456_2024 계획.pdf", "2024"),    # 긴 숫자는 건너뛰고 뒤의 진짜 연도를 쓴다
    ("20251399.pdf", None),                   # 13월 99일 → 날짜가 아님
    ("20251315.pdf", None),                   # 13월 15일: 달만 틀려도 날짜가 아님
    ("202513_보고.odt", None),                # 연월 13월
    ("20250015.pdf", None),                   # 0월
    ("20250100.pdf", None),                   # 0일 → 날짜가 아님
    ("2099.pdf", "2099"),                     # 4자리 20xx 는 그대로 연도
    ("1999.pdf", None),
    ("19990304.pdf", None),                   # 날짜 모양이어도 20xx 가 아니면 연도로 안 침
])
def test_extract_year_digit_runs(idx, name, expected):
    assert idx.extract_year_from_path(Path("공문") / name) == expected


def test_extract_year_takes_the_first_valid_year_in_path_order(idx):
    assert idx.extract_year_from_path(Path("2024학년도/20250304_공문.pdf")) == "2024"


def test_extract_dept_from_path(idx):
    assert idx.extract_dept_from_path(Path("공문/체육/대회.odt")) == "체육"
    assert idx.extract_dept_from_path(Path("공문/기타/대회.odt")) is None


def test_extract_dept_uses_keyword_list_order_not_path_order(idx):
    # '교무' 가 목록에서 '체육' 보다 앞이라, 체육 폴더 안의 '교무회의' 파일도 교무가 된다(현재 동작)
    assert idx.extract_dept_from_path(Path("체육/교무회의.odt")) == "교무"


def test_should_exclude(idx, monkeypatch, tmp_path):
    f = tmp_path / "초안_임시.odt"
    f.write_text("x", encoding="utf-8")
    monkeypatch.setattr(idx, "EXCLUDE_PATTERNS", [])
    assert idx.should_exclude(f) is False
    monkeypatch.setattr(idx, "EXCLUDE_PATTERNS", ["임시"])
    assert idx.should_exclude(f) is True
    monkeypatch.setattr(idx, "EXCLUDE_PATTERNS", ["없는말", "초안"])
    assert idx.should_exclude(f) is True


def test_exclude_patterns_parsed_from_env(chroma, env, monkeypatch):
    pytest.importorskip("odf")
    pytest.importorskip("watchdog")
    monkeypatch.setenv("EXCLUDE_PATTERNS", " 임시 , ,초안,")
    mod = load_script("t_doc_indexer_ex", "indexer.py")
    assert mod.EXCLUDE_PATTERNS == ["임시", "초안"]


# ── 청크 나누기 ────────────────────────────────────────────────

def para(text):
    return {"type": "paragraph", "text": text}


def test_chunk_empty_and_blank_elements(idx):
    assert idx._chunk_by_elements([]) == []
    assert idx._chunk_by_elements([para("   "), {"type": "table", "text": ""}, {"type": "paragraph"}]) == []


def test_chunk_merges_small_paragraphs_and_overflows_to_next_chunk(idx):
    chunks = idx._chunk_by_elements([para("가" * 40), para("나" * 40), para("다" * 40)])
    assert [c[0] for c in chunks] == [
        "가" * 40 + "\n\n" + "나" * 40,
        "나" * 10 + "\n" + "다" * 40,        # 앞 조각 끝 10자가 겹쳐 붙음
    ]
    assert all(meta == {"chunk_type": "paragraph"} for _, meta in chunks)


def test_chunk_type_mixed_when_paragraph_and_table_share_chunk(idx):
    chunks = idx._chunk_by_elements([para("문단"), {"type": "table", "text": "가 | 나"}])
    assert len(chunks) == 1
    assert chunks[0][0] == "문단\n\n가 | 나"
    assert chunks[0][1]["chunk_type"] == "mixed"


def test_chunk_long_element_standalone_and_flushes_buffer_first(idx):
    chunks = idx._chunk_by_elements([para("앞" * 20), {"type": "table", "text": "표" * 150}, para("뒤" * 20)])
    texts = [c[0] for c in chunks]
    assert texts[0] == "앞" * 20
    assert "표" * 150 in texts[1]
    assert chunks[1][1]["chunk_type"] == "table"
    assert texts[2].endswith("뒤" * 20)


def test_chunk_exactly_chunk_size_is_standalone(idx):
    chunks = idx._chunk_by_elements([para("가" * 100)])
    assert [c[0] for c in chunks] == ["가" * 100]


def test_chunk_huge_element_sliced_with_overlap_without_duplicate_prefix(idx):
    text = "".join(chr(0xAC00 + i) for i in range(250))   # 서로 다른 글자 250개
    chunks = idx._chunk_by_elements([para(text)])
    assert [c[0] for c in chunks] == [text[0:100], text[90:190], text[180:250]]


def test_chunk_no_overlap_when_zero(idx, monkeypatch):
    monkeypatch.setattr(idx, "CHUNK_OVERLAP", 0)
    chunks = idx._chunk_by_elements([para("가" * 40), para("나" * 40), para("다" * 40)])
    assert [c[0] for c in chunks][1] == "다" * 40


def test_chunk_for_file_pdf_splits_paragraphs_on_blank_lines(idx, monkeypatch):
    monkeypatch.setattr(idx, "parse_pdf", lambda p: "첫 문단\n줄바꿈\n\n\n둘째 문단\n\n  \n")
    chunks = idx.chunk_for_file(Path("x.pdf"), ".pdf")
    assert [c[0] for c in chunks] == ["첫 문단\n줄바꿈\n\n둘째 문단"]


def test_chunk_for_file_pdf_empty_text(idx, monkeypatch):
    monkeypatch.setattr(idx, "parse_pdf", lambda p: "  \n ")
    assert idx.chunk_for_file(Path("x.pdf"), ".pdf") == []


def test_chunk_for_file_odt_uses_element_parser(idx, monkeypatch):
    monkeypatch.setattr(idx, "parse_odt_elements", lambda p: [para("문단")])
    assert idx.chunk_for_file(Path("x.odt"), ".odt") == [("문단", {"chunk_type": "paragraph"})]


# ── ODT·PDF 읽기 ───────────────────────────────────────────────

def make_odt(path, build):
    from odf.opendocument import OpenDocumentText
    doc = OpenDocumentText()
    build(doc)
    doc.save(str(path))


def test_parse_odt_elements_paragraphs_and_table(idx, tmp_path):
    from odf.table import Table, TableCell, TableRow
    from odf.text import P

    def build(doc):
        doc.text.addElement(P(text="  제목 문단  "))
        doc.text.addElement(P(text=""))
        table = Table()
        for cells in (["이름", "값"], ["", ""], ["가", ""]):
            row = TableRow()
            for c in cells:
                cell = TableCell()
                cell.addElement(P(text=c))
                row.addElement(cell)
            table.addElement(row)
        doc.text.addElement(table)
        doc.text.addElement(P(text="마지막"))

    f = tmp_path / "a.odt"
    make_odt(f, build)
    assert idx.parse_odt_elements(f) == [
        {"type": "paragraph", "text": "제목 문단"},
        {"type": "table", "text": "이름 | 값\n가 | "},
        {"type": "paragraph", "text": "마지막"},
    ]


def test_parse_odt_elements_keeps_heading_text(idx, tmp_path):
    # 제목(text:h) 글도 문단처럼 뽑는다(ISSUE-001 해결)
    from odf.text import H, P

    def build(doc):
        doc.text.addElement(H(outlinelevel=1, text="과학의 달 계획"))
        doc.text.addElement(P(text="본문"))

    f = tmp_path / "h.odt"
    make_odt(f, build)
    texts = [e["text"] for e in idx.parse_odt_elements(f)]
    assert "과학의 달 계획" in texts


def test_parse_odt_elements_keeps_heading_order_and_skips_empty_headings(idx, tmp_path):
    from odf.text import H, P

    def build(doc):
        doc.text.addElement(H(outlinelevel=1, text="1. 목적"))
        doc.text.addElement(P(text="본문 하나"))
        doc.text.addElement(H(outlinelevel=2, text="   "))     # 빈 제목은 뺀다
        doc.text.addElement(H(outlinelevel=2, text="2. 일정"))
        doc.text.addElement(P(text="본문 둘"))

    f = tmp_path / "h2.odt"
    make_odt(f, build)
    assert idx.parse_odt_elements(f) == [
        {"type": "paragraph", "text": "1. 목적"},
        {"type": "paragraph", "text": "본문 하나"},
        {"type": "paragraph", "text": "2. 일정"},
        {"type": "paragraph", "text": "본문 둘"},
    ]


def test_parse_odt_elements_broken_file_returns_empty(idx, tmp_path, capsys):
    f = tmp_path / "깨짐.odt"
    f.write_bytes(b"not a zip")
    assert idx.parse_odt_elements(f) == []
    assert "ODT 파싱 실패" in capsys.readouterr().out


def test_parse_pdf_with_fake_extractor(idx, monkeypatch):
    hl = types.ModuleType("pdfminer.high_level")
    hl.extract_text = lambda p: "추출된 글"
    monkeypatch.setitem(sys.modules, "pdfminer.high_level", hl)
    assert idx.parse_pdf(Path("x.pdf")) == "추출된 글"


def test_parse_pdf_extractor_error_returns_empty(idx, monkeypatch, capsys):
    hl = types.ModuleType("pdfminer.high_level")

    def boom(p):
        raise RuntimeError("깨진 PDF")

    hl.extract_text = boom
    monkeypatch.setitem(sys.modules, "pdfminer.high_level", hl)
    assert idx.parse_pdf(Path("x.pdf")) == ""
    assert "PDF 파싱 실패" in capsys.readouterr().out


def test_parse_pdf_without_pdfminer_returns_empty(idx, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "pdfminer.high_level", None)   # import 하면 ImportError
    assert idx.parse_pdf(Path("x.pdf")) == ""
    assert "pdfminer.six 미설치" in capsys.readouterr().out


# ── 인덱싱 ─────────────────────────────────────────────────────

def test_file_hash_same_content_same_hash(idx, tmp_path):
    a, b, c = tmp_path / "a.odt", tmp_path / "b.odt", tmp_path / "c.odt"
    a.write_bytes(b"abc")
    b.write_bytes(b"abc")
    c.write_bytes(b"abd")
    assert idx.file_hash(a) == idx.file_hash(b) != idx.file_hash(c)


def test_index_file_ignores_other_suffix_and_excluded(idx, monkeypatch, tmp_path):
    txt = tmp_path / "메모.txt"
    txt.write_text("내용", encoding="utf-8")
    assert idx.index_file(txt) is False
    f = tmp_path / "임시.pdf"
    f.write_bytes(b"%PDF")
    monkeypatch.setattr(idx, "EXCLUDE_PATTERNS", ["임시"])
    monkeypatch.setattr(idx, "chunk_for_file", lambda p, s: pytest.fail("제외 파일은 읽으면 안 됨"))
    assert idx.index_file(f) is False
    assert idx.col.count() == 0


def test_index_file_stores_chunks_with_metadata(idx, monkeypatch, tmp_path):
    folder = tmp_path / "2026학년도" / "체육"
    folder.mkdir(parents=True)
    f = folder / "대회계획.PDF"
    f.write_bytes(b"%PDF fake")
    monkeypatch.setattr(idx, "chunk_for_file", lambda p, s: [("첫 조각", {"chunk_type": "paragraph"}), ("둘째 조각", {"chunk_type": "table"})])
    assert idx.index_file(f) is True
    h = idx.file_hash(f)
    assert list(idx.col.rows) == [f"{h}_0", f"{h}_1"]
    doc, meta = idx.col.rows[f"{h}_1"]
    assert doc == "둘째 조각"
    assert meta["file_name"] == "대회계획.PDF" and meta["file_type"] == ".pdf"
    assert meta["chunk_idx"] == 1 and meta["chunk_type"] == "table"
    assert meta["file_hash"] == h and meta["year"] == "2026" and meta["dept"] == "체육"
    assert meta["indexed_at"][:4].isdigit()


def test_index_file_metadata_year_and_dept_are_none_when_not_found(idx, monkeypatch, tmp_path):
    f = tmp_path / "x.odt"
    f.write_bytes(b"odt-bytes")
    monkeypatch.setattr(idx, "extract_year_from_path", lambda p: None)
    monkeypatch.setattr(idx, "extract_dept_from_path", lambda p: None)
    monkeypatch.setattr(idx, "chunk_for_file", lambda p, s: [("조각", {})])
    assert idx.index_file(f) is True
    _doc, meta = next(iter(idx.col.rows.values()))
    assert meta["year"] is None and meta["dept"] is None   # 실제 ChromaDB 가 None 을 받는지는 확인 필요
    assert meta["chunk_type"] == "unknown"


def test_index_file_skips_same_content_already_indexed(idx, monkeypatch, tmp_path, capsys):
    a, b = tmp_path / "a.odt", tmp_path / "b.odt"
    a.write_bytes(b"same")
    b.write_bytes(b"same")
    monkeypatch.setattr(idx, "chunk_for_file", lambda p, s: [("조각", {"chunk_type": "paragraph"})])
    assert idx.index_file(a) is True
    assert idx.index_file(b) is False
    assert idx.col.count() == 1
    assert "이미 인덱싱됨" in capsys.readouterr().out


def test_index_file_empty_text_returns_false(idx, monkeypatch, tmp_path):
    f = tmp_path / "x.odt"
    f.write_bytes(b"x")
    monkeypatch.setattr(idx, "chunk_for_file", lambda p, s: [])
    assert idx.index_file(f) is False
    assert idx.col.count() == 0


@pytest.mark.xfail(
    reason="내용이 바뀐 같은 파일을 다시 넣으면 해시가 달라 새로 저장만 하고, 이전 버전 조각은 DB 에 그대로 남아 "
    "검색 결과에 옛 내용과 새 내용이 같이 나온다(추정: 실제 공문 폴더에서 파일이 고쳐지는 일이 있는지는 확인 필요).",
    strict=False,
)
def test_index_file_replaces_old_chunks_when_same_path_changes(idx, monkeypatch, tmp_path):
    f = tmp_path / "계획.odt"
    texts = {"v": "옛 내용"}
    monkeypatch.setattr(idx, "chunk_for_file", lambda p, s: [(texts["v"], {"chunk_type": "paragraph"})])
    f.write_bytes(b"v1")
    idx.index_file(f)
    texts["v"] = "새 내용"
    f.write_bytes(b"v2")
    idx.index_file(f)
    assert [d for d, _ in idx.col.rows.values()] == ["새 내용"]


def test_index_folder_scans_recursively_and_reports(idx, monkeypatch, tmp_path, capsys):
    (tmp_path / "in" / "sub").mkdir(parents=True)
    for rel in ("a.odt", "sub/b.pdf", "sub/c.txt"):
        (tmp_path / "in" / rel).write_bytes(b"x")
    seen = []
    monkeypatch.setattr(idx, "index_file", lambda p: seen.append(p.name))
    idx.index_folder(tmp_path / "in")
    assert sorted(seen) == ["a.odt", "b.pdf"]
    assert "2개 파일 발견" in capsys.readouterr().out


def test_index_folder_no_files(idx, monkeypatch, tmp_path, capsys):
    (tmp_path / "empty").mkdir()
    monkeypatch.setattr(idx, "index_file", lambda p: pytest.fail("파일이 없는데 호출됨"))
    idx.index_folder(tmp_path / "empty")
    assert "처리할 파일 없음" in capsys.readouterr().out


# ── 제외 데이터 삭제 ───────────────────────────────────────────

def test_purge_without_patterns_does_nothing(idx, capsys):
    idx.col.add(["a"], ["문서"], [{"file_name": "a.odt", "file_path": "/x/a.odt"}])
    idx.purge_excluded_data()
    assert idx.col.count() == 1
    assert "EXCLUDE_PATTERNS" in capsys.readouterr().out


def test_purge_deletes_matching_by_name_or_path(idx, monkeypatch, capsys):
    monkeypatch.setattr(idx, "EXCLUDE_PATTERNS", ["임시", "개인폴더"])
    idx.col.add(
        ["a", "b", "c", "d"], ["1", "2", "3", "4"],
        [
            {"file_name": "임시안.odt", "file_path": "/docs/임시안.odt"},
            {"file_name": "x.odt", "file_path": "/개인폴더/x.odt"},
            {"file_name": "정상.odt", "file_path": "/docs/정상.odt"},
            {"file_name": "임시안.odt", "file_path": "/docs/임시안.odt"},
        ],
    )
    idx.purge_excluded_data()
    assert list(idx.col.rows) == ["c"]
    out = capsys.readouterr().out
    assert "2개 파일 (3개 청크)" in out


def test_purge_deletes_in_batches_of_500(idx, monkeypatch):
    monkeypatch.setattr(idx, "EXCLUDE_PATTERNS", ["임시"])
    n = 1100
    idx.col.add([f"i{k}" for k in range(n)], ["t"] * n, [{"file_name": "임시.odt", "file_path": "/임시.odt"}] * n)
    idx.purge_excluded_data()
    assert idx.col.delete_calls == [500, 500, 100] and idx.col.count() == 0


def test_purge_nothing_to_delete(idx, monkeypatch, capsys):
    monkeypatch.setattr(idx, "EXCLUDE_PATTERNS", ["임시"])
    idx.col.add(["a"], ["1"], [{"file_name": "정상.odt", "file_path": "/정상.odt"}])
    idx.purge_excluded_data()
    assert idx.col.delete_calls == [] and "삭제할 데이터가 없습니다" in capsys.readouterr().out


# ── 폴더 감시기·main ───────────────────────────────────────────

def test_handler_created_and_moved(idx, monkeypatch):
    seen = []
    monkeypatch.setattr(idx.time, "sleep", lambda s: None)
    monkeypatch.setattr(idx, "index_file", lambda p: seen.append(p.name))
    h = idx.DocHandler()
    h.on_created(SimpleNamespace(is_directory=False, src_path="/in/a.odt"))
    h.on_created(SimpleNamespace(is_directory=False, src_path="/in/b.PDF"))
    h.on_created(SimpleNamespace(is_directory=False, src_path="/in/c.txt"))
    h.on_created(SimpleNamespace(is_directory=True, src_path="/in/폴더.odt"))
    h.on_moved(SimpleNamespace(is_directory=False, src_path="/tmp/x", dest_path="/in/d.pdf"))
    h.on_moved(SimpleNamespace(is_directory=False, src_path="/tmp/x", dest_path="/in/e.zip"))
    h.on_moved(SimpleNamespace(is_directory=True, src_path="/tmp/x", dest_path="/in/f.pdf"))
    assert seen == ["a.odt", "b.PDF", "d.pdf"]


def test_main_once_indexes_and_exits(idx, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(sys, "argv", ["indexer.py", "--once"])
    monkeypatch.setattr(idx, "WATCH_FOLDER", tmp_path / "새폴더")
    monkeypatch.setattr(idx, "index_folder", lambda f: calls.append(f))
    monkeypatch.setattr(idx, "Observer", lambda: pytest.fail("--once 에서는 감시하면 안 됨"))
    idx.main()
    assert calls == [tmp_path / "새폴더"] and (tmp_path / "새폴더").is_dir()


def test_main_purge_only_exits_without_indexing(idx, monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "argv", ["indexer.py", "--purge-excluded"])
    monkeypatch.setattr(idx, "purge_excluded_data", lambda: calls.append("purge"))
    monkeypatch.setattr(idx, "index_folder", lambda f: pytest.fail("삭제만 하고 끝나야 함"))
    idx.main()
    assert calls == ["purge"]


def test_main_purge_with_once_does_both(idx, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(sys, "argv", ["indexer.py", "--purge-excluded", "--once"])
    monkeypatch.setattr(idx, "WATCH_FOLDER", tmp_path / "w")
    monkeypatch.setattr(idx, "purge_excluded_data", lambda: calls.append("purge"))
    monkeypatch.setattr(idx, "index_folder", lambda f: calls.append("index"))
    idx.main()
    assert calls == ["purge", "index"]


# ══ search.py ══════════════════════════════════════════════════

def test_tokenize_ko(srch):
    assert srch._tokenize_ko("과학의 달, 예산(기안) NEIS-2026!") == ["과학의", "달", "예산", "기안", "neis", "2026"]
    assert srch._tokenize_ko("") == [] and srch._tokenize_ko("!!! ...") == []


def test_build_where(srch):
    assert srch._build_where(None, None) is None
    assert srch._build_where("2026", None) == {"year": "2026"}
    assert srch._build_where(None, "체육") == {"dept": "체육"}
    assert srch._build_where(2026, "체육") == {"$and": [{"year": "2026"}, {"dept": "체육"}]}
    assert srch._build_where("", "") is None


def test_rrf_fuse(srch):
    scores = srch._rrf_fuse([["a", "b"], ["b", "a"]])
    assert scores["a"] == pytest.approx(scores["b"]) == pytest.approx(1 / 61 + 1 / 62)
    weighted = srch._rrf_fuse([["a"], ["b"]], k=10, weights=[2.0, 1.0])
    assert weighted == {"a": pytest.approx(2 / 11), "b": pytest.approx(1 / 11)}
    assert srch._rrf_fuse([]) == {}


def test_col_get_all_pages_through_batches(srch, chroma, env):
    col = fill(chroma, env, [(f"i{k}", f"문서{k}", {"n": k}) for k in range(5)])
    ids, docs, metas = srch._col_get_all(col, batch=2)
    assert ids == ["i0", "i1", "i2", "i3", "i4"] and docs[4] == "문서4" and metas[2] == {"n": 2}
    assert col.get_calls == 4   # 2+2+1 개 읽고, 빈 결과 확인 1번 더


def test_col_get_all_with_where(srch, chroma, env):
    col = fill(chroma, env, DOCS)
    ids, _docs, _metas = srch._col_get_all(col, where={"year": "2026"})
    assert ids == ["d1", "d3"]


def test_search_missing_collection_exits(srch, chroma, env, capsys):
    with pytest.raises(SystemExit) as e:
        srch.search("질의")
    assert e.value.code == 1
    assert "컬렉션 없음" in capsys.readouterr().out


def test_search_dense_only(srch, chroma, env, capsys):
    col = fill(chroma, env, DOCS)
    col.dense_ids = ["d3", "d1", "d2"]
    col.dense_dists = [0.1, 0.2, 0.4]
    srch.search("과학", top_k=2, hybrid=False)
    out = capsys.readouterr().out
    assert "[1위] 유사도: 90.0%" in out and "[2위] 유사도: 80.0%" in out
    assert out.index("c.odt") < out.index("a.odt") and "b.odt" not in out
    assert "총 2개 결과 반환 (상위 2개 요청)" in out
    assert col.query_calls[0]["n_results"] == 3   # max(top_k, dense_k)=25 → 전체 3개로 줄임


def test_search_dense_only_applies_filters(srch, chroma, env, capsys):
    col = fill(chroma, env, DOCS)
    srch.search("계획", year="2025", dept="체육", hybrid=False)
    out = capsys.readouterr().out
    assert col.query_calls[0]["where"] == {"$and": [{"year": "2025"}, {"dept": "체육"}]}
    assert "b.odt" in out and "a.odt" not in out
    assert "year=2025, dept=체육" in out


def test_search_no_match_prints_no_result(srch, chroma, env, capsys):
    fill(chroma, env, DOCS)
    srch.search("계획", year="1999", hybrid=False)
    assert "결과 없음." in capsys.readouterr().out


def test_search_hybrid_fuses_dense_and_bm25(srch, chroma, env, capsys):
    col = fill(chroma, env, DOCS)
    col.dense_ids = ["d3", "d1", "d2"]
    srch.search("예산", top_k=2, hybrid=True)
    out = capsys.readouterr().out
    # 점수: d1(밀집 2위+BM25 1위) > d3(밀집 1위+BM25 3위) > d2
    assert "(Hybrid: Dense+BM25)" in out
    assert out.index("a.odt") < out.index("c.odt") and "b.odt" not in out
    assert "총 2개 결과 반환" in out


def test_search_hybrid_respects_where_and_empty_subset(srch, chroma, env, capsys):
    col = fill(chroma, env, DOCS)
    srch.search("계획", top_k=5, year="2025", hybrid=True)
    out = capsys.readouterr().out
    assert "b.odt" in out and "a.odt" not in out and "c.odt" not in out
    srch.search("계획", year="1999", hybrid=True)
    assert "결과 없음." in capsys.readouterr().out
    assert col.count() == 3


@pytest.mark.xfail(
    reason="유사도를 (1 - 거리) × 100 으로 계산하는데, 컬렉션을 만들 때 거리 방식을 정하지 않아 기본값(l2)이면 "
    "거리가 1을 넘어 '-40.0%' 같은 음수 유사도가 나올 수 있다(추정: 실제 화면에서 확인 필요).",
    strict=False,
)
def test_search_similarity_never_negative(srch, chroma, env, capsys):
    col = fill(chroma, env, DOCS)
    col.dense_ids = ["d1"]
    col.dense_dists = [1.4]
    srch.search("과학", top_k=1, hybrid=False)
    assert "유사도: -" not in capsys.readouterr().out


def test_search_main_passes_arguments(srch, monkeypatch):
    seen = {}
    monkeypatch.setattr(srch, "search", lambda q, **kw: seen.update(q=q, **kw))
    monkeypatch.setattr(sys, "argv", ["search.py", "질의", "--top", "2", "--year", "2026", "--dept", "과학", "--hybrid", "--dense-k", "7", "--bm25-k", "9"])
    srch.main()
    assert seen == {"q": "질의", "top_k": 2, "year": "2026", "dept": "과학", "hybrid": True, "dense_k": 7, "bm25_k": 9}


def test_search_main_defaults(srch, monkeypatch):
    seen = {}
    monkeypatch.setattr(srch, "search", lambda q, **kw: seen.update(q=q, **kw))
    monkeypatch.setattr(sys, "argv", ["search.py", "질의"])
    srch.main()
    assert seen["top_k"] == 5 and seen["hybrid"] is False and seen["year"] is None


# ══ ask.py ═════════════════════════════════════════════════════

def test_ask_retrieve_returns_fused_pairs(ask, chroma, env):
    col = fill(chroma, env, DOCS)
    col.dense_ids = ["d3", "d1", "d2"]
    results = ask.retrieve("예산", top_k=2)
    assert [m["file_name"] for m, _ in results] == ["a.odt", "c.odt"]
    assert results[0][1] == "과학의 달 예산 기안 계획"


def test_ask_retrieve_missing_collection_exits(ask, capsys):
    with pytest.raises(SystemExit) as e:
        ask.retrieve("질의")
    assert e.value.code == 1


def test_ask_retrieve_empty_collection_returns_empty(ask, chroma, env):
    fill(chroma, env, [])
    assert ask.retrieve("질의") == []


def fake_openai(monkeypatch, ask, chunks=None, error=None):
    record = {}

    class FakeOpenAI:
        def __init__(self, **kw):
            record["init"] = kw
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **kw):
            record["create"] = kw
            if error:
                raise error
            return iter(chunks or [])

    monkeypatch.setattr(ask, "OpenAI", FakeOpenAI)
    return record


def chunk(text):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])


def test_ask_bot_requires_api_key(ask, capsys):
    with pytest.raises(SystemExit) as e:
        ask.ask_bot("질의")
    assert e.value.code == 1
    assert "OPENROUTER_API_KEY" in capsys.readouterr().out


def test_ask_bot_no_results_does_not_call_model(ask, chroma, env, monkeypatch, capsys):
    monkeypatch.setenv("OPENROUTER_API_KEY", "KEY_FAKE")
    fill(chroma, env, [])
    rec = fake_openai(monkeypatch, ask)
    ask.ask_bot("질의")
    assert "관련 문서를 찾지 못했습니다" in capsys.readouterr().out
    assert "create" not in rec


def test_ask_bot_builds_prompt_and_streams_answer(ask, chroma, env, monkeypatch, capsys):
    monkeypatch.setenv("OPENROUTER_API_KEY", "KEY_FAKE")
    col = fill(chroma, env, DOCS)
    col.dense_ids = ["d1", "d3", "d2"]
    rec = fake_openai(monkeypatch, ask, chunks=[chunk("안녕"), chunk(None), chunk("하세요")])
    ask.ask_bot("과학의 달 예산은?", top_k=2)
    out = capsys.readouterr().out
    assert rec["init"] == {"api_key": "KEY_FAKE", "base_url": "https://openrouter.ai/api/v1"}
    assert rec["create"]["stream"] is True and rec["create"]["model"] == "openrouter/hunter-alpha"
    prompt = rec["create"]["messages"][0]["content"]
    assert "[문서 1] a.odt (연도: 2026, 부서: 과학)" in prompt
    assert "과학의 달 예산 기안 계획" in prompt and "[질문]\n과학의 달 예산은?" in prompt
    assert "안녕하세요" in out
    assert "문서에서는 해당 내용을 찾을 수 없습니다" in prompt   # 모르면 모른다고 하게 한 규칙


def test_ask_bot_model_error_is_reported_not_raised(ask, chroma, env, monkeypatch, capsys):
    monkeypatch.setenv("OPENROUTER_API_KEY", "KEY_FAKE")
    fill(chroma, env, DOCS)
    fake_openai(monkeypatch, ask, error=RuntimeError("연결 실패"))
    ask.ask_bot("질의")
    out = capsys.readouterr().out
    assert "AI 답변 생성 오류" in out and "연결 실패" in out


def test_ask_prompt_includes_retrieved_text_so_it_leaves_the_pc(ask, chroma, env, monkeypatch):
    """찾은 공문 조각이 그대로 외부 서비스(OpenRouter)로 보내진다는 사실을 확인한다(교사 확인용 기록)."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "KEY_FAKE")
    fill(chroma, env, [("x", "민감할 수 있는 공문 본문", {"file_name": "x.odt", "year": "2026", "dept": "교무"})])
    rec = fake_openai(monkeypatch, ask, chunks=[chunk("답")])
    ask.ask_bot("질의")
    assert "민감할 수 있는 공문 본문" in rec["create"]["messages"][0]["content"]


def test_ask_prompt_has_no_literal_none(ask, chroma, env, monkeypatch):
    # 연도·부서를 못 찾아 None 으로 저장돼도 프롬프트에 'None' 글자가 들어가지 않는다(ISSUE-003 해결)
    monkeypatch.setenv("OPENROUTER_API_KEY", "KEY_FAKE")
    fill(chroma, env, [("x", "본문", {"file_name": "x.odt", "year": None, "dept": None})])
    rec = fake_openai(monkeypatch, ask, chunks=[chunk("답")])
    ask.ask_bot("질의")
    assert "None" not in rec["create"]["messages"][0]["content"]


def test_ask_prompt_keeps_a_found_year_when_only_dept_is_missing(ask, chroma, env, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "KEY_FAKE")
    fill(chroma, env, [("x", "본문", {"file_name": "x.odt", "year": "2025", "dept": None})])
    rec = fake_openai(monkeypatch, ask, chunks=[chunk("답")])
    ask.ask_bot("질의")
    content = rec["create"]["messages"][0]["content"]
    assert "(연도: 2025, 부서: )" in content and "None" not in content
