"""
ask.py: 공문서 RAG 기반 AI 질의응답 비서
- search.py의 검색 결과를 OpenRouter(Hunter Alpha)에게 보내서 요약/답변 생성

사용법:
  python3 ask.py "올해 수영실기교육 예산은 어디에 쓰면 돼?"
  python3 ask.py "PAPS 실시 대상 학년 개정 내용" --top 10
"""

import os
import sys
import re
import argparse
from dotenv import load_dotenv
from openai import OpenAI

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from rank_bm25 import BM25Okapi

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma-db")
EMBED_MODEL = os.getenv("EMBED_MODEL", "jhgan/ko-sroberta-multitask")
COLLECTION  = "school_docs"


# ── search.py의 핵심 로직을 직접 포함 (import 의존성 문제 방지) ──

def _tokenize_ko(text: str) -> list[str]:
    return [t for t in re.split(r"[^\w가-힣]+", text.lower()) if t]


def _col_get_all(col, where=None, batch=512):
    ids, docs, metas = [], [], []
    offset = 0
    while True:
        data = col.get(where=where, limit=batch, offset=offset, include=["documents", "metadatas"])
        batch_ids = data.get("ids") or []
        if not batch_ids:
            break
        ids.extend(batch_ids)
        docs.extend(data.get("documents") or [])
        metas.extend(data.get("metadatas") or [])
        offset += len(batch_ids)
    return ids, docs, metas


def _rrf_fuse(rankings, k=60, weights=None):
    if weights is None:
        weights = [1.0] * len(rankings)
    scores = {}
    for w, ranking in zip(weights, rankings):
        for r, doc_id in enumerate(ranking, 1):
            scores[doc_id] = scores.get(doc_id, 0.0) + w * (1.0 / (k + r))
    return scores


def retrieve(query: str, top_k: int = 5):
    """ChromaDB에서 하이브리드 검색으로 상위 문서를 가져옵니다."""
    embed_fn = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    try:
        col = client.get_collection(COLLECTION, embedding_function=embed_fn)
    except Exception:
        print("❌ 컬렉션이 없습니다. 먼저 indexer.py를 실행해주세요.")
        sys.exit(1)

    total = col.count()
    print(f"[검색] 총 {total}개 청크에서 하이브리드 검색: \"{query}\"")

    # Dense 검색
    dense_n = min(max(top_k, 25), total)
    dense_results = col.query(query_texts=[query], n_results=dense_n, include=["documents", "metadatas", "distances"])
    dense_ids = dense_results["ids"][0] if dense_results.get("ids") else []

    # BM25 검색
    all_ids, all_docs, all_metas = _col_get_all(col)
    if not all_ids:
        return []

    tokenized = [_tokenize_ko(d) for d in all_docs]
    bm25 = BM25Okapi(tokenized)
    bm25_scores = bm25.get_scores(_tokenize_ko(query))
    bm25_ranked = sorted(range(len(all_ids)), key=lambda i: bm25_scores[i], reverse=True)[:50]
    bm25_ids = [all_ids[i] for i in bm25_ranked]

    # RRF 융합
    fused = _rrf_fuse([dense_ids[:25], bm25_ids])
    final_ids = [doc_id for doc_id, _ in sorted(fused.items(), key=lambda kv: kv[1], reverse=True)][:top_k]

    # 최종 문서 가져오기
    got = col.get(ids=final_ids, include=["documents", "metadatas"])
    id_to_idx = {i: idx for idx, i in enumerate(got.get("ids") or [])}

    results = []
    for i in final_ids:
        if i in id_to_idx:
            idx = id_to_idx[i]
            results.append((got["metadatas"][idx], got["documents"][idx]))
    return results


def ask_bot(query: str, top_k: int = 5):
    """검색 + LLM 답변 생성"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ .env 파일에 OPENROUTER_API_KEY를 설정해주세요.")
        print("   발급: https://openrouter.ai/keys")
        sys.exit(1)

    # 1. 문서 검색
    print(f"\n🔍 '{query}' 관련 문서를 검색합니다...\n")
    results = retrieve(query, top_k=top_k)

    if not results:
        print("관련 문서를 찾지 못했습니다.")
        return

    # 2. 검색 결과를 LLM 컨텍스트로 조립
    context_text = ""
    for idx, (meta, doc) in enumerate(results, 1):
        file_name = meta.get("file_name", "알 수 없음")
        year = meta.get("year", "")
        dept = meta.get("dept", "")
        clean_doc = doc.replace('\n', ' ').strip()
        context_text += f"[문서 {idx}] {file_name} (연도: {year}, 부서: {dept})\n{clean_doc}\n\n"

    prompt = f"""당신은 한국 초등학교 교사를 돕는 업무 자동화 AI 비서입니다.
아래 [관련 공문서 내용]만을 바탕으로 [질문]에 전문적이고 친절하게 답변해주세요.

규칙:
1. 반드시 제공된 문서 내용만 사용할 것.
2. 문서에 답이 없으면 "제공된 문서에서는 해당 내용을 찾을 수 없습니다."라고 할 것.
3. 출처(파일명)를 간략히 명시할 것. 마크다운을 활용할 것.

[관련 공문서 내용]
{context_text}

[질문]
{query}

[답변]
"""

    # 3. OpenRouter API 호출
    print("🤖 AI 비서(Hunter Alpha)가 공문을 분석하여 답변을 작성합니다...\n")
    print("=" * 70)

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        response = client.chat.completions.create(
            model="openrouter/hunter-alpha",
            messages=[
                {"role": "user", "content": prompt}
            ],
            stream=True # 스트리밍 활성화
        )
        
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                print(chunk.choices[0].delta.content, end="", flush=True)
                
        print("\n\n" + "=" * 70)

    except Exception as e:
        print(f"\n❌ AI 답변 생성 오류: {e}")
        print("인터넷 연결 또는 API 키를 확인해주세요.")
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="학교 공문 기반 AI 질의응답 비서")
    parser.add_argument("query", type=str, help="AI에게 물어볼 질문")
    parser.add_argument("--top", type=int, default=5, help="참고할 문서 수 (기본 5)")
    args = parser.parse_args()

    ask_bot(args.query, top_k=args.top)
