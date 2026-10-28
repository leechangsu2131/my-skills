"""
search.py: ChromaDB에서 자연어로 공문 검색
사용법:
  python search.py "과학의 달 예산 기안"
  python search.py "작년 현장학습 동의서" --top 3
  python search.py "체육대회 운영" --year 2026 --dept 체육
  python search.py "NEIS" --hybrid --top 5
"""

import os
import sys
import argparse
import re
from pathlib import Path

from dotenv import load_dotenv
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from rank_bm25 import BM25Okapi

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma-db")
EMBED_MODEL = os.getenv("EMBED_MODEL", "jhgan/ko-sroberta-multitask")
COLLECTION  = "school_docs"

def _tokenize_ko(text: str) -> list[str]:
    # 한국어 형태소 분석까지는 과하지만, BM25용으로 최소 토큰화(공백 + 구두점 분리)
    return [t for t in re.split(r"[^\w가-힣]+", text.lower()) if t]


def _build_where(year: str | None, dept: str | None) -> dict | None:
    filters: list[dict] = []
    if year:
        filters.append({"year": str(year)})
    if dept:
        filters.append({"dept": dept})
    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    # Chroma where는 최상위에 operator 1개 형태를 요구함
    return {"$and": filters}


def _col_get_all(col, where: dict | None = None, batch: int = 512):
    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict] = []
    offset = 0
    while True:
        data = col.get(
            where=where,
            limit=batch,
            offset=offset,
            include=["documents", "metadatas"],
        )
        batch_ids = data.get("ids") or []
        if not batch_ids:
            break
        ids.extend(batch_ids)
        docs.extend(data.get("documents") or [])
        metas.extend(data.get("metadatas") or [])
        offset += len(batch_ids)
    return ids, docs, metas


def _rrf_fuse(rankings: list[list[str]], k: int = 60, weights: list[float] | None = None) -> dict[str, float]:
    """
    Reciprocal Rank Fusion
    score(d) = Σ w_i * 1/(k + rank_i(d))
    """
    if weights is None:
        weights = [1.0] * len(rankings)
    scores: dict[str, float] = {}
    for w, ranking in zip(weights, rankings):
        for r, doc_id in enumerate(ranking, 1):
            scores[doc_id] = scores.get(doc_id, 0.0) + w * (1.0 / (k + r))
    return scores


