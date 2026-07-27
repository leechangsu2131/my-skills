"""
cleaner.py — 원본 문서(txt/md/pdf)를 Episode 배열(episodes.json)로 변환하는 1회성 정제 스크립트.

설계 원칙 (AGENTS.md 참고):
- TTS가 읽을 것은 narration 필드뿐이다. 원문을 그대로 넘기지 않는다.
- 표/그림/구분선/페이지번호 등 잡음은 여기서 제거하거나 자연스러운 문장으로 풀어쓴다.
- Claude 응답이 JSON 스키마를 안 지킬 경우를 대비해 반드시 fallback을 둔다.

사용법:
    export ANTHROPIC_API_KEY=sk-ant-...
    python cleaner.py 원본문서.txt
    python cleaner.py 원본문서.pdf --out episodes.json --block-size 3500 --concurrency 4
"""

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from anthropic import Anthropic
except ImportError:
    sys.exit("anthropic 패키지가 필요합니다: pip install anthropic")

MODEL = "claude-sonnet-5"  # 계정에서 사용 가능한 모델명으로 바꿔도 됩니다.

CLEAN_SYSTEM_PROMPT = """당신은 책/문서의 원문 텍스트를 소리 내어 읽어주기 좋게 다듬는 편집자입니다.
아래 원문 블록을 처리해서 반드시 아래 JSON 스키마로만 응답하세요. 다른 설명, 코드블록 표시(```json 등),
따옴표 밖의 텍스트를 절대 포함하지 마세요.

{
  "narration": "소리 내어 읽기 좋은 자연스러운 문장. 실제 내용은 하나도 빠뜨리지 말 것(요약 금지, 정리만).
                구분선/페이지번호/저작권 표기 등 잡음은 제거. 표나 그림이 텍스트로 깨져 뒤섞인 부분은
                원래 의미를 보존하면서 자연스러운 문장으로 풀어 쓸 것 (예: 'A: 3, B: 5' -> 'A는 3, B는 5입니다').
                명백한 OCR 오탈자는 문맥에 맞게 교정.",
  "entities": ["이 블록에 등장하는 인물/장소/핵심 개념 이름들 (최대 8개)"],
  "summary": "이 블록 내용을 한두 문장으로 요약 (나중에 질문 응답 컨텍스트로 사용됨)"
}
"""


def read_source(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".pdf"):
        try:
            import fitz  # PyMuPDF
        except ImportError:
            sys.exit("PDF를 읽으려면 PyMuPDF가 필요합니다: pip install pymupdf")
        doc = fitz.open(path)
        return "\n\n".join(page.get_text() for page in doc)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def preprocess_text(raw: str) -> str:
    """구분선, 페이지 번호, 기호 과다 줄 등 기계적으로 걸러낼 수 있는 잡음을 제거한다."""
    text = raw.replace("\r", "")

    # "본문 시작" 같은 명시적 마커가 있으면 그 이전(메타데이터 블록)은 통째로 건너뜀
    marker = re.search(r"MAIN TEXT BEGINS BELOW", text, re.IGNORECASE)
    if marker:
        text = text[marker.end():]
        text = re.sub(r"^\s*[=\-_*#~]{3,}\s*\n", "", text)

    cleaned_lines = []
    for line in text.split("\n"):
        t = line.strip()
        if t == "":
            cleaned_lines.append(line)
            continue
        if re.fullmatch(r"[=\-_*#~]{3,}", t):
            continue  # 구분선
        if re.fullmatch(r"\d{1,4}", t):
            continue  # 페이지 번호만 있는 줄
        symbol_count = len(re.findall(r"[^\w\s가-힣.,!?'\"()·:;\-]", t, re.UNICODE))
        if len(t) > 4 and symbol_count / len(t) > 0.4:
            continue  # 기호 비율 과다(표/장식 등)
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"[•▪●]", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text


def split_into_blocks(text: str, block_size: int) -> list[str]:
    """문단 경계를 지키며 block_size 근처로 나눈다."""
    paragraphs = re.split(r"\n\s*\n", text)
    blocks, buf = [], ""
    for p in paragraphs:
        if len(buf) + len(p) + 2 > block_size and buf:
            blocks.append(buf)
            buf = p
        else:
            buf = f"{buf}\n\n{p}" if buf else p
    if buf.strip():
        blocks.append(buf)
    return blocks


def parse_episode_json(raw_response: str, fallback_text: str) -> dict:
    """Claude 응답이 스키마를 안 지킬 경우를 대비한 방어적 파싱."""
    text = raw_response.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        data = json.loads(text)
        if "narration" in data:
            data.setdefault("entities", [])
            data.setdefault("summary", "")
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    # 실패 시: 침묵하는 것보다 원문이라도 읽어주는 게 낫다
    return {"narration": fallback_text, "entities": [], "summary": ""}


def clean_block(client: Anthropic, block: str) -> dict:
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=CLEAN_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": block}],
        )
        raw_text = "".join(
            part.text for part in resp.content if getattr(part, "type", None) == "text"
        )
        return parse_episode_json(raw_text, fallback_text=block)
    except Exception as e:
        print(f"  [경고] 블록 처리 실패, 원문으로 대체: {e}", file=sys.stderr)
        return {"narration": block, "entities": [], "summary": ""}


def build_episodes(blocks: list[str], concurrency: int) -> list[dict]:
    client = Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용
    results = [None] * len(blocks)
    done = 0

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(clean_block, client, b): i for i, b in enumerate(blocks)}
        for future in as_completed(futures):
            i = futures[future]
            results[i] = future.result()
            done += 1
            print(f"책을 준비하는 중… ({done}/{len(blocks)})", end="\r")
    print()

    episodes = []
    for i, r in enumerate(results):
        episodes.append({"id": i, **r})
    return episodes


def main():
    parser = argparse.ArgumentParser(description="문서를 Episode JSON으로 정제합니다.")
    parser.add_argument("source", help="원본 문서 경로 (.txt/.md/.pdf)")
    parser.add_argument("--out", default="episodes.json", help="출력 경로 (기본: episodes.json)")
    parser.add_argument("--block-size", type=int, default=3500, help="정제 요청 단위 글자 수")
    parser.add_argument("--concurrency", type=int, default=4, help="동시 API 요청 수")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("환경변수 ANTHROPIC_API_KEY가 설정되어 있지 않습니다.")

    print(f"'{args.source}' 읽는 중…")
    raw = read_source(args.source)

    print("기계적 잡음 제거 중…")
    cleaned = preprocess_text(raw)

    blocks = split_into_blocks(cleaned, args.block_size)
    print(f"{len(blocks)}개 블록으로 나눴습니다. Claude로 정제를 시작합니다…")

    episodes = build_episodes(blocks, args.concurrency)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)

    with open("progress.json", "w", encoding="utf-8") as f:
        json.dump({"idx": 0, "title": os.path.basename(args.source)}, f, ensure_ascii=False)

    print(f"완료: {args.out} 에 {len(episodes)}개 Episode 저장됨. (progress.json 초기화됨)")


if __name__ == "__main__":
    main()