def search(
    query: str,
    top_k: int = 5,
    year: str | None = None,
    dept: str | None = None,
    hybrid: bool = True,
    dense_k: int = 25,
    bm25_k: int = 50,
):
    print(f"[init] 임베딩 모델 로딩: {EMBED_MODEL}")
    embed_fn = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    client   = chromadb.PersistentClient(path=CHROMA_PATH)

    try:
        col = client.get_collection(COLLECTION, embedding_function=embed_fn)
    except Exception:
        print(f"[오류] 컬렉션 없음. 먼저 indexer.py를 실행하세요.")
        sys.exit(1)

    total = col.count()
    print(f"[검색] 총 {total}개 청크에서 검색: \"{query}\"\n")

    where = _build_where(year, dept)
    if where:
        print(f"[필터] where={where}\n")

    dense_n = min(max(top_k, dense_k), total) if total else 0
    dense_results = col.query(
        query_texts=[query],
        where=where,
        n_results=dense_n,
        include=["documents", "metadatas", "distances"],
    )

    dense_docs = dense_results["documents"][0] if dense_results.get("documents") else []
    dense_metas = dense_results["metadatas"][0] if dense_results.get("metadatas") else []
    dense_dists = dense_results["distances"][0] if dense_results.get("distances") else []
    dense_ids = dense_results["ids"][0] if dense_results.get("ids") else []

    if not hybrid:
        docs = dense_docs[:top_k]
        metas = dense_metas[:top_k]
        distances = dense_dists[:top_k]
        ids = dense_ids[:top_k]
    else:
        # BM25 코퍼스 구성 (필터 적용된 subset만)
        all_ids, all_docs, all_metas = _col_get_all(col, where=where)
        if not all_ids:
            print("결과 없음.")
            return

        tokenized = [_tokenize_ko(d) for d in all_docs]
        bm25 = BM25Okapi(tokenized)
        q_tokens = _tokenize_ko(query)
        bm25_scores = bm25.get_scores(q_tokens)

        # BM25 상위 후보
        bm25_ranked_idx = sorted(range(len(all_ids)), key=lambda i: bm25_scores[i], reverse=True)
        bm25_ranked_idx = bm25_ranked_idx[: min(bm25_k, len(bm25_ranked_idx))]
        bm25_ids_rank = [all_ids[i] for i in bm25_ranked_idx]

        # Dense 상위 후보
        dense_ids_rank = dense_ids[: min(dense_k, len(dense_ids))]

        # RRF 융합
        fused = _rrf_fuse([dense_ids_rank, bm25_ids_rank], k=60, weights=[1.0, 1.0])
        final_ids = [doc_id for doc_id, _ in sorted(fused.items(), key=lambda kv: kv[1], reverse=True)]
        final_ids = final_ids[:top_k]

        # 최종 문서/메타 조회 (id 기반)
        got = col.get(ids=final_ids, include=["documents", "metadatas"])
        # col.get은 요청 순서를 보장하지 않을 수 있어, id→index로 재정렬
        id_to_idx = {i: idx for idx, i in enumerate(got.get("ids") or [])}
        ids = [i for i in final_ids if i in id_to_idx]
        docs = [got["documents"][id_to_idx[i]] for i in ids]
        metas = [got["metadatas"][id_to_idx[i]] for i in ids]
        distances = [None] * len(ids)  # hybrid에서는 dense distance가 전부 있지 않을 수 있음

    if not docs:
        print("결과 없음.")
        return

    print("=" * 60)
    for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances), 1):
        if dist is None:
            print(f"[{i}위] (Hybrid: Dense+BM25)")
        else:
            similarity = round((1 - dist) * 100, 1)
            print(f"[{i}위] 유사도: {similarity}%")
        print(f"  📄 파일: {meta.get('file_name', '?')}")
        if meta.get("year") or meta.get("dept"):
            print(f"  🧾 메타: year={meta.get('year')}, dept={meta.get('dept')}, chunk_type={meta.get('chunk_type')}")
        print(f"  🗓  인덱싱: {meta.get('indexed_at', '?')[:10]}")
        print(f"  📝 내용 미리보기:")
        preview = doc[:200].replace("\n", " ")
        print(f"    {preview}...")
        print()

    print("=" * 60)
    print(f"총 {len(docs)}개 결과 반환 (상위 {top_k}개 요청)")


def main():
    parser = argparse.ArgumentParser(description="공문 자연어 검색")
    parser.add_argument("query", help="검색할 자연어 쿼리")
    parser.add_argument("--top", type=int, default=5, help="반환할 결과 수 (기본: 5)")
    parser.add_argument("--year", type=str, default=None, help="연도 메타데이터 필터 (예: 2026)")
    parser.add_argument("--dept", type=str, default=None, help="부서/업무 키워드 필터 (예: 체육)")
    parser.add_argument("--hybrid", action="store_true", help="Dense+BM25 하이브리드 검색 사용")
    parser.add_argument("--dense-k", type=int, default=25, help="Dense 후보 수 (기본: 25)")
    parser.add_argument("--bm25-k", type=int, default=50, help="BM25 후보 수 (기본: 50)")
    args = parser.parse_args()

    search(
        args.query,
        top_k=args.top,
        year=args.year,
        dept=args.dept,
        hybrid=args.hybrid,
        dense_k=args.dense_k,
        bm25_k=args.bm25_k,
    )


if __name__ == "__main__":
    main()
